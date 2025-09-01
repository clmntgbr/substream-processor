from celery import Celery
from config import Config
from kombu import Queue
from models import GetVideoRequest

import yt_dlp

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

@celery.task(name="tasks.get_video_task", queue='get_video_task')
def get_video_task(url: str, stream_id: str):
    print(url)
    print(stream_id)
