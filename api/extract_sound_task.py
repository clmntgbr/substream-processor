from celery import Celery
from config import Config
from kombu import Queue
from s3_client import S3Client
from file_client import FileClient
from pydub import AudioSegment
from models import GetVideoResponse, GetVideoFailureResponse, ExtractSoundResponse, ExtractSoundFailureResponse

import re
import requests
import yt_dlp
import os
import uuid
import ffmpeg

celery = Celery(
    "tasks",
    broker=Config.RABBITMQ_URL,
)

celery.conf.update(
    {
        "task_serializer": "json",
        "accept_content": ["json"],
        "broker_connection_retry_on_startup": True,
        "task_routes": {
            "tasks.extract_sound_task": {"queue": "extract_sound_task"},
        },
        "task_queues": [
            Queue(
                "extract_sound_task", routing_key="extract_sound_task"
            )
        ],
    }
)

s3_client = S3Client(Config)
file_client = FileClient()

@celery.task(name="tasks.extract_sound_task", queue='extract_sound_task')
def extract_sound_task(stream_id: str, stream_file_name: str):
    try:
        print(f"Processing extract sound for {stream_id}")

        s3_key = f"{stream_id}/{stream_file_name}"
        output_path = f"/tmp/{stream_file_name}"

        if not s3_client.download_file(s3_key, output_path):
            raise Exception("Failed to download video from S3")
        
        audio_file_path = output_path.replace(".mp4", ".mp3")

        if not extract_sound(output_path, audio_file_path):
            raise Exception("Failed to extract audio")

        wav_file_path = convert_to_wav(audio_file_path)
        chunk_filenames = chunk_wav(wav_file_path, stream_id)

        for chunk_filename in chunk_filenames:
            if not s3_client.upload_file(f"/tmp/{chunk_filename}", f"{stream_id}/audios/{chunk_filename}"):
                raise Exception("Failed to upload chunk to S3")

            if not file_client.delete_file(f"/tmp/{chunk_filename}"):
                raise Exception("Failed to delete chunk file")
        
        if not file_client.delete_file(audio_file_path):
            raise Exception("Failed to delete audio file")
        
        if not file_client.delete_file(wav_file_path):
            raise Exception("Failed to delete wav file")
        
        if not file_client.delete_file(output_path):
            raise Exception("Failed to delete video file")

        results_sorted = sorted(chunk_filenames, key=extract_chunk_number)

        response = ExtractSoundResponse(
            audio_files=results_sorted,
            stream_id=stream_id,
        )

        print(f"Sending extract sound success response to processor for {stream_id}")
        print(response.dict())

        requests.post(
            Config.SUBSTREAM_API_URL + "/processor/extract-sound",
            json=response.dict(),
            headers={
                "Content-Type": "application/json",
                "Authorization": Config.PROCESSOR_TOKEN
            }
        )
    except Exception as e:
        print(f"Sending extract sound failure response to processor for {stream_id}")

        requests.post(
            Config.SUBSTREAM_API_URL + "/processor/extract-sound-failure",
            json=ExtractSoundFailureResponse(
                stream_id=stream_id,
            ).dict(),
            headers={
                "Content-Type": "application/json",
                "Authorization": Config.PROCESSOR_TOKEN
            }
        )

def extract_sound(file_path: str, audio_file_path: str) -> bool:
    try:
        ffmpeg.input(file_path).output(f"{audio_file_path}").run()
        print(f"audio successfully extracted: {audio_file_path}")
        return True
    except Exception as e:
        print(f"error extracting audio: {e}")
    return False

def convert_to_wav(audio_file_path: str) -> str:
    wav_path = audio_file_path.replace(".mp3", ".wav")
    ffmpeg.input(audio_file_path).output(wav_path, ac=1, ar=16000, y=None).run(quiet=True)
    return wav_path


def chunk_wav(audio_file_path: str, id: str) -> list[str]:
    audio = AudioSegment.from_mp3(audio_file_path)
    segment_duration = 5 * 60 * 1000
    chunk_filenames = []

    chunks = [
        audio[i : i + segment_duration] for i in range(0, len(audio), segment_duration)
    ]
    for idx, chunk in enumerate(chunks):
        chunk.export(f"/tmp/{id}_{idx+1}.wav", format="wav")
        chunk_filenames.append(f"{id}_{idx+1}.wav")

    return chunk_filenames

def extract_chunk_number(item):
    match = re.search(r"_(\d+)\.wav$", item[0])
    return int(match.group(1)) if match else float("inf")