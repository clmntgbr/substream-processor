from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from datetime import datetime
import os
import requests
from pathlib import Path
from get_video import router as get_video
from extract_sound import router as extract_sound
from generate_subtitles import router as generate_subtitles
from transform_subtitle import router as transform_subtitle
from transform_video import router as transform_video

app = FastAPI(
    title="Substream Processor API",
    version="1.0.0"
)

app.include_router(get_video)
app.include_router(extract_sound)
app.include_router(generate_subtitles)
app.include_router(transform_subtitle)
app.include_router(transform_video)

@app.get("/status")
async def root():
    return {
        "status": "active",
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9010)