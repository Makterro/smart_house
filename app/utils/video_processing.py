import os
import cv2
import logging
from ultralytics import YOLO
from pathlib import Path
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.services.video_service import VideoService
from app.services.minio_service import MinioService
from app.models.video import VideoStatus
from app.utils.action_recognition import detect_actions
from app.utils.send_webhook import send_webhook

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка модели YOLOv8 Pose
MODEL_PATH = "yolov8x-pose.pt"
yolo_model = YOLO(MODEL_PATH)

def process_video(video_id: int, video_name: str, output_name: str, video_folder: str, frame_step="fps", retry=False):
    """Обработка видео: детекция и сохранение результата"""
    try:
        video_path = Path("media") / video_folder / video_name
        output_path = Path("media") / video_folder / output_name

        logger.info(f"🚀 Начинаем обработку видео: {video_path}")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            logger.error(f"❌ Не удалось открыть видеофайл: {video_path}")
            return None

        fps = int(cap.get(cv2.CAP_PROP_FPS))

        # Выбор шага обработки кадров
        step = 1 if retry else (fps if frame_step == "fps" else frame_step)

        frame_count = 0
        skeletons = []  # Список для сохранения найденных скелетов

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % step == 0:
                results = yolo_model(source=frame, conf=0.3, imgsz=640, device='0')

                for result in results:
                    if result.keypoints is not None:
                        keypoints = result.keypoints.cpu().numpy().tolist()
                        skeletons.append({"frame": frame_count, "keypoints": keypoints})

            frame_count += 1

        cap.release()

        # Работа с БД
        db = SessionLocal()

        if skeletons:
            logger.info(f"✅ Найдено {len(skeletons)} кадров со скелетами в {video_name}")

            minio_service = MinioService()

            # Если это первый проход, меняем статус и перезапускаем обработку
            if not retry:
                VideoService.update_video_status(db, video_id, VideoStatus.FIND_SKELET)
                process_video(video_id, video_name, output_name, video_folder, frame_step="all", retry=True)
            else:
                # Если это повторный проход — отправляем на детекцию и сохраняем все скелеты в БД
                detect_actions(video_id)
                VideoService.update_video_skeletons(db, video_id, skeletons)
                minio_service.update_video_metadata(video_folder, video_name, skeletons_found = True)
                
                # Удаляем файл видео
                try:
                    os.remove(video_path)
                    logger.info(f"🗑️ Видео удалено: {video_path}")
                except Exception as e:
                    logger.error(f"⚠️ Ошибка при удалении видео {video_path}: {e}")

                VideoService.update_video_status(db, video_id, VideoStatus.COMPLETED)

                video = VideoService.get_video(db, video_id)
                send_webhook(video)

        else:
            minio_service.update_video_metadata(video_folder, video_name, skeletons_found = False)

        db.close()


    except Exception as e:
        logger.error(f"❌ Ошибка при обработке видео: {e}")
        return None
