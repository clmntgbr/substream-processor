from pydantic import BaseModel
from typing import Optional

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

class ExtractSoundRequest(BaseModel):
    stream_id: str
    stream_file_name: str

class ExtractSoundResponse(BaseModel):
    audio_files: list[str]
    stream_id: str

class ExtractSoundFailureResponse(BaseModel):
    stream_id: str

class GenerateSubtitlesRequest(BaseModel):
    stream_id: str
    audio_files: list[str]

class GenerateSubtitlesResponse(BaseModel):
    subtitle_file: str
    subtitle_files: list[str]
    stream_id: str

class GenerateSubtitlesFailureResponse(BaseModel):
    stream_id: str