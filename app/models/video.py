from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean
from sqlalchemy.sql import func
from app.db.base import Base
import enum

class VideoStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    processed_filename = Column(String, nullable=True)
    folder = Column(String, nullable=False)
    camera_id = Column(Integer, nullable=True)  # ID камеры
    actions = Column(JSON, nullable=True)  # Хранение обнаруженных действий
    skeletons = Column(JSON, nullable=True)  # Данные скелетов от YOLO
    status = Column(Enum(VideoStatus), default=VideoStatus.PENDING, nullable=False)  # Статус обработки
    detect = Column(Boolean, default=False, nullable=False)  # Флаг, указывающий, были ли обнаружены действия
    start_time = Column(DateTime(timezone=True), nullable=True)  # Время начала записи
    end_time = Column(DateTime(timezone=True), nullable=True)  # Время окончания записи
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    link = Column(String, nullable=True)  # Добавленное поле для хранения ссылки на видео в MinIO