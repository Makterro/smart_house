import os
import uuid
from fastapi import APIRouter, Depends, File, UploadFile, Request, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.utils.video_processing import process_video
from app.core.config import settings
from fastapi.templating import Jinja2Templates
from app.services.video_service import VideoService
from app.services.minio_service import MinioService
import logging
from app.worker import process_video_task
from pathlib import Path

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="templates")
templates.env.globals["settings"] = settings

@router.get("/", response_class=HTMLResponse)
async def list_videos(
    request: Request,
    db: Session = Depends(get_db)
):
    videos = VideoService.get_videos(db)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request, 
            "videos": videos,
            "settings": settings
        }
    )

@router.get("/video/{video_id}", response_class=HTMLResponse)
async def get_video(
    video_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    video = VideoService.get_video(db, video_id)
    frames_folder = settings.MEDIA_DIR / video.folder / "frames"
    
    if not frames_folder.exists():
        raise HTTPException(status_code=404, detail="Кадры не найдены")
        
    frames = [f for f in os.listdir(frames_folder) if f.endswith(".jpg")]
    return templates.TemplateResponse(
        "video.html",
        {
            "request": request, 
            "video": video, 
            "frames": frames,
            "settings": settings
        }
    )

@router.post("/upload/")
async def upload_video(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        folder_name = VideoService.generate_folder_name(file.filename)
        folder_path = settings.MEDIA_DIR / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)
        
        file_path = folder_path / file.filename
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        video = VideoService.create_video(db, file.filename, folder_name)
        
        # Запускаем обработку через Celery
        process_video_task.delay(video.id)
        
        return {"message": "Video uploaded successfully", "video_id": video.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cameras", response_class=HTMLResponse)
async def list_cameras(
    request: Request,
    db: Session = Depends(get_db)
):
    # Получаем список камер с последними видео
    cameras = [
        {"id": 1, "name": "Камера 1"},
        {"id": 2, "name": "Камера 2"},
    ]
    
    # Для каждой камеры получаем последнее видео
    for camera in cameras:
        latest_video = VideoService.get_latest_camera_video(db, camera["id"])
        camera["latest_video"] = latest_video

    return templates.TemplateResponse(
        "cameras.html",
        {
            "request": request,
            "cameras": cameras,
            "settings": settings
        }
    )

@router.get("/camera/{camera_id}", response_class=HTMLResponse)
async def view_camera(
    camera_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    # Получаем все видео для данной камеры
    videos = VideoService.get_camera_videos(db, camera_id)
    if not videos:
        raise HTTPException(status_code=404, detail="Видео не найдены")
    
    # Получаем последнее видео
    latest_video = videos[0] if videos else None
    
    # Получаем frames для последнего видео
    frames = []
    if latest_video:
        frames_folder = settings.MEDIA_DIR / latest_video.folder / "frames"
        if frames_folder.exists():
            frames = [f for f in os.listdir(frames_folder) if f.endswith(".jpg")]
    
    return templates.TemplateResponse(
        "camera.html",
        {
            "request": request,
            "camera_id": camera_id,
            "videos": videos,
            "latest_video": latest_video,
            "frames": frames,
            "settings": settings
        }
    )

@router.get("/camera/{camera_id}/videos")
async def get_camera_videos(
    camera_id: int,
    db: Session = Depends(get_db)
):
    videos = VideoService.get_camera_videos(db, camera_id)
    if not videos:
        return {"videos": []}
        
    return {
        "videos": [
            {
                "id": video.id,
                "filename": video.filename,
                "folder": video.folder,
                "created_at": video.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
            for video in videos
        ]
    }

@router.get("/camera/{camera_id}/frames/{folder}")
async def get_video_frames(
    camera_id: int,
    folder: str,
    db: Session = Depends(get_db)
):
    try:
        frames_folder = settings.MEDIA_DIR / folder / "frames"
        if not frames_folder.exists():
            return {"frames": []}
            
        frames = [f for f in os.listdir(frames_folder) if f.endswith(".jpg")]
        return {"frames": frames}
    except Exception as e:
        logger.error(f"Ошибка при получении кадров из папки {folder}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при получении кадров") 