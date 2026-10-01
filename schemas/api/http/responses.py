"""HTTP response schemas for the Portfolio Agent API."""

from typing import Any

from pydantic import BaseModel

from schemas.api.shared.metadata import ApiResponseMetaData


class ApiHttpResponse(BaseModel):
    meta: ApiResponseMetaData
    data: Any | None