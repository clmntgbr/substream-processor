from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import Optional
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel
from config import Config
from s3_client import S3Client
from file_client import FileClient

import requests
import yt_dlp
import os
import uuid
import subprocess

s3_client = S3Client(Config)
file_client = FileClient()

router = APIRouter(prefix="/api/download", tags=["video"])

class GetVideoRequest(BaseModel):
    url: str
    stream_id: str

class GetVideoResponse(BaseModel):
    file_name: str
    original_name: str
    mime_type: str
    size: int
    stream_id: str

class GetVideoFailureResponse(BaseModel):
    stream_id: str

@router.post("/video/url")
def get_video_from_url(request: GetVideoRequest):
    print(f"Starting download for stream_id: {request.stream_id}")
    
    # Traitement synchrone direct
    try:
        result = process_video_download(request)
        
        return {
            "status": "completed", 
            "stream_id": request.stream_id,
            "message": "Video download completed successfully",
            "result": result
        }
    except Exception as e:
        print(f"Error in download: {e}")
        return {
            "status": "error",
            "stream_id": request.stream_id,
            "message": f"Download failed: {str(e)}"
        }

def process_video_download(request: GetVideoRequest):
    try:
        print(f"Processing download for {request.stream_id}")
        
        format = "bestvideo[height<=720]+bestaudio/best[height<=720]"
        video_id = str(uuid.uuid4())
        output_path = f"/tmp/{video_id}.mp4"

        ydl_opts = {
            "format": format,
            "outtmpl": output_path,
            "merge_output_format": "mp4",
        }

        print(f"Getting video info...")
        video_info = get_video_info(format, request.url)
        print(f"Video info retrieved: {video_info.get('title', 'Unknown')}")

        print(f"Starting video download...")
        download_video(ydl_opts, request.url)
        print(f"Video download completed")
        
        file_size = get_file_size(output_path)
        print(f"Video file size: {file_size} bytes")

        print(f"Creating response object...")
        response = GetVideoResponse(
            file_name=f"{video_id}.mp4",
            original_name=video_info.get("title") + ".mp4",
            mime_type="video/mp4",
            size=file_size,
            stream_id=request.stream_id,
        )
        print(f"Response object created successfully")

        print(f"Starting S3 upload for {request.stream_id}")
        if not s3_client.upload_file(output_path, f"{request.stream_id}/{video_id}.mp4"):
            raise Exception("Failed to upload video to S3")
        

        print(f"Starting local file deletion for {request.stream_id}")
        if not file_client.delete_file(output_path):
            raise Exception("Failed to delete video file")
        
        print(f"Download completed for {request.stream_id}")
        return response
        
    except Exception as e:
        print(f"Error downloading video: {e}")
        import traceback
        traceback.print_exc()
        raise e

def download_video(ydl_opts, url):
    """Fonction synchrone pour télécharger la vidéo"""
    try:
        print(f"Starting yt-dlp download for {url}")
        print(f"Output path: {ydl_opts['outtmpl']}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.download([url])
            print(f"yt-dlp download result: {result}")
            
        print(f"yt-dlp download completed successfully")
        return True
        
    except Exception as e:
        print(f"yt-dlp download error: {e}")
        import traceback
        traceback.print_exc()
        raise e

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