import boto3
from botocore.config import Config


class S3Client:
    def __init__(self, config):
        custom_config = Config(retries={"max_attempts": 5, "mode": "standard"})
        self.client = boto3.client(
            "s3",
            aws_access_key_id=config.S3_ACCESS_KEY,
            aws_secret_access_key=config.S3_SECRET_KEY,
            endpoint_url=config.S3_ENDPOINT,
            region_name=config.S3_REGION,
            config=custom_config,
        )
        self.bucket_name = config.S3_BUCKET_NAME

    def upload_file(self, file_path, object_name):
        print(f"uploading s3 file {file_path}")
        try:
            self.client.upload_file(file_path, self.bucket_name, object_name)
            return True
        except Exception as e:
            print(f"error uploading s3 file {file_path} ({e})")
        return False

    def download_file(self, object_name, file_path) -> bool:
        print(f"downloading s3 file {file_path}")
        try:
            self.client.download_file(self.bucket_name, object_name, file_path)
            return True
        except Exception as e:
            print(f"error downloading s3 file {file_path} ({e})")
        return False

    def delete_file(self, object_name) -> bool:
        print(f"deleting s3 file {object_name}")
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=object_name)
            return True
        except Exception as e:
            print(f"error deleting s3 file {object_name} ({e})")
            return False