import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SUBSTREAM_API_URL: str = os.getenv("SUBSTREAM_API_URL")
    PROCESSOR_TOKEN: str = os.getenv("PROCESSOR_TOKEN")
    S3_ACCESS_KEY: str = os.getenv("S3_ACCESS_KEY")
    S3_SECRET_KEY: str = os.getenv("S3_SECRET_KEY")
    S3_ENDPOINT: str = os.getenv("S3_ENDPOINT")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME")
    S3_REGION: str = os.getenv("S3_REGION")
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL")