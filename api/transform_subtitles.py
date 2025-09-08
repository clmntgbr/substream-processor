from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import Optional
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel
from config import Config
from s3_client import S3Client
from file_client import FileClient
from transform_subtitles_task import transform_subtitles_task
from models import TransformSubtitlesRequest
from auth import verify_token
from fastapi import Depends

s3_client = S3Client(Config)
file_client = FileClient()

router = APIRouter(prefix="/api", tags=["subtitles"])

@router.post("/transform-subtitles")
def transform_subtitles(request: TransformSubtitlesRequest, authenticated: bool = Depends(verify_token)):
    print(f"Starting transform subtitles for stream_id: {request.stream_id}")

    transform_subtitles_task.delay(request.stream_id, request.subtitle_file)

    return {
        "stream_id": request.stream_id,
    }