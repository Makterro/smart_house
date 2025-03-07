from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.config import settings
from app.services.video_service import VideoService
import logging
from fastapi.responses import JSONResponse
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/camera/{camera_id}", response_class=JSONResponse)
async def get_camera_videos(
    camera_id: int,
    db: Session = Depends(get_db)
):
    # Получаем все видео для данной камеры
    videos = VideoService.get_camera_videos(db, camera_id)
    
    # Если видео не найдены, возвращаем ошибку
    if not videos:
        raise HTTPException(status_code=404, detail="Видео не найдены")
    
    # Формируем ответ в нужном формате
    video_data = [
        {
            "id": video.id,
            "link": video.link,  # Ссылка на видео из базы данных
            "start": video.start_time.isoformat() if video.start_time else None,
            "finish": video.end_time.isoformat() if video.end_time else None
        }
        for video in videos
    ]
    
    # Возвращаем ответ в формате JSON
    return JSONResponse(content={"videos": video_data})

@router.get("/camera/{camera_id}/videos", response_class=JSONResponse)
async def get_camera_videos(
    camera_id: int,
    start: str = None,  # Опциональные параметры для фильтрации по времени
    finish: str = None,
    db: Session = Depends(get_db)
):
    # Преобразуем строки start и finish в объекты datetime, если они есть
    start_datetime = datetime.fromisoformat(start) if start else None
    finish_datetime = datetime.fromisoformat(finish) if finish else None
    
    # Получаем все видео для данной камеры
    videos = VideoService.get_camera_videos(db, camera_id)

    # Если видео не найдены, возвращаем ошибку
    if not videos:
        raise HTTPException(status_code=404, detail="Видео не найдены")

    # Фильтруем видео по времени, если параметры start и finish заданы
    if start_datetime and finish_datetime:
        videos = [video for video in videos if video.start_time and video.end_time and start_datetime <= video.start_time <= finish_datetime]

    # Формируем ответ в нужном формате
    video_data = [
        {
            "id": video.id,
            "link": video.link,  # Ссылка на видео из базы данных
            "start": video.start_time.isoformat() if video.start_time else None,
            "finish": video.end_time.isoformat() if video.end_time else None,
            "detect": video.detect  # Указываем, были ли обнаружены действия
        }
        for video in videos
    ]
    
    # Возвращаем ответ в формате JSON
    return JSONResponse(content={"videos": video_data})