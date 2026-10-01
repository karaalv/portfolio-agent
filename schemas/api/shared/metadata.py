"""Metadata schema for API responses."""

from datetime import datetime

from pydantic import BaseModel


class ApiResponseMetaData(BaseModel):
    request_id: str
    success: bool
    message: str
    timestamp: datetime