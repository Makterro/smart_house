from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # Основные настройки
    PROJECT_NAME: str
    API_V1_STR: str
    DEBUG: bool
    
    # MinIO настройки
    MINIO_ENDPOINT: str = "http://minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"  # значение по умолчанию
    MINIO_SECRET_KEY: str = "minioadmin"  # значение по умолчанию
    
    # Пути
    MEDIA_DIR: str = "media"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.MEDIA_DIR = Path(self.MEDIA_DIR)
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings() 