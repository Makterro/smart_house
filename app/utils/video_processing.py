import os
import cv2
import logging
import torch

from ultralytics import YOLO
from pathlib import Path
from app.db.session import SessionLocal
from app.services.video_service import VideoService
from app.services.minio_service import MinioService
from app.models.video import VideoStatus
from app.utils.action_recognition import detect_actions
from app.utils.send_webhook import send_webhook
from app.core.config import settings


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка модели YOLOv8 Pose
MODEL_PATH = "yolov8x-pose.pt"
yolo_model = YOLO(MODEL_PATH)
logging.info(f"log cuda is available: {torch.cuda.is_available()}")
logging.info(f"YOLO model device: {yolo_model.device}")

def process_video(video_path: str, frame_step="fps"):
    """Выполняет предикт на видео и возвращает найденные скелеты."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"❌ Не удалось открыть видеофайл: {video_path}")
        return []

    fps = int(cap.get(cv2.CAP_PROP_FPS))
    
    if frame_step == "fps":
        step = fps # Анализировать 1 кадр в секунду
    elif frame_step == "all":
        step = 1  # Анализировать каждый кадр

    frame_count = 0
    skeletons = []

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % step == 0:
            results = yolo_model(source=frame, conf=0.3, imgsz=640, device='0')
            for result in results:
                if result.keypoints is not None:
                    keypoints = result.keypoints.xy.cpu().numpy().tolist()
                    skeletons.append({"frame": frame_count, "keypoints": keypoints})

        frame_count += 1

    cap.release()
    return skeletons

def process_video_with_different_fps(video_id: int, video_name: str, video_folder: str):
    """Функция управляет процессом обработки видео, вызывая предикт дважды с разными FPS в зависимости от найденных скелетов."""
    try:
        db = SessionLocal()
        VideoService.update_video_status(db, video_id, VideoStatus.PROCESSING)
        video_path = str(Path("media") / video_folder / video_name)

        logger.info(f"🚀 Начинаем обработку видео: {video_path}")

        # Первый проход (fps)
        skeletons_fps = process_video(video_path, frame_step="fps")
        
        if skeletons_fps:
            logger.info(f"✅ Найдено {len(skeletons_fps)} кадров со скелетами в {video_name}, начинаем повторную обработку")
            
            # Второй проход (all)
            skeletons_all = process_video(video_path, frame_step="all")
            logger.info(f"✅ Найдено {len(skeletons_all)} кадров со скелетами в {video_name} за второй прогон")

            VideoService.update_video_skeletons(db, video_id, skeletons_all)
            detect_actions(video_id)

            minio_service = MinioService()
            minio_service.set_tags(settings.MINIO_BUCKET_NAME, video_name, {'type': 'significant'})

            try:
                os.remove(video_path)
                logger.info(f"🗑️ Видео файл удален: {video_path}")
            except Exception as e:
                logger.error(f"⚠️ Ошибка при удалении видео файла {video_path}: {e}")

            video = VideoService.get_video(db, video_id)
            send_webhook(video, settings.MANAGMENT_SERVICE_ENDPOINT_WEBHOOK)

        else:
            minio_service.set_tags(settings.MINIO_BUCKET_NAME, video_name, {'type': 'insignificant'})
            
        VideoService.update_video_status(db, video_id, VideoStatus.COMPLETED)
        db.close()

    except Exception as e:
        logger.error(f"❌ Ошибка при обработке видео: {e}")
        return None