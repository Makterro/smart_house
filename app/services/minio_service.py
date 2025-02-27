from minio import Minio
from app.core.config import settings
import os
from pathlib import Path

class MinioService:
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT.replace("http://", ""),
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=False
        )

    def download_video(self, bucket_name: str, object_name: str, folder_path: Path) -> bool:
        """Скачивает видео из MinIO"""
        try:
            file_path = folder_path / os.path.basename(object_name)
            folder_path.mkdir(parents=True, exist_ok=True)
            
            self.client.fget_object(bucket_name, object_name, str(file_path))
            return True
        except Exception as e:
            print(f"Error downloading from MinIO: {e}")
            return False 