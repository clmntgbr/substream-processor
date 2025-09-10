from pydantic import BaseModel
from typing import Optional

class GetVideoRequest(BaseModel):
    url: str
    stream_id: str

class GetVideoResponse(BaseModel):
    file_name: str
    original_file_name: str
    mime_type: str
    size: int
    stream_id: str

class GetVideoFailureResponse(BaseModel):
    stream_id: str

class ExtractSoundRequest(BaseModel):
    stream_id: str
    file_name: str

class ExtractSoundResponse(BaseModel):
    audio_files: list[str]
    stream_id: str

class ExtractSoundFailureResponse(BaseModel):
    stream_id: str

class GenerateSubtitlesRequest(BaseModel):
    stream_id: str
    audio_files: list[str]

class GenerateSubtitlesResponse(BaseModel):
    subtitle_srt_file: str
    subtitle_srt_files: list[str]
    stream_id: str

class GenerateSubtitlesFailureResponse(BaseModel):
    stream_id: str

class TransformSubtitleOptionsRequest(BaseModel):
    subtitle_font: str
    subtitle_size: int
    subtitle_color: str
    subtitle_bold: bool
    subtitle_italic: bool
    subtitle_underline: bool
    subtitle_outline_color: str
    subtitle_outline_thickness: int
    subtitle_shadow: int
    subtitle_shadow_color: str
    y_axis_alignment: float

class TransformSubtitleRequest(BaseModel):
    stream_id: str
    subtitle_srt_file: str
    options: TransformSubtitleOptionsRequest

class TransformSubtitleResponse(BaseModel):
    stream_id: str
    subtitle_ass_file: str

class TransformSubtitleFailureResponse(BaseModel):
    stream_id: str

class TransformVideoOptionsRequest(BaseModel):
    video_format: str
    video_parts: int

class TransformVideoRequest(BaseModel):
    stream_id: str
    file_name: str
    options: TransformVideoOptionsRequest

class TransformVideoResponse(BaseModel):
    stream_id: str
    file_name_transformed: str

class TransformVideoFailureResponse(BaseModel):
    stream_id: str