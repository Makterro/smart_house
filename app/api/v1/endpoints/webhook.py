from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.minio_webhook import MinioWebhook
from app.services.video_service import VideoService
from app.worker import download_video_task
import logging
import os

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/webhook/minio")
async def minio_webhook(
    event: MinioWebhook,
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"Получено событие MinIO: {event.EventName}")

        if event.EventName not in ["s3:ObjectCreated:Put", "s3:ObjectCreated:CompleteMultipartUpload"]:
            logger.info(f"Игнорируем событие: {event.EventName}")
            return {"message": "Ignored event"}

        for record in event.Records:
            bucket_name = record.s3.bucket.name
            object_key = record.s3.object.key
            logger.info(f"Обнаружен новый объект в MinIO: {object_key} (Bucket: {bucket_name})")

            # Определяем ID камеры из имени файла (например, camera_1_timestamp.mp4)
            try:
                camera_id = int(object_key.split('_')[1])
            except (IndexError, ValueError):
                camera_id = None
                logger.warning(f"Не удалось определить ID камеры из имени файла: {object_key}")

            folder_name = VideoService.generate_folder_name(object_key)
            logger.info(f"Сгенерировано имя папки: {folder_name}")

            # Создаем видео в БД и получаем объект video
            video = VideoService.create_video(
                db=db,
                filename=os.path.basename(object_key),
                folder=folder_name,
                camera_id=camera_id
            )
            logger.info(f"Создана запись видео в БД: ID {video.id}, Filename {video.filename}, Camera {camera_id}")

            # Отправляем задачу для скачивания видео
            download_video_task.delay(bucket_name, object_key, video.id)
            logger.info(f"Отправлена Celery-задача на скачивание видео: {video.id}")

        logger.info("Все объекты обработаны успешно")
        return {"message": "Processing started"}

    except Exception as e:
        logger.exception(f"Ошибка при обработке вебхука MinIO: {e}")
        return {"error": str(e)}
