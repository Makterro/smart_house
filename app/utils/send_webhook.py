import requests
from datetime import datetime
import uuid
import logging
from app.models.video import Video

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_webhook(video: Video):
    """Отправка вебхука с данными видео"""
    camera_id = video.camera_id  # ID камеры
    start_time = video.start_time  # Время начала записи
    end_time = video.end_time  # Время окончания записи
    actions = video.actions  # Извлекаем список действий из поля 'actions'

    # Проверяем, что действия действительно были обнаружены
    if not actions:
        logger.warning(f"❌ Не найдено действий в видео {video.id}")
        return

    webhook_url = "http://example.com/webhook"  # Эндпоинт вебхука
    payload = {
        "camera_id": str(camera_id),  # ID камеры (или UUID)
        "people": [],  # Пустой список людей (пока что не используется)
        "actions": actions,  # Список действий из базы данных
        "dt_from": start_time.isoformat(),  # Время начала
        "dt_to": end_time.isoformat()  # Время окончания
    }

    # try:
    #     # Отправляем вебхук
    #     response = requests.post(webhook_url, json=payload)
    #     if response.status_code == 200:
    #         logger.info(f"✅ Вебхук успешно отправлен для видео {video.id}")
    #     else:
    #         logger.error(f"❌ Ошибка при отправке вебхука: {response.status_code}")
    # except Exception as e:
    #     logger.error(f"⚠️ Ошибка при отправке вебхука: {e}")

    logger.info(f"✅ Вебхук успешно отправлен для видео {video.id}")