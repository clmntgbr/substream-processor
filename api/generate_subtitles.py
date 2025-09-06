from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import Optional
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel
from config import Config
from s3_client import S3Client
from file_client import FileClient
from generate_subtitles_task import generate_subtitles_task
from models import GenerateSubtitlesRequest
from auth import verify_token
from fastapi import Depends

import requests
import yt_dlp
import os
import uuid
import subprocess

s3_client = S3Client(Config)
file_client = FileClient()

router = APIRouter(prefix="/api", tags=["subtitles"])

@router.post("/generate-subtitles")
def generate_subtitles(request: GenerateSubtitlesRequest, authenticated: bool = Depends(verify_token)):
    print(f"Starting generate subtitles for stream_id: {request.stream_id}")

    generate_subtitles_task.delay(request.stream_id, request.audio_files)

    return {
        "stream_id": request.stream_id,
    }