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
            "tasks.transform_subtitles_task": {"queue": "transform_subtitles_task"},
        },
        "task_queues": [
            Queue(
                "transform_subtitles_task", routing_key="transform_subtitles_task"
            )
        ],
    }
)

s3_client = S3Client(Config)
file_client = FileClient()

@celery.task(name="tasks.transform_subtitles_task", queue='transform_subtitles_task')
def transform_subtitles_task(stream_id: str, subtitle_file: str):
    print(f"Processing transform subtitles for {stream_id}")