import os
import uuid
from sqlalchemy.orm import Session
from app.models.video import Video
from app.core.config import settings

class VideoService:
    @staticmethod
    def get_videos(db: Session):
        return db.query(Video).all()
    
    @staticmethod
    def get_video(db: Session, video_id: int):
        return db.query(Video).filter(Video.id == video_id).first()
    
    @staticmethod
    def create_video(db: Session, filename: str, folder: str):
        processed_filename = f"processed_{filename}"
        video = Video(
            filename=filename,
            processed_filename=processed_filename,
            folder=folder,
            actions=None  # Будет обновлено после обработки
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