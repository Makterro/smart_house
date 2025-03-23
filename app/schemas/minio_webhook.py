from pydantic import BaseModel
from typing import List, Dict, Optional

class S3Object(BaseModel):
    key: str
    size: int | None = None
    eTag: str | None = None
    contentType: str | None = None
    userMetadata: Dict[str, str] | None = None

class S3Bucket(BaseModel):
    name: str
    arn: str

class S3Info(BaseModel):
    bucket: S3Bucket
    object: S3Object

class MinioRecord(BaseModel):
    eventName: str
    s3: S3Info

class MinioWebhook(BaseModel):
    EventName: str
    Key: str
    Records: List[MinioRecord] 