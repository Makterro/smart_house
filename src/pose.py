import cv2
import json
from ultralytics import YOLO

# Загрузка предобученной модели YOLO-Pose
model = YOLO("yolov8x-pose.pt")  # Модель yolov8x-pose

# Путь к изображению
image_path = "A_14898_0.png"

output_json_path = "keypoints_output.json"

# Список пар ключевых точек для построения костей (не используется для сохранения JSON)
skeleton = [
    (0, 1),  # нос -> левый глаз
    (0, 2),  # нос -> правый глаз
    (1, 3),  # левый глаз -> левое ухо
    (2, 4),  # правый глаз -> правое ухо
    (5, 7),  # левое плечо -> левый локоть
    (7, 9),  # левый локоть -> левое запястье
    (6, 8),  # правое плечо -> правый локоть
    (8, 10),  # правый локоть -> правое запястье
    (5, 6),  # левое плечо -> правое плечо
    (5, 11),  # левое плечо -> левое бедро
    (6, 12),  # правое плечо -> правое бедро
    (11, 13),  # левое бедро -> левое колено
    (13, 15),  # левое колено -> левая лодыжка
    (12, 14),  # правое бедро -> правое колено
    (14, 16)  # правое колено -> правая лодыжка
]


def save_keypoints_to_json(keypoints_dict, output_json_path):
    """
    Сохраняет ключевые точки в JSON-файл.
    keypoints_dict: словарь {имя_изображения: [[x1, y1], [x2, y2], ...]}
    """
    with open(output_json_path, "w") as f:
        json.dump(keypoints_dict, f, indent=4)


def main():
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Image not found at {image_path}")

    results = model(image)

    # Словарь для хранения ключевых точек
    keypoints_dict = {}

    # Обработка результатов
    for result in results:
        keypoints_data = result.keypoints.data.cpu().numpy()
        if len(keypoints_data) == 0:
            print("No keypoints detected.")
            continue

        # Берем первого человека
        keypoints = keypoints_data[0]
        keypoints = [[float(kp[0]), float(kp[1])] for kp in keypoints]  # Преобразуем в формат списка

        keypoints_dict[image_path] = [keypoints]

    save_keypoints_to_json(keypoints_dict, output_json_path)
    print(f"Keypoints saved to {output_json_path}")


if __name__ == "__main__":
    main()