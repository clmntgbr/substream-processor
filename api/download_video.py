from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import Optional
from datetime import datetime
import requests
from pathlib import Path
from pydantic import BaseModel
import asyncio

router = APIRouter(prefix="/api/download", tags=["video"])

class VideoDownloadRequest(BaseModel):
    url: str
    streamId: str

@router.post("/video/url")
async def download_video_from_url(request: VideoDownloadRequest):
    print(request)
    return {
        "status": "success",
    }
