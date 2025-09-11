from typing import Any, Dict
from celery import Celery
from config import Config
from kombu import Queue
from s3_client import S3Client
from file_client import FileClient
from models import TransformVideoOptionsRequest, TransformVideoResponse, TransformVideoFailureResponse

import re
import requests
import ffmpeg

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
            "tasks.transform_video_task": {"queue": "transform_video_task"},
        },
        "task_queues": [
            Queue(
                "transform_video_task", routing_key="transform_video_task"
            )
        ],
    }
)

s3_client = S3Client(Config)
file_client = FileClient()

@celery.task(name="tasks.transform_video_task", queue='transform_video_task')
def transform_video_task(stream_id: str, file_name: str, options: TransformVideoOptionsRequest):
    print(f"Processing transform video for {stream_id}")
    options = TransformVideoOptionsRequest(**options)

    s3_key = f"{stream_id}/{file_name}"
    file_name_transformed = file_name.replace('.mp4', '.transformed.mp4')
    s3_key_transformed = f"{stream_id}/{file_name_transformed}"
    output_path = f"/tmp/{file_name}"
    output_path_transformed = f"/tmp/{file_name_transformed}"

    if not s3_client.download_file(s3_key, output_path):
        raise Exception("Failed to download video from S3")

    if options.video_format == "original":
        print("no transformation needed for original format")

    if options.video_format == "zoomed_916":
        if not transform_video_to_zoomed_916(output_path, output_path_transformed):
            raise Exception("Failed to transform video to zoomed 9:16 format")

    if not s3_client.upload_file(output_path, s3_key_transformed):
        raise Exception("Failed to upload transformed video to S3")

    if not file_client.delete_file(output_path):
        raise Exception("Failed to delete video file")

    response = TransformVideoResponse(
        file_name_transformed=file_name_transformed,
        stream_id=stream_id,
    )

    print(f"Sending transform video success response to processor for {stream_id}")
    print(response.dict())

    requests.post(
        Config.SUBSTREAM_API_URL + "/processor/transform-video",
        json=response.dict(),
    )

def transform_video_to_zoomed_916(input_path: str, output_path: str) -> bool:
    try:
        probe = ffmpeg.probe(input_path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        original_width = int(video_stream['width'])
        original_height = int(video_stream['height'])
        
        max_width = 1080
        max_height = 1920
        target_aspect_ratio = max_width / max_height
        
        original_aspect_ratio = original_width / original_height
        
        if abs(original_aspect_ratio - target_aspect_ratio) < 0.01:
            if original_width <= max_width and original_height <= max_height:
                print("Video is already in correct 9:16 format and resolution, copying without re-encoding")
                ffmpeg.input(input_path).output(output_path, vcodec='copy', acodec='copy').overwrite_output().run()
                return True
            else:
                print("Video is 9:16 but too large, scaling down to max 1080x1920")
                (
                    ffmpeg
                    .input(input_path)
                    .filter('scale', max_width, max_height)
                    .output(
                        output_path,
                        vcodec='libx264',
                        acodec='aac',
                        preset='fast',
                        crf=23,
                        maxrate='4M',
                        bufsize='8M',
                        pix_fmt='yuv420p',
                        movflags='faststart'
                    )
                    .overwrite_output()
                    .run()
                )
                return True

        if original_aspect_ratio > target_aspect_ratio:
            new_width = int(original_height * target_aspect_ratio)
            x_offset = (original_width - new_width) // 2
            crop_width = new_width
            crop_height = original_height
            crop_x = x_offset
            crop_y = 0
        else:
            new_height = int(original_width / target_aspect_ratio)
            y_offset = (original_height - new_height) // 2
            crop_width = original_width
            crop_height = new_height
            crop_x = 0
            crop_y = y_offset
        
        if crop_width <= max_width and crop_height <= max_height:
            (
                ffmpeg
                .input(input_path)
                .filter('crop', crop_width, crop_height, crop_x, crop_y)
                .output(
                    output_path,
                    vcodec='libx264',
                    acodec='aac',
                    preset='fast',
                    crf=23,
                    maxrate='4M',
                    bufsize='8M',
                    pix_fmt='yuv420p',
                    movflags='faststart'
                )
                .overwrite_output()
                .run()
            )
        else:
            (
                ffmpeg
                .input(input_path)
                .filter('crop', crop_width, crop_height, crop_x, crop_y)
                .filter('scale', max_width, max_height)
                .output(
                    output_path,
                    vcodec='libx264',
                    acodec='aac',
                    preset='fast',
                    crf=23,
                    maxrate='4M',
                    bufsize='8M',
                    pix_fmt='yuv420p',
                    movflags='faststart'
                )
                .overwrite_output()
                .run()
            )
        
        return True

    except Exception as e:
        print(f"Error transforming video to zoomed 9:16: {e}")
        return False