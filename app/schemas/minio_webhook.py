from pydantic import BaseModel
from typing import List, Dict, Optional

class S3Object(BaseModel):
    key: str
    size: int
    eTag: str
    contentType: str
    userMetadata: Dict[str, str]

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