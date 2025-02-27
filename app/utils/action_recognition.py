import torch
import numpy as np
import logging
from pathlib import Path
from mmaction.apis import inference_model, init_model

logger = logging.getLogger(__name__)

class ActionRecognizer:
    def __init__(self, yolo_model):
        self.yolo_model = yolo_model
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        try:
            # Загружаем предобученную модель для скелетной классификации
            self.model = init_model(
                'configs/skeleton/stgcn/stgcn_80e_ntu60_xsub_keypoint.py',
                'https://download.openmmlab.com/mmaction/skeleton/stgcn/stgcn_80e_ntu60_xsub_keypoint/stgcn_80e_ntu60_xsub_keypoint-e7bb9653.pth',
                device=self.device
            )
            self.threshold = 0.5
            logger.info(f"Модель ST-GCN загружена на устройство: {self.device}")
        except Exception as e:
            logger.error(f"Ошибка при загрузке модели: {e}")
            raise

    def preprocess_keypoints(self, keypoints):
        """Преобразует keypoints из YOLO в формат для ST-GCN"""
        # YOLO возвращает 17 точек, ST-GCN ожидает определенный формат
        processed = np.zeros((1, len(keypoints), 3))  # [N, T, V, C]
        for i, kp in enumerate(keypoints):
            processed[0, i] = [kp[0], kp[1], kp[2]]  # x, y, confidence
        return processed

    def recognize_action(self, video_path: str):
        """Распознает действия в видео по скелетным данным"""
        try:
            # Получаем позы из видео с помощью YOLOv8
            results = self.yolo_model(video_path)
            
            actions = []
            for frame in results:
                if frame.keypoints is not None:
                    # Берем keypoints первого человека
                    keypoints = frame.keypoints.data[0].cpu().numpy()
                    
                    # Преобразуем формат
                    skeleton_data = self.preprocess_keypoints(keypoints)
                    
                    # Получаем предсказание
                    result = inference_model(self.model, skeleton_data)
                    
                    # Добавляем действие если уверенность выше порога
                    if result['pred_score'] > self.threshold:
                        actions.append({
                            "action": result['pred_label'],
                            "confidence": float(result['pred_score']),
                            "timestamp": None
                        })
            
            return actions

        except Exception as e:
            logger.error(f"Ошибка при распознавании действий: {e}")
            return [] 