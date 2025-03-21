import os
import logging

from minio import Minio
from minio.error import S3Error
from app.core.config import settings
from typing_extensions import Any
from pathlib import Path
from minio.commonconfig import CopySource, Tags


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MinioService:
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
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
            logging.ERROR(f"Error downloading from MinIO: {e}")
            return False 
    
    def set_tags(
            self,
            bucket_name: str,
            object_name: str,
            tags: dict[str, Any]
    ):
        try:
            object_tags = Tags.new_object_tags()
            for k, v in tags.items():
                object_tags[k] = str(v)

            self.client.set_object_tags(bucket_name, object_name, object_tags)
            logging.INFO(f"✅ Метаданные обновлены для {object_name}")
        except S3Error as e:
            logging.ERROR(f"⚠️ Ошибка при установке тегов объекта MinIO: {e}")
            return False