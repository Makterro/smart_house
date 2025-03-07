import os
import uuid
from sqlalchemy.orm import Session
from app.models.video import Video, VideoStatus
from app.core.config import settings
from sqlalchemy import desc

class VideoService:
    @staticmethod
    def get_videos(db: Session):
        return db.query(Video).order_by(desc(Video.created_at)).all()
    
    @staticmethod
    def get_video(db: Session, video_id: int):
        return db.query(Video).filter(Video.id == video_id).first()
    
    @staticmethod
    def create_video(db: Session, filename: str, folder: str, camera_id: int):
        """Создание записи видео в базе данных и формирование ссылки на видео в MinIO"""
        try:
            # Создание записи видео в базе данных
            video = Video(
                filename=filename,
                folder=folder,
                camera_id=camera_id,
                status="pending"  # Начальный статус
            )
            db.add(video)
            db.commit()
            db.refresh(video)

            # Формируем ссылку на видео в MinIO
            video_link = f"http://minio.example.com/{folder}/{filename}"
            video.link = video_link

            # Сохраняем ссылку в базе данных
            db.commit()
            db.refresh(video)
            
            return video
        except Exception as e:
            raise Exception(f"Ошибка при создании видео: {e}")
    
    @staticmethod
    def update_video_actions(db: Session, video_id: int, actions: list):
        video = VideoService.get_video(db, video_id)
        if video:
            video.actions = actions
            video.detect = True  # Устанавливаем флаг detect в True, так как действия были обнаружены
            db.commit()
            db.refresh(video)
        return video

    @staticmethod
    def update_video_status(db: Session, video_id: int, status: str):
        """Обновляет статус видео"""
        video = VideoService.get_video(db, video_id)
        if video:
            video.status = status
            db.commit()
            db.refresh(video)
        return video

    @staticmethod
    def update_video_skeletons(db: Session, video_id: int, skeletons: list):
        """Сохраняет найденные скелеты в видео"""
        video = VideoService.get_video(db, video_id)
        if video:
            video.skeletons = skeletons
            db.commit()
            db.refresh(video)
        return video
    
    @staticmethod
    def generate_folder_name(filename: str) -> str:
        """Создает уникальную папку на основе имени файла"""
        name = os.path.splitext(filename)[0]
        unique_hash = uuid.uuid4().hex[:8]
        return f"{name}_{unique_hash}"

    @staticmethod
    def get_camera_videos(db: Session, camera_id: int):
        """Получить все видео для конкретной камеры"""
        return db.query(Video)\
            .filter(Video.camera_id == camera_id)\
            .order_by(desc(Video.created_at))\
            .all()

    @staticmethod
    def get_latest_camera_video(db: Session, camera_id: int):
        """Получить последнее видео для камеры"""
        return db.query(Video)\
            .filter(Video.camera_id == camera_id)\
            .order_by(desc(Video.created_at))\
            .first()

    @staticmethod
    def save_video_actions(db: Session, video_id: int, actions: list):
        """Сохраняет действия в JSON поле видео"""
        video = VideoService.get_video(db, video_id)
        if video:
            video.actions = actions
            db.commit()
            db.refresh(video)
        return video
    