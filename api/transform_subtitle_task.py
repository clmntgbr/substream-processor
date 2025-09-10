from typing import Any, Dict
from celery import Celery
from config import Config
from kombu import Queue
from s3_client import S3Client
from file_client import FileClient
from models import TransformSubtitleOptionsRequest, TransformSubtitleResponse, TransformSubtitleFailureResponse

import re
import requests

celery = Celery(
    "tasks",
    broker=Config.RABBITMQ_URL,
)

celery.conf.update(
    {
        "task_serializer": "json",
        "accept_content": ["json"],
        "broker_connection_retry_on_startup": True,
        "task_routes": {
            "tasks.transform_subtitle_task": {"queue": "transform_subtitle_task"},
        },
        "task_queues": [
            Queue(
                "transform_subtitle_task", routing_key="transform_subtitle_task"
            )
        ],
    }
)

s3_client = S3Client(Config)
file_client = FileClient()

@celery.task(name="tasks.transform_subtitle_task", queue='transform_subtitle_task')
def transform_subtitle_task(stream_id: str, subtitle_srt_file: str, options: TransformSubtitleOptionsRequest):
    try:
        print(f"Processing transform subtitle for {stream_id}")
        options = TransformSubtitleOptionsRequest(**options)

        print(options)
        
        s3_srt_key = f"{stream_id}/{subtitle_srt_file}"
        output_srt_path = f"/tmp/{subtitle_srt_file}"
        ass_file_name = subtitle_srt_file.replace('.srt', '.ass')
        output_ass_path = f"/tmp/{ass_file_name}"

        if not s3_client.download_file(s3_srt_key, output_srt_path):
            raise Exception("Failed to download subtitles from S3")
            
        with open(output_srt_path, "r", encoding="utf-8") as srt_file, open(
                output_ass_path, "w", encoding="utf-8"
            ) as ass_file:
                ass_file.write(get_ass_header(options))

                srt_content = srt_file.read().strip()
                srt_blocks = re.split(r"\n\s*\n", srt_content)

                for block in srt_blocks:
                    lines = block.split("\n")
                    if len(lines) < 3:
                        continue

                    start_time, end_time = lines[1].split(" --> ")
                    start_time = srt_time_to_ass(start_time)
                    end_time = srt_time_to_ass(end_time)

                    text = " ".join(lines[2:])
                    formatted_text = split_lines(text)

                    ass_file.write(
                        f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{formatted_text}\n"
                    )

        s3_ass_key = f"{stream_id}/{ass_file_name}"

        if not s3_client.upload_file(output_ass_path, s3_ass_key):
            raise Exception("Failed to upload subtitles to S3")
        
        file_client.delete_file(output_ass_path)
        file_client.delete_file(output_srt_path)

        response = TransformSubtitleResponse(
            subtitle_ass_file=ass_file_name,
            stream_id=stream_id,
        )

        print(f"Sending transform subtitle success response to processor for {stream_id}")
        print(response.dict())

        requests.post(
            Config.SUBSTREAM_API_URL + "/processor/transform-subtitle",
            json=response.dict(),
            headers={
                "Content-Type": "application/json",
                "Authorization": Config.PROCESSOR_TOKEN
            }
        )
    except Exception as e:
        print(f"Sending transform subtitle failure response to processor for {stream_id}")
        requests.post(
            Config.SUBSTREAM_API_URL + "/processor/transform-subtitle-failure",
            json=TransformSubtitleFailureResponse(
                stream_id=stream_id,
            ).dict(),
            headers={
                "Content-Type": "application/json",
                "Authorization": Config.PROCESSOR_TOKEN
            }
        )

def srt_time_to_ass(srt_time):
    h, m, s = srt_time.split(":")
    s, ms = s.split(",")
    return f"{int(h)}:{int(m):02}:{int(s):02}.{ms[:2]}"

def split_lines(text, max_words=4):
    words = text.split()
    mid = len(words) // 2 if len(words) > max_words else len(words)
    return (
        " ".join(words[:mid]) + r"\N" + " ".join(words[mid:])
        if len(words) > max_words
        else text
    )

def get_ass_header(options: TransformSubtitleOptionsRequest):
    return f"""
[Script Info]
ScriptType: v4.00+
PlayResX: 384
PlayResY: 288
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname, Fontsize,PrimaryColour, SecondaryColour,OutlineColour, BackColour, Bold, Italic, Underline,StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default, {options.subtitle_font},{options.subtitle_size}, {convert_color(options.subtitle_color)}, {convert_color(options.subtitle_color)}, {convert_color(options.subtitle_outline_color)},&H00000000, {options.subtitle_bold}, {options.subtitle_italic},{options.subtitle_underline}, 0, 100, 100, 0, 0,1, {options.subtitle_outline_thickness}, {1 if options.subtitle_shadow != "NONE" else 0},2,10,10,{options.y_axis_alignment},0

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

def convert_color(hex_color):
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return "&HFFFFFF"
    r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
    return f"&H{b}{g}{r}"