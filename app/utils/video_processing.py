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
from tqdm import tqdm
from ultralytics.engine.results import Results


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

yolo_model = YOLO(settings.YOLO_MODEL_PATH)
logging.info(f"log cuda is available: {torch.cuda.is_available()}")
logging.info(f"YOLO model device: {yolo_model.device}")

def transform_result_xy_normalized(prediction: Results) -> list[tuple[float, float]]: 
    bbox = prediction.boxes.xyxyn[0].cpu().numpy().tolist()
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    keypoints = prediction.keypoints.xyn[0].cpu().numpy().tolist()
    return list(
        map(
            lambda p: (
                max(0, (p[0] - bbox[0]) / width),
                max(0, (p[1] - bbox[1]) / height),
            ),
            keypoints
        )
    )

target_transform_result = transform_result_xy_normalized

def process_video(video_path: str, frame_step="fps") -> tuple[list[tuple[int, list[tuple[float, float]]]], int]:
    """Выполняет предикт на видео и возвращает найденные скелеты."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.info(f"❌ Не удалось открыть видеофайл: {video_path}")
        return [], 0

    fps = int(round(cap.get(cv2.CAP_PROP_FPS)))
    length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    step = fps if frame_step == "fps" else 1
    skeletons: list[tuple[int, list[tuple[float, float]]]] = []
    frame_number = 0

    for _ in tqdm(range(length)):
        retrieved = cap.grab()
        if not retrieved:
            break

        if frame_number % step == 0:
            _, frame = cap.retrieve()
            results = list(yolo_model.predict(frame, 0.5, verbose=False))
            if len(results[0].boxes.xyxy) == 0:
                skeletons.append({"frame": frame_number, "keypoints": []})
            else:
                keypoints = target_transform_result(results[0])
                skeletons.append({"frame": frame_number, "keypoints": keypoints})
        
        frame_number += 1

    cap.release()
    return skeletons, fps

def process_video_with_different_fps(video_id: int, video_name: str, video_folder: str):
    """Функция управляет процессом обработки видео, вызывая предикт дважды с разными FPS в зависимости от найденных скелетов."""
    try:
        db = SessionLocal()
        VideoService.update_video_status(db, video_id, VideoStatus.PROCESSING)
        video_path = str(settings.MEDIA_DIR / video_folder / video_name)

        logger.info(f"🚀 Начинаем обработку видео: {video_path}")

        # Первый проход (fps)
        skeletons_fps, fps = process_video(video_path, frame_step="fps")

        minio_service = MinioService()
        object_name = f"{video_folder}/{video_name}"
        if skeletons_fps:
            logger.info(f"✅ Найдено {len(skeletons_fps)} кадров со скелетами в {video_name}, начинаем повторную обработку")
            
            # Второй проход (all)
            skeletons_all, fps = process_video(video_path, frame_step="all")
            logger.info(f"✅ Найдено {len(skeletons_all)} кадров со скелетами в {video_name} за второй прогон")

            detect_actions(video_id, skeletons_all, fps)

            minio_service.set_tags(settings.MINIO_BUCKET_NAME, object_name, {'type': 'significant'})

            try:
                os.remove(video_path)
                logger.info(f"🗑️ Видео файл удален: {video_path}")
            except Exception as e:
                logger.error(f"⚠️ Ошибка при удалении видео файла {video_path}: {e}")

            video = VideoService.get_video(db, video_id)
            send_webhook(video, settings.MANAGMENT_SERVICE_ENDPOINT_WEBHOOK)

        else:
            minio_service.set_tags(settings.MINIO_BUCKET_NAME, object_name, {'type': 'insignificant'})
            
        VideoService.update_video_status(db, video_id, VideoStatus.COMPLETED)
        db.close()

    except Exception as e:
        logger.error(f"❌ Ошибка при обработке видео: {e}")
        return None