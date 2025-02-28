import os
import cv2
import logging
import torch
from ultralytics import YOLO
from pathlib import Path
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка модели позы YOLOv8
MODEL_PATH = "yolov8x-pose.pt"
yolo_model = YOLO(MODEL_PATH)

def process_video(video_name: str, output_name: str, video_folder: str, frame_step="fps"):
    """Обработка видео: детекция и сохранение результата"""
    video_path = Path("media") / video_folder / video_name
    output_path = Path("media") / video_folder / output_name
    frames_dir = Path("media") / video_folder / "frames"

    frames_dir.mkdir(exist_ok=True)

    logger.info(f"🚀 Начинаем обработку видео: {video_path}")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        logger.error(f"❌ Не удалось открыть видеофайл: {video_path}")
        return

    fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'X','2','6','4')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (frame_width, frame_height))

    frame_count = 0
    if frame_step == "all":
        step = 1  # Каждый кадр
    elif frame_step == "fps":
        step = fps  # Каждую секунду
    elif isinstance(frame_step, int) and frame_step > 0:
        step = frame_step  # Каждый N-й кадр
    else:
        logger.warning("⚠️ Некорректное значение frame_step, используем 'fps'")
        step = fps

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % step == 0:
            results = yolo_model(source=frame, conf=0.3, imgsz=640, device='0')
            
            annotated_frame = results[0].plot()
            out.write(annotated_frame)

            for result in results:
                boxes = result.boxes.xyxy.cpu().numpy()
                
                for i, (x1, y1, x2, y2) in enumerate(boxes):
                    x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
                    person_crop = frame[y1:y2, x1:x2]

                    if person_crop.size > 0:
                        crop_filename = f"person_{frame_count}_{i}.jpg"
                        cv2.imwrite(str(frames_dir / crop_filename), person_crop)
                        logger.info(f"🧍 Вырезано изображение: {crop_filename}")

        frame_count += 1

    cap.release()
    out.release()

    logger.info(f"✅ Обработка завершена, результат сохранен: {output_path}")
    return output_name
