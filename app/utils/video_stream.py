import cv2
import time
from pathlib import Path
import logging
from celery import Celery
from app.services.minio_service import MinioService
from app.core.config import settings

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

celery = Celery('video_stream', broker='redis://redis:6379/0')
celery.conf.task_routes = {
    'stream_video': {'queue': 'video_stream_queue'}
}

@celery.task(name='stream_video')
def stream_video_task(video_path: str, bucket_name: str = "video-stream"):
    """Задача для стриминга видео в MinIO"""
    logger.info(f"Запуск задачи stream_video_task с видео: {video_path}")
    
    try:
        minio_service = MinioService()
        
        # Проверяем подключение к MinIO
        logger.info("Проверяем подключение к MinIO...")
        if not minio_service.client.bucket_exists(bucket_name):
            logger.info(f"Бакет {bucket_name} не найден, создаем его...")
            minio_service.client.make_bucket(bucket_name)
        else:
            logger.info(f"Бакет {bucket_name} уже существует")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Не удалось открыть видео: {video_path}")
            return

        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = cv2.VideoWriter_fourcc(*'X','2','6','4')
        frames_per_chunk = fps * 15
        frame_count = 0
        chunk_count = 0
        out = None
        
        logger.info(f"Параметры видео: FPS={fps}, Width={width}, Height={height}")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.info("Достигнут конец видео")
                break

            if frame_count % frames_per_chunk == 0:
                if out is not None:
                    out.release()
                    
                    # Отправляем чанк и удаляем его
                    chunk_path = Path("media/chunks") / f"chunk_{chunk_count - 1}.mp4"
                    object_name = f"{chunk_path.name}"
                    
                    try:
                        logger.info(f"Загружаем чанк {chunk_path} в MinIO как {object_name}...")
                        minio_service.client.fput_object(
                            bucket_name,
                            object_name,
                            str(chunk_path)
                        )
                        logger.info(f"Успешно загружен чанк: {object_name}")
                        chunk_path.unlink()  # Удаляем чанк после загрузки
                        logger.info(f"Удален чанк: {chunk_path}")
                    except Exception as e:
                        logger.error(f"Ошибка при загрузке чанка {chunk_path}: {e}")
                        return
                    
                    time.sleep(15)
                
                chunk_path = Path("media/chunks") / f"chunk_{chunk_count}.mp4"
                chunk_path.parent.mkdir(parents=True, exist_ok=True)
                out = cv2.VideoWriter(str(chunk_path), fourcc, fps, (width, height))
                logger.info(f"Создан новый чанк: {chunk_path}")
                chunk_count += 1
            
            out.write(frame)
            frame_count += 1

        if out is not None:
            out.release()
        cap.release()
        
    except Exception as e:
        logger.error(f"Ошибка в stream_video_task: {e}")
