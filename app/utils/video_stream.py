import cv2
import time
from pathlib import Path
import logging
from celery import Celery
from app.services.minio_service import MinioService
from app.core.config import settings

logger = logging.getLogger(__name__)

celery = Celery('video_stream', broker='redis://redis:6379/0')
celery.conf.task_routes = {
    'stream_video': {'queue': 'video_stream_queue'}
}

def split_video(video_path: str, chunk_duration: int = 15):
    """Разделяет видео на чанки заданной длительности"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"Не удалось открыть видео: {video_path}")
        return None

    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    
    frames_per_chunk = fps * chunk_duration
    frame_count = 0
    chunk_count = 0
    chunk_path = None
    out = None

    chunks = []
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % frames_per_chunk == 0:
            if out is not None:
                out.release()
            
            chunk_path = Path("media/chunks") / f"chunk_{chunk_count}.mp4"
            chunk_path.parent.mkdir(parents=True, exist_ok=True)
            
            out = cv2.VideoWriter(str(chunk_path), fourcc, fps, (width, height))
            chunks.append(chunk_path)
            chunk_count += 1

        out.write(frame)
        frame_count += 1

    if out is not None:
        out.release()
    cap.release()

    return chunks

@celery.task(name='stream_video')
def stream_video_task(video_path: str, bucket_name: str = "video-stream"):
    """Задача для стриминга видео в MinIO"""
    try:
        minio_service = MinioService()
        
        # Создаем бакет, если его нет
        if not minio_service.client.bucket_exists(bucket_name):
            minio_service.client.make_bucket(bucket_name)

        while True:  # Бесконечный цикл для повторной загрузки
            # Разделяем видео на чанки
            chunks = split_video(video_path)
            if not chunks:
                logger.error("Не удалось разделить видео на чанки")
                return

            # Загружаем каждый чанк в MinIO
            for chunk_path in chunks:
                try:
                    # Загружаем чанк в MinIO
                    object_name = f"chunks/{chunk_path.name}"
                    minio_service.client.fput_object(
                        bucket_name,
                        object_name,
                        str(chunk_path)
                    )
                    logger.info(f"Загружен чанк: {object_name}")
                    
                    # Ждем 15 секунд перед следующей загрузкой
                    time.sleep(15)
                    
                except Exception as e:
                    logger.error(f"Ошибка при загрузке чанка {chunk_path}: {e}")

            logger.info("Завершен цикл загрузки, начинаем заново")

    except Exception as e:
        logger.error(f"Ошибка в stream_video_task: {e}") 