from celery import Celery
from config import Config
from kombu import Queue
from s3_client import S3Client
from file_client import FileClient
from models import GenerateSubtitlesResponse, GenerateSubtitlesFailureResponse
from functools import partial
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import assemblyai as aai
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
            "tasks.generate_subtitles_task": {"queue": "generate_subtitles_task"},
        },
        "task_queues": [
            Queue(
                "generate_subtitles_task", routing_key="generate_subtitles_task"
            )
        ],
    }
)

s3_client = S3Client(Config)
file_client = FileClient()

@celery.task(name="tasks.generate_subtitles_task", queue='generate_subtitles_task')
def generate_subtitles_task(stream_id: str, audio_files: list[str]):
    try:
        print(f"Processing generate subtitles for {stream_id}")

        partialMultiprocess = partial(multiprocess, stream_id=stream_id)

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(partialMultiprocess, audio_files))
        
        results_sorted = sorted(results, key=extract_chunk_number)
        
        current_offset = 0
        subtitle_index = 1
        merged_subtitles = []
        for file in results_sorted:
            output_path = f"/tmp/{file}"
            parse_subtitles = parse_srt(output_path)
            for _, timestamps, text in parse_subtitles:
                new_timestamps = shift_timestamps(timestamps, current_offset)
                merged_subtitles.append(f"{subtitle_index}\n{new_timestamps}\n{text}\n\n")
                subtitle_index += 1

            current_offset += 300
            file_client.delete_file(output_path)

        s3_srt_key = f"{stream_id}/{stream_id}.srt"
        output_srt_path = f"/tmp/{stream_id}.srt"

        with open(output_srt_path, "w", encoding="utf-8") as f:
            f.writelines(merged_subtitles)

        if not s3_client.upload_file(output_srt_path, s3_srt_key):
            raise Exception()
        
        if not file_client.delete_file(output_srt_path):
            raise Exception()

        response = GenerateSubtitlesResponse(
            subtitle_srt_file=f"{stream_id}.srt",
            subtitle_srt_files=results_sorted,
            stream_id=stream_id,
        )

        print(f"Sending generate subtitles success response to processor for {stream_id}")
        print(response.dict())

        requests.post(
            Config.SUBSTREAM_API_URL + "/processor/generate-subtitles",
            json=response.dict(),
            headers={
                "Content-Type": "application/json",
                "Authorization": Config.PROCESSOR_TOKEN
            }
        )
    except Exception as e:
        print(f"Sending generate subtitles failure response to processor for {stream_id}")
        requests.post(
            Config.SUBSTREAM_API_URL + "/processor/generate-subtitles-failure",
            json=GenerateSubtitlesFailureResponse(
                stream_id=stream_id,
            ).dict(),
            headers={
                "Content-Type": "application/json",
                "Authorization": Config.PROCESSOR_TOKEN
            }
        )

def multiprocess(chunk: str, stream_id: str):
    s3_key = f"{stream_id}/audios/{chunk}"
    output_path = f"/tmp/{chunk}"

    chunk_name = chunk.replace('.wav', '.srt')
    srt_output_path = f"/tmp/{chunk_name}"

    if not s3_client.download_file(s3_key, output_path):
        raise Exception()

    if not generate_subtitle_assemblyAI(output_path, srt_output_path):
        raise Exception()

    if not s3_client.upload_file(srt_output_path, f"{stream_id}/subtitles/{chunk_name}"):
        raise Exception()

    return chunk_name

def extract_chunk_number(item):
    match = re.search(r"_(\d+)\.srt$", item[0])
    return int(match.group(1)) if match else float("inf")

def ms_to_srt_time(ms):
    td = timedelta(milliseconds=ms)
    return f"{td.seconds // 3600:02}:{(td.seconds % 3600) // 60:02}:{td.seconds % 60:02},{td.microseconds // 1000:03}"

def generate_subtitle_assemblyAI(output_path: str, srt_output_path: str) -> bool:
    print("Uploading file for transcription...")

    aai.settings.api_key = Config.ASSEMBLY_AI_API_KEY
    config = aai.TranscriptionConfig(language_detection=True)
    transcriber = aai.Transcriber(config=config)

    transcript = transcriber.transcribe(output_path)
    words = transcript.words

    srtContent = ""
    subIndex = 1
    currentLine = []
    startTime = words[0].start

    for i, word in enumerate(words):
        currentLine.append(word.text)

        if len(currentLine) >= 6 or i == len(words) - 1:
            endTime = words[i].end

            mid_index = len(currentLine) // 2
            first_line = " ".join(currentLine[:mid_index])
            second_line = " ".join(currentLine[mid_index:])

            srtContent += f"{subIndex}\n"
            srtContent += f"{ms_to_srt_time(startTime)} --> {ms_to_srt_time(endTime)}\n"
            srtContent += f"{first_line}\n{second_line}\n\n"

            subIndex += 1
            currentLine = []
            if i < len(words) - 1:
                startTime = words[i + 1].start

    print("File successfully transcribed")

    with open(srt_output_path, "w", encoding="utf-8") as file:
        file.write(srtContent)

    print("SRT file successfully generated")
    return True

def parse_srt(srt_file_path):
    subtitles = []
    with open(srt_file_path, "r", encoding="utf-8") as file:
        content = file.read().strip()

    entries = re.split(r"\n\n+", content)
    for entry in entries:
        lines = entry.split("\n")
        if len(lines) >= 3:
            num = int(lines[0])
            timestamps = lines[1]
            text = "\n".join(lines[2:])
            subtitles.append((num, timestamps, text))

    return subtitles

def shift_timestamps(timestamps, offset_seconds):
    def convertToMs(timestamp):
        match = re.match(r"(\d+):(\d+):(\d+),(\d+)", timestamp)
        if not match:
            raise ValueError(f"Format de timestamp invalide : {timestamp}")
        h, m, s, ms = map(int, match.groups())
        return (h * 3600 + m * 60 + s) * 1000 + ms

    def convertFromMs(ms):
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    start, end = timestamps.split(" --> ")
    start_ms = convertToMs(start) + offset_seconds * 1000
    end_ms = convertToMs(end) + offset_seconds * 1000
    return f"{convertFromMs(start_ms)} --> {convertFromMs(end_ms)}"