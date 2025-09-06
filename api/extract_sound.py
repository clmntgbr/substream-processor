from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import Optional
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel
from config import Config
from s3_client import S3Client
from file_client import FileClient
from extract_sound_task import extract_sound_task
from models import ExtractSoundRequest
from auth import verify_token
from fastapi import Depends

import requests
import yt_dlp
import os
import uuid
import subprocess

s3_client = S3Client(Config)
file_client = FileClient()

router = APIRouter(prefix="/api", tags=["sound"])

@router.post("/extract-sound")
def extract_sound(request: ExtractSoundRequest, authenticated: bool = Depends(verify_token)):
    print(f"Starting extract sound for stream_id: {request.stream_id}")

    extract_sound_task.delay(request.stream_id, request.stream_file_name)

    return {
        "stream_id": request.stream_id,
    }