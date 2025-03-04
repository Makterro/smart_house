import os
import cv2
import logging
import torch
from ultralytics import YOLO
from pathlib import Path
import json
import subprocess
import shutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка модели позы YOLOv8
MODEL_PATH = "yolov8x-pose.pt"
yolo_model = YOLO(MODEL_PATH)

def process_video(video_name: str, output_name: str, video_folder: str, frame_step="fps"):
    """Обработка видео: детекция и сохранение результата"""
    try:
        video_path = Path("media") / video_folder / video_name
        output_path = Path("media") / video_folder / output_name
        frames_dir = Path("media") / video_folder / "frames"
        temp_frames_dir = Path("media") / video_folder / "temp_frames"

        # Создаем необходимые директории
        frames_dir.mkdir(exist_ok=True)
        temp_frames_dir.mkdir(exist_ok=True)

        logger.info(f"🚀 Начинаем обработку видео: {video_path}")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            logger.error(f"❌ Не удалось открыть видеофайл: {video_path}")
            return None

        fps = int(cap.get(cv2.CAP_PROP_FPS))
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

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

        processed_frames = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % step == 0:
                results = yolo_model(source=frame, conf=0.3, imgsz=640, device='0')
                
                annotated_frame = results[0].plot()
                # Сохраняем обработанный кадр во временную директорию
                frame_filename = f"frame_{processed_frames:06d}.jpg"
                cv2.imwrite(str(temp_frames_dir / frame_filename), annotated_frame)
                processed_frames += 1

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

        # Собираем видео из кадров с помощью ffmpeg
        try:
            ffmpeg_cmd = [
                'ffmpeg',
                '-framerate', str(fps),
                '-i', str(temp_frames_dir / 'frame_%06d.jpg'),
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                '-y',
                str(output_path)
            ]
            logger.info("🎥 Собираем видео с помощью ffmpeg...")
            subprocess.run(ffmpeg_cmd, check=True)
            logger.info(f"✅ Видео успешно создано: {output_path}")
            return output_name
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Ошибка при создании видео через ffmpeg: {e}")
            return None
        finally:
            # Удаляем временную директорию с кадрами
            if temp_frames_dir.exists():
                shutil.rmtree(temp_frames_dir)
                logger.info("🧹 Временные файлы удалены")
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке видео: {e}")
        return None
