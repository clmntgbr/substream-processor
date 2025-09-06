from celery import Celery
from config import Config
from kombu import Queue
from s3_client import S3Client
from file_client import FileClient
from pydub import AudioSegment
from models import GetVideoResponse, GetVideoFailureResponse, ExtractSoundResponse, ExtractSoundFailureResponse

import re
import requests
import yt_dlp
import os
import uuid
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
            "tasks.get_video_task": {"queue": "get_video_task"},
        },
        "task_queues": [
            Queue(
                "get_video_task", routing_key="get_video_task"
            )
        ],
    }
)

s3_client = S3Client(Config)
file_client = FileClient()

# Get video task

@celery.task(name="tasks.get_video_task", queue='get_video_task')
def get_video_task(url: str, stream_id: str):
    print(f"Processing download for {stream_id}")

    try:
        format = "bestvideo[height<=720]+bestaudio/best[height<=720]"
        video_id = stream_id
        output_path = f"/tmp/{video_id}.mp4"

        ydl_opts = {
            "format": format,
            "outtmpl": output_path,
            "merge_output_format": "mp4",
        }

        video_info = get_video_info(format, url)
        download_video(ydl_opts, url)
        file_size = get_file_size(output_path)

        response = GetVideoResponse(
            file_name=f"{video_id}.mp4",
            original_name=video_info.get("title") + ".mp4",
            mime_type="video/mp4",
            size=file_size,
            stream_id=stream_id,
        )

        if not s3_client.upload_file(output_path, f"{stream_id}/{video_id}.mp4"):
            raise Exception("Failed to upload video to S3")

        if not file_client.delete_file(output_path):
            raise Exception("Failed to delete video file")

        requests.post(
            Config.SUBSTREAM_API_URL + "/processor/get-video-url",
            json=response.dict(),
            headers={
                "Content-Type": "application/json",
                "Authorization": Config.PROCESSOR_TOKEN
            }
        )
    except Exception as e:
        requests.post(
            Config.SUBSTREAM_API_URL + "/processor/get-video-url-failure",
            json=GetVideoFailureResponse(
                stream_id=stream_id,
            ).dict(),
            headers={
                "Content-Type": "application/json",
                "Authorization": Config.PROCESSOR_TOKEN
            }
        )

def download_video(ydl_opts, url):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.download([url])
        
    return True

def get_file_size(path) -> int:
    size_bytes = os.path.getsize(path)
    return size_bytes

def get_video_info(format, url) -> dict:
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "format": format,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)
