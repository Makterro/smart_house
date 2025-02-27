import os
import uuid
from fastapi import APIRouter, Depends, File, UploadFile, Request, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.utils.video_processing import process_video
from app.core.config import settings
from fastapi.templating import Jinja2Templates
from app.services.video_service import VideoService
import logging
from app.worker import process_video_task

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