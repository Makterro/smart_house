import requests
from datetime import datetime
import uuid
import logging
from app.models.video import Video
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_webhook(video: Video, webhook_url: str):
    """Отправка вебхука с данными видео"""
    camera_id = video.camera_id  # ID камеры
    video_id = video.id # ID видео
    start_time = video.start_time  # Время начала записи
    end_time = video.end_time  # Время окончания записи
    actions = video.actions if video.actions else None  # Извлекаем список действий из поля 'actions'

    if not webhook_url:
        logger.warning(f"⚠️ Вебхук URL не передан для видео {video.id}")
        return

    # Проверяем, что действия действительно были обнаружены
    if not actions:
        logger.info(f"❌ Не найдено действий в видео {video.id}")
        return

    payload = {
        "camera_id": str(camera_id),  # ID камеры (или UUID)
        "video_id": video_id,   # ID видео
        "people": [],  # Пустой список людей (пока что не используется)
        "actions": actions,  # Список действий из базы данных
        "dt_from": start_time.isoformat(),  # Время начала
        "dt_to": end_time.isoformat()  # Время окончания
    }

    try:
        # Отправляем вебхук
        response = requests.post(webhook_url, json=payload, timeout=3)
        if response.status_code == 200:
            logger.info(f"✅ Вебхук успешно отправлен для видео {video.id}")
        else:
            logger.error(f"❌ Ошибка при отправке вебхука для видео {video.id} status: {response.status_code}")
            
    except Exception as e:
        logger.error(f"⚠️ Ошибка при отправке вебхука: {e}")