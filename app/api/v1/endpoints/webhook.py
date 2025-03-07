from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.minio_webhook import MinioWebhook
from app.services.video_service import VideoService
from app.worker import download_video_task
import logging
import os
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/webhook/minio")
async def minio_webhook(
    event: MinioWebhook,
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"Получено событие MinIO: {event.EventName}")

        # Обрабатываем только нужные события
        if event.EventName not in ["s3:ObjectCreated:Put", "s3:ObjectCreated:CompleteMultipartUpload", "s3:ObjectRemoved:Delete"]:
            logger.info(f"Игнорируем событие: {event.EventName}")
            return {"message": "Ignored event"}

        for record in event.Records:
            bucket_name = record.s3.bucket.name
            object_key = record.s3.object.key
            logger.info(f"Обнаружен объект: {object_key} (Bucket: {bucket_name})")
            user_metadata = record.s3.object.userMetadata
            logger.info(f"Метаданные объекта: {user_metadata}")

            # Для событий создания (Put или CompleteMultipartUpload)
            if event.EventName in ["s3:ObjectCreated:Put", "s3:ObjectCreated:CompleteMultipartUpload"]:
                folder_name = VideoService.generate_folder_name(object_key)
                logger.info(f"Сгенерировано имя папки: {folder_name}")

                

                # Преобразуем строки метаданных в datetime
                start_time_str = user_metadata.get("X-Amz-Meta-Start", "Не указано")
                end_time_str = user_metadata.get("X-Amz-Meta-End", "Не указано")

                start_time = datetime.fromisoformat(start_time_str) if start_time_str != "Не указано" else None
                end_time = datetime.fromisoformat(end_time_str) if end_time_str != "Не указано" else None
                src_id = user_metadata.get("X-Amz-Meta-Src", "Не указано")

                logger.info(f"Метаданные объекта: start_time={start_time}, end_time={end_time}, src_id={src_id}")

                # Создаем видео в БД
                video = VideoService.create_video(
                    db=db,
                    filename=os.path.basename(object_key),
                    folder=folder_name,
                    camera_id=src_id,
                    start_time=start_time,
                    end_time=end_time,
                )
                logger.info(f"Создана запись видео в БД: ID {video.id}, Filename {video.filename}, Camera {src_id}")

                # Отправляем задачу на скачивание видео
                download_video_task.delay(bucket_name, object_key, video.id)
                logger.info(f"Отправлена Celery-задача на скачивание видео: {video.id}")

            # Для событий удаления (ObjectRemoved:Delete)
            elif event.EventName == "s3:ObjectRemoved:Delete":
                logger.info(f"Удаление объекта: {object_key}")

                # Ищем видео в БД по ключу объекта
                video = VideoService.get_video_by_filename(db, object_key)
                if video:
                    # Удаляем видео из базы данных
                    VideoService.delete_video(db, video.id)
                    logger.info(f"Запись видео удалена из базы данных: {video.id}")
                else:
                    logger.warning(f"Видео с именем {object_key} не найдено в базе данных.")

        logger.info("Все объекты обработаны успешно")
        return {"message": "Processing started"}

    except Exception as e:
        logger.exception(f"Ошибка при обработке вебхука MinIO: {e}")
        return {"error": str(e)}
