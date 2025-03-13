from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.api.v1.endpoints import video_api, webhook
import logging
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/media", StaticFiles(directory="media"), name="media")

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
        port=8080,
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