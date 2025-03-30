import json
import os
import torch
import numpy as np
from net.main import PlainSequence

# Конфигурация (должна совпадать с обучением)
device = "cuda" if torch.cuda.is_available() else "cpu"
seq_len = 10  # Длина последовательности
seq_step = 2  # Шаг между кадрами
landmark_count = 17  # Число ключевых точек
num_classes = 3  # Количество классов

# Пути
model_path = "E9990S29972.pt"
json_path = "keypoints_output.json"

# Загрузка модели
model = torch.load(model_path, map_location=device)
model.eval()

# Список классов
labels = ["3_WALK", "1_SQUAT", "8_LYING"]


def load_json_data(json_path):
    """Загружает JSON-файл с ключевыми точками"""
    with open(json_path) as f:
        return json.load(f)


def preprocess_frame(landmarks):
    """
    Преобразует ключевые точки в тензор.
    Формат: [landmark_count * 2] (x, y для каждой точки)
    """
    flattened = []
    for point in landmarks:
        flattened.extend(point[:2])  # Берем только x,y (без confidence)

    # Если точек меньше, заполняем нулями
    if len(flattened) < landmark_count * 2:
        flattened += [0.0] * (landmark_count * 2 - len(flattened))

    return torch.tensor(flattened[:landmark_count * 2], dtype=torch.float32, device=device)


def predict_sequence(frame_data, seq_len=10, seq_step=2):
    """
    Предсказывает класс для последовательности кадров
    frame_data: словарь {имя_файла: ключевые_точки}
    """
    # Сортируем кадры по имени и выбираем последовательность
    sorted_frames = sorted(frame_data.items(), key=lambda x: x[0])
    selected_frames = [frame[1][0] for frame in sorted_frames[::seq_step]]

    # Если кадров меньше, чем нужно, повторяем их
    while len(selected_frames) < seq_len:
        selected_frames.extend(selected_frames)
    selected_frames = selected_frames[:seq_len]

    sequence_tensors = [preprocess_frame(frame) for frame in selected_frames]

    # Добавляем batch-размерность [1, seq_len, landmark_count*2]
    input_tensor = torch.stack(sequence_tensors).unsqueeze(0)

    # Проверяем форму входного тензора
    print("Input tensor shape:", input_tensor.shape)

    with torch.no_grad():
        output = model(input_tensor)
        predicted_class = torch.argmax(output).item()

    return labels[predicted_class]


if __name__ == "__main__":
    frame_data = load_json_data(json_path)

    # Предсказание
    prediction = predict_sequence(frame_data, seq_len, seq_step)
    print(f"Predicted class: {prediction}")