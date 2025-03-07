import random
import logging
from app.db.session import SessionLocal
from app.services.video_service import VideoService

logger = logging.getLogger(__name__)

# "Плохие" действия
BAD_ACTIONS = [
    "fight", "aggression", "weapon_detected", "vandalism", 
    "harassment", "theft", "breaking_objects", "loitering", 
    "trespassing", "dangerous_behavior"
]

def detect_actions(video_id: int):
    """Функция распознавания действий с 50% шансом"""
    try:
        detected_actions = []

        # 50% вероятность, что будут найдены действия
        if random.random() < 0.5:
            # Если найдены, выбираем от 2 до 5 случайных действий
            detected_actions = random.sample(BAD_ACTIONS, random.randint(2, 5))

        # Сохраняем в БД
        db = SessionLocal()
        VideoService.save_video_actions(db, video_id, detected_actions)
        db.close()

        if detected_actions:
            logger.info(f"🚨 Найдены подозрительные действия для видео {video_id}: {detected_actions}")
        else:
            logger.info(f"✅ Никаких подозрительных действий в видео {video_id} не обнаружено")

    except Exception as e:
        logger.error(f"❌ Ошибка при определении действий: {e}")
