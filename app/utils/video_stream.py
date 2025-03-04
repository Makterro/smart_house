import cv2
import time
from pathlib import Path
import logging
from celery import Celery
import subprocess
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
def stream_video_task(video_path: str, bucket_name: str = "video-stream", camera_id: int = 1):
    """Задача для стриминга видео в MinIO"""
    logger.info(f"Запуск задачи stream_video_task с видео: {video_path} для камеры {camera_id}")
    
    try:
        minio_service = MinioService()
        
        # Проверяем подключение к MinIO
        logger.info("Проверяем подключение к MinIO...")
        if not minio_service.client.bucket_exists(bucket_name):
            logger.info(f"Бакет {bucket_name} не найден, создаем его...")
            minio_service.client.make_bucket(bucket_name)
        else:
            logger.info(f"Бакет {bucket_name} уже существует")

        # Получаем длительность видео
        probe_cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        duration = float(subprocess.check_output(probe_cmd).decode().strip())
        logger.info(f"Длительность видео: {duration} секунд")

        chunk_duration = 15
        chunk_count = 0
        current_time = 0

        while current_time < duration:
            try:
                # Создаем путь для чанка с ID камеры
                chunk_filename = f"camera_{camera_id}_chunk_{chunk_count}.mp4"
                chunk_path = Path("media/chunks") / chunk_filename
                chunk_path.parent.mkdir(parents=True, exist_ok=True)

                # Вырезаем 15-секундный чанк
                ffmpeg_cmd = [
                    'ffmpeg',
                    '-ss', str(current_time),
                    '-i', video_path,
                    '-t', str(chunk_duration),
                    '-c:v', 'libx264',
                    '-preset', 'medium',
                    '-crf', '23',
                    '-y',
                    str(chunk_path)
                ]
                logger.info(f"Создаем чанк {chunk_count} начиная с {current_time} секунды для камеры {camera_id}...")
                subprocess.run(ffmpeg_cmd, check=True)

                # Отправляем чанк в MinIO
                object_name = chunk_filename
                logger.info(f"Загружаем чанк {chunk_path} в MinIO как {object_name}...")
                minio_service.client.fput_object(
                    bucket_name,
                    object_name,
                    str(chunk_path)
                )
                logger.info(f"Успешно загружен чанк: {object_name}")

                # Удаляем локальный файл
                chunk_path.unlink()
                logger.info(f"Удален локальный чанк: {chunk_path}")

                # Ждем 15 секунд перед следующим чанком
                time.sleep(15)

                current_time += chunk_duration
                chunk_count += 1

            except subprocess.CalledProcessError as e:
                logger.error(f"Ошибка FFmpeg при создании чанка {chunk_count}: {e}")
                break
            except Exception as e:
                logger.error(f"Ошибка при обработке чанка {chunk_count}: {e}")
                break

    except Exception as e:
        logger.error(f"Ошибка в stream_video_task: {e}")
    
    finally:
        # Запускаем задачу заново после завершения
        logger.info("🔄 Перезапускаем обработку видео...")
        stream_video_task.delay(video_path, bucket_name, camera_id)
