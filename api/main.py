from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from datetime import datetime
import os
import requests
from pathlib import Path
from download_video import router as download_video

app = FastAPI(
    title="Substream Processor API",
    version="1.0.0"
)

app.include_router(download_video)

@app.get("/status")
async def root():
    return {
        "status": "active",
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9010)