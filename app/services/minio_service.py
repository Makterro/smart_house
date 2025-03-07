from minio import Minio
from minio.error import S3Error
from app.core.config import settings
import os
from pathlib import Path

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
            print(f"Error downloading from MinIO: {e}")
            return False 
        
    def update_video_metadata(self, bucket_name: str, object_name: str, skeletons_found: bool):
        """Обновляет метаданные видео в MinIO (status=processed, type=raw или processed)"""
        try:
            # Получаем текущие метаданные
            obj_stat = self.client.stat_object(bucket_name, object_name)
            current_metadata = obj_stat.metadata

            # Обновляем метаданные: если скелеты найдены, type = processed, иначе raw
            new_metadata = {
                **current_metadata,  # Сохраняем существующие метаданные
                "X-Amz-Meta-Status": "processed",
                "X-Amz-Meta-Type": "processed" if skeletons_found else "raw"
            }

            # Копируем объект с обновленными метаданными
            self.client.copy_object(
                bucket_name,
                object_name,
                f"/{bucket_name}/{object_name}",
                metadata=new_metadata,
                metadata_directive="REPLACE"
            )

            print(f"✅ Метаданные обновлены для {object_name}: {new_metadata}")
            return True
        except S3Error as e:
            print(f"⚠️ Ошибка при обновлении метаданных MinIO: {e}")
            return False