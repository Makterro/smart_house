from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.api.v1.endpoints import video_api, webhook
import logging
from fastapi.middleware.cors import CORSMiddleware
from app.db.base import Base, engine
from app.models.video import Video
from sqlalchemy import Table

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    logger.info("Запуск приложения.")

    # Base.metadata.drop_all(bind=engine)
    # Base.metadata.create_all(bind=engine)

    # Video.__table__.drop(engine, checkfirst=True)
    Video.__table__.create(engine, checkfirst=True)
    
    yield
    # shutdown
    logger.info("Завершение работы приложения")

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(settings.ALLOW_ORIGINS)],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/media", StaticFiles(directory="media"), name="media")

app.include_router(video_api.router, prefix=settings.API_V1_STR)
app.include_router(webhook.router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=str(settings.HOST_IP),
        port=int(settings.HOST_PORT),
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