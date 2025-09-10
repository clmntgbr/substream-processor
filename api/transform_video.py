from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import Optional
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel
from config import Config
from s3_client import S3Client
from file_client import FileClient
from transform_video_task import transform_video_task
from models import TransformVideoRequest
from auth import verify_token
from fastapi import Depends

s3_client = S3Client(Config)
file_client = FileClient()

router = APIRouter(prefix="/api", tags=["video"])

@router.post("/transform-video")
def transform_video(request: TransformVideoRequest, authenticated: bool = Depends(verify_token)):
    print(f"Starting transform video for stream_id: {request.stream_id}")

    transform_video_task.delay(request.stream_id, request.file_name, request.options.model_dump())

    return {
        "stream_id": request.stream_id,
    }