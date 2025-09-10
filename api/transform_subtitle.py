from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import Optional
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel
from config import Config
from s3_client import S3Client
from file_client import FileClient
from transform_subtitle_task import transform_subtitle_task
from models import TransformSubtitleRequest
from auth import verify_token
from fastapi import Depends

s3_client = S3Client(Config)
file_client = FileClient()

router = APIRouter(prefix="/api", tags=["subtitles"])

@router.post("/transform-subtitle")
def transform_subtitle(request: TransformSubtitleRequest, authenticated: bool = Depends(verify_token)):
    print(f"Starting transform subtitle for stream_id: {request.stream_id}")

    transform_subtitle_task.delay(request.stream_id, request.subtitle_srt_file, request.options.model_dump())

    return {
        "stream_id": request.stream_id,
    }