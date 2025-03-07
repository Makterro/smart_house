from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.core.config import settings
from app.api.v1.endpoints import video_api, webhook
from app.db.base import Base, engine
import logging
import shutil
import os
from pathlib import Path

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_app():
    """Очистка медиа директории и пересоздание базы данных"""
    logger.info("🔄 Сброс приложения...")
    
    # Очистка медиа директории
    if settings.MEDIA_DIR.exists():
        logger.info("🗑️ Очистка медиа директории...")
        for item in settings.MEDIA_DIR.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
    
    # Создание медиа директории
    logger.info("📁 Создание медиа директории...")
    settings.MEDIA_DIR.mkdir(exist_ok=True)
    
    # Пересоздание базы данных
    logger.info("🔨 Пересоздание базы данных...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    logger.info("✅ Сброс приложения завершен")

# Сброс приложения при запуске только в режиме отладки
if settings.DEBUG:
    reset_app()

app = FastAPI(title=settings.PROJECT_NAME)

# Монтирование статических файлов
app.mount("/media", StaticFiles(directory="media"), name="media")

# Создание объекта шаблонов с контекстом по умолчанию
templates = Jinja2Templates(directory="templates")
templates.env.globals["settings"] = settings

# Подключение роутеров
app.include_router(video_api.router, prefix=settings.API_V1_STR)
app.include_router(webhook.router, prefix=settings.API_V1_STR)

@app.on_event("shutdown")
async def shutdown_event():
    """Запускается при остановке приложения"""
    logger.info("Завершение работы приложения")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=settings.DEBUG
    )


# для подсоединения к сервису http://host.docker.internal:8000/api/v1/webhook/minio
# uvicorn main:app --host 0.0.0.0 --port 8000 --reload
# Запуск воркера для скачивания
# celery -A app.worker -b redis://localhost:6379/0 worker --loglevel=info --queues=download_queue --pool=solo

# # Запуск воркера для обработки видео
# celery -A app.worker -b redis://localhost:6379/0 worker --loglevel=info --queues=video_processing_queue --pool=solo

# # Запуск воркера для стриминга
# celery -A app.utils.video_stream -b redis://localhost:6379/0 worker --loglevel=info --queues=video_stream_queue --pool=solo