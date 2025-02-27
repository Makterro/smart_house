from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.minio_webhook import MinioWebhook
from app.services.video_service import VideoService
from app.worker import download_video_task
import logging
import os

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/webhook/minio")
async def minio_webhook(
    event: MinioWebhook,
    db: Session = Depends(get_db)
):
    try:
        if event.EventName != "s3:ObjectCreated:Put":
            return {"message": "Ignored non-creation event"}

        for record in event.Records:
            bucket_name = record.s3.bucket.name
            object_key = record.s3.object.key
            
            folder_name = VideoService.generate_folder_name(object_key)
            video = VideoService.create_video(
                db=db,
                filename=os.path.basename(object_key),
                folder=folder_name
            )
            
            download_video_task.delay(bucket_name, object_key, video.id)
            
            logger.info(f"Started processing video: {video.id}")
            
        return {"message": "Processing started"}
    
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return {"error": str(e)} 