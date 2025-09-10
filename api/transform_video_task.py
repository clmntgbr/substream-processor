from typing import Any, Dict
from celery import Celery
from config import Config
from kombu import Queue
from s3_client import S3Client
from file_client import FileClient
from models import TransformVideoOptionsRequest, TransformVideoResponse, TransformVideoFailureResponse

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
