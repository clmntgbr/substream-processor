from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import Optional
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel
from config import Config
from s3_client import S3Client
from file_client import FileClient
from task import get_video_task
from models import GetVideoRequest

import requests
import yt_dlp
import os
import uuid
import subprocess

s3_client = S3Client(Config)
file_client = FileClient()

router = APIRouter(prefix="/api/download", tags=["video"])

@router.post("/video/url")
def get_video_from_url(request: GetVideoRequest):
    print(f"Starting download for stream_id: {request.stream_id}")

    task_id = str(uuid.uuid4())
    get_video_task.delay(request.url, request.stream_id)

    return {
        "status": "queued",
        "stream_id": request.stream_id,
    }