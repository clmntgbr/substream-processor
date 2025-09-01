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