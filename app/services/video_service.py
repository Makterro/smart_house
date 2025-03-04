import os
import uuid
from sqlalchemy.orm import Session
from app.models.video import Video
from app.core.config import settings
from pathlib import Path
from sqlalchemy import desc

class VideoService:
    @staticmethod
    def get_videos(db: Session):
        return db.query(Video).order_by(desc(Video.created_at)).all()
    
    @staticmethod
    def get_video(db: Session, video_id: int):
        return db.query(Video).filter(Video.id == video_id).first()
    
    @staticmethod
    def create_video(db: Session, filename: str, folder: str, camera_id: int = None):
        video = Video(
            filename=filename,
            folder=folder,
            camera_id=camera_id
        )
        db.add(video)
        db.commit()
        db.refresh(video)
        return video
    
    @staticmethod
    def update_video_actions(db: Session, video_id: int, actions: list):
        video = VideoService.get_video(db, video_id)
        if video:
            video.actions = actions
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