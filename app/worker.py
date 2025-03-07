from celery import Celery
from app.core.config import settings
from app.services.minio_service import MinioService
from app.services.video_service import VideoService
from app.utils.video_processing import process_video
from app.db.session import SessionLocal
import logging

logger = logging.getLogger(__name__)

celery = Celery('tasks', broker='redis://redis:6379/0')

# Настройка очередей
celery.conf.task_routes = {
    'download_video': {'queue': 'download_queue'},
    'process_video': {'queue': 'video_processing_queue'}
}

@celery.task(name='download_video')
def download_video_task(bucket_name: str, object_name: str, video_id: int):
    """Скачивает видео из MinIO и запускает обработку"""
    try:
        db = SessionLocal()
        video = VideoService.get_video(db, video_id)
        if not video:
            raise Exception(f"Video {video_id} not found")

        folder_path = settings.MEDIA_DIR / video.folder
        
        minio_service = MinioService()
        if minio_service.download_video(bucket_name, object_name, folder_path):
            logger.info(f"Video downloaded successfully: {video_id}")
            # Запускаем обработку в отдельной очереди
            process_video_task.delay(video_id)
        else:
            logger.error(f"Failed to download video: {video_id}")
    
    except Exception as e:
        logger.error(f"Error in download_video_task: {e}")
    finally:
        db.close()

@celery.task(name='process_video')
def process_video_task(video_id: int):
    """Обрабатывает видео"""
    try:
        db = SessionLocal()
        video = VideoService.get_video(db, video_id)
        if not video:
            raise Exception(f"Video {video_id} not found")

        # Генерируем имя для обработанного файла
        processed_filename = f"processed_{video.filename}"
        
        # Обрабатываем видео
        result = process_video(
            video_id,                 # video_id
            video.filename,           # video_name
            processed_filename,       # output_name
            video.folder              # video_folder
        )
        
        # Обновляем запись в БД только если обработка прошла успешно
        if result:
            video.processed_filename = processed_filename
            db.commit()
            logger.info(f"Video processed successfully: {video_id}")
        else:
            logger.error(f"Failed to process video: {video_id}")

    except Exception as e:
        logger.error(f"Error in process_video_task: {e}")
    finally:
        db.close() 