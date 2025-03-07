import random
import logging
from app.db.session import SessionLocal
from app.services.video_service import VideoService

logger = logging.getLogger(__name__)

# Список фальшивых действий
FAKE_ACTIONS = [
    "walking", "running", "jumping", "sitting", "standing", 
    "waving", "clapping", "falling", "crouching", "dancing", 
    "turning", "pushing", "pulling", "lifting", "throwing"
]

def detect_actions(video_id: int):
    """Фальшивая функция распознавания действий"""
    try:
        # Выбираем случайные 10 действий
        detected_actions = random.sample(FAKE_ACTIONS, 10)
        
        # Сохраняем их в БД
        db = SessionLocal()
        VideoService.save_video_actions(db, video_id, detected_actions)
        db.close()

        logger.info(f"🎭 Определены действия для видео {video_id}: {detected_actions}")
    except Exception as e:
        logger.error(f"❌ Ошибка при определении действий: {e}")
