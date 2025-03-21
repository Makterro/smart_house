from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # Основные настройки
    PROJECT_NAME: str
    API_V1_STR: str
    DEBUG: bool = True
    HOST_IP: str = "127.0.0.1"
    HOST_PORT: int = 8080
    ALLOW_ORIGINS: str
    
    # MinIO настройки
    MINIO_ENDPOINT: str = "89.105.137.28:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_ROOT_USER: str = 'minioadmin'
    MINIO_ROOT_PASSWORD: str = 'minioadmin'
    MINIO_BUCKET_NAME: str

    # DB
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    REDIS_URL: str = 'redis://redis:6379'

    # Webhook
    MANAGMENT_SERVICE_ENDPOINT_WEBHOOK: str
    
    # Пути
    MEDIA_DIR: str = "media"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.MEDIA_DIR = Path(self.MEDIA_DIR)
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings() 