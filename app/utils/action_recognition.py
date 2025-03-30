import random
import logging
import json
import os.path
import numpy as np
import math
import torch
import cv2

from app.db.session import SessionLocal
from app.services.video_service import VideoService
from collections import defaultdict
from tqdm import tqdm
from typing_extensions import Sequence
from ultralytics.engine.results import Results
from app.core.config import settings
from enum import Enum


logger = logging.getLogger(__name__)

logging.info(f"log cuda is available for action recognition: {torch.cuda.is_available()}")

device = "cuda" if torch.cuda.is_available() else "cpu"
landmark_count = 17  # Число ключевых точек

labels = ["3_WALK", "1_SQUAT", "8_LYING"]

model_action_path = "E9990S29972.pt"
json_path = "keypoints_output.json"

results_path = "results_step2.json"

model = torch.load(model_action_path, map_location=device)
model.eval()

LABELS = ["3_WALK", "1_SQUAT", "8_LYING"]

# "Плохие" действия
BAD_ACTIONS = [
    "8_LYING"
]


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


def extract_sequences(
        skeletons: list[tuple[int, list[tuple[float, float]]]],
        n: int,
) -> list[list[tuple[int, list[tuple[float, float]]]]]:
    sequences = []
    start = None
    for i, data in enumerate(skeletons):
        if data[1]:
            start = i
            break

    if start is None:
        return sequences

    space_counter = 0
    skeletons_length = len(skeletons)
    i = 0
    while start is not None:
        seq: list[tuple[int, list[tuple[float, float]]]] = []
        for i in range(skeletons_length - start):
            data = skeletons[start + i]
            if data[1]:
                seq.append(data)
                space_counter = 0
            else:
                space_counter += 1

            if space_counter >= n:
                sequences.append(seq)
                break

        if seq and (len(sequences) == 0 or seq[0][0] != sequences[-1][0][0]):
            sequences.append(seq)

        start += i
        while not skeletons[start][1]:
            start += 1
            if start >= skeletons_length:
                break

        remain = skeletons_length - start
        if remain == 1 and skeletons[start][1] and skeletons[start][0] != sequences[-1][-1][0]:
            sequences.append([skeletons[start]])
        if remain <= 1:
            start = None

    return sequences


def preprocess_frame(landmarks):
    flattened = []
    for point in landmarks:
        flattened.extend(point[:2])  # Берем только x,y (без confidence)

    if len(flattened) < landmark_count * 2:
        flattened += [0.0] * (landmark_count * 2 - len(flattened))

    return torch.tensor(flattened[:landmark_count * 2], dtype=torch.float32, device=device)


def predict_sequence(
        frame_data: list[list[tuple[float, float]]],
        seq_len=10,
        seq_step=2
) -> dict[str, list[tuple[int, int, float]]]:
    actions = defaultdict(list)
    iteration_step = seq_len * seq_step
    length = len(frame_data)
    steps = math.ceil(length / iteration_step)
    for i in range(steps):
        from_index = i * iteration_step
        to_index = (i + 1) * iteration_step
        selected_frames = frame_data[from_index:to_index:seq_step]
        if len(selected_frames) < round(seq_len * 0.3):
            break

        while len(selected_frames) < seq_len:
            selected_frames.extend(selected_frames[:seq_len-len(selected_frames)])

        sequence_tensors = [preprocess_frame(frame) for frame in selected_frames]

        input_tensor = torch.stack(sequence_tensors).unsqueeze(0)

        with torch.no_grad():
            print(f'{i+1}/{steps}')
            output = model(input_tensor)
            predicted_class = torch.argmax(output).item()
            conf = output[0][predicted_class].item()

        actions[labels[predicted_class]].append((from_index, to_index, conf))
    return actions


def detect_actions(video_id: int, skeletons, fps: int):
    """Функция распознавания действий через нейронку"""
    try:
        detected_actions = []

        skeletons_sequences = extract_sequences(skeletons, 1)

        result = defaultdict(list)

        # Обрабатываем последовательности
        for sequence in skeletons_sequences:
            actions = predict_sequence([skeleton for i, skeleton in sequence], seq_step=settings.SEQ_STEP)
            sequence_length = len(sequence)

            # Собираем кадры и классы с оценками
            class_durations = defaultdict(float)  # Длительность каждого класса
            action_data_list = []

            # Собираем все данные для каждого класса
            for classname, action_list in actions.items():
                for from_i, to_i, conf in action_list:
                    start_frame = sequence[from_i][0]
                    end_frame = sequence[min(to_i, sequence_length - 1)][0]

                    # Преобразуем кадры в секунды
                    start_time = start_frame / fps
                    end_time = end_frame / fps
                    duration = end_time - start_time  # Продолжительность действия в секундах

                    # Обновляем длительность действия для данного класса
                    class_durations[classname] += duration

                    # Добавляем предсказания в список
                    action_data = {
                        "class": classname,
                        "start_frame": start_frame,
                        "end_frame": end_frame,
                        "start_time": start_time,
                        "end_time": end_time,
                        "confidence": conf,
                        "Realy": False  # Изначально Realy False
                    }

                    action_data_list.append(action_data)

            # Сортируем по start_frame
            action_data_list.sort(key=lambda x: x['start_frame'])

            # Проверяем для каждой записи, есть ли 3 подряд идущих записи с одинаковым классом
            for i, action_data in enumerate(action_data_list):
                class_name = action_data["class"]
                # Проверяем 3 подряд идущих кадра с одинаковым классом
                consecutive_count = 0

                # Проверяем предыдущие кадры
                for j in range(i-1, max(i-settings.FRAMES_TO_CHECK_AROUND, -1), -1):  # Проверяем до N предыдущих кадров
                    if action_data_list[j]["class"] == class_name:
                        consecutive_count += 1
                    else:
                        break

                # Проверяем следующие кадры
                for j in range(i+1, min(i+settings.FRAMES_TO_CHECK_AROUND, len(action_data_list))):  # Проверяем до N следующих кадров
                    if action_data_list[j]["class"] == class_name:
                        consecutive_count += 1
                    else:
                        break

                # Если найдено заданное количество подряд идущих кадров с одинаковым классом, помечаем как Realy: true
                if consecutive_count >= settings.CONSECUTIVE_FRAMES_THRESHOLD- 1:  # Мы включаем сам текущий кадр
                    action_data["Realy"] = True
                else:
                    action_data["Realy"] = False

                # Добавляем в итоговый результат
                result[action_data["start_frame"]].append(action_data)

                # Проверяем, является ли действие опасным и подтвержденным
                if classname in BAD_ACTIONS and action_data["Realy"]:
                    detected_actions.append(action_data)

        # Сортировка по start_frame
        sorted_result = dict(sorted(result.items()))

        # Перепишем результат в файл
        with open(results_path, 'w') as fw:
            json.dump(sorted_result, fw, indent=4)

        # Сохраняем в БД
        db = SessionLocal()
        VideoService.save_video_actions(db, video_id, detected_actions)
        db.close()

        if detected_actions:
            logger.info(f"🚨 Найдены подозрительные действия для видео {video_id}: {len(detected_actions)}")
        else:
            logger.info(f"✅ Никаких подозрительных действий в видео {video_id} не обнаружено")

    except Exception as e:
        logger.error(f"❌ Ошибка при определении действий: {e}")
        logger.exception("Полная информация об ошибке")
        raise   