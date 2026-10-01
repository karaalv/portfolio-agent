"""
Utility functions for API responses,
such as creating standardized response objects.
"""
from datetime import datetime, timezone
from typing import Any

from fastapi.responses import JSONResponse

from schemas.api.http.responses import ApiHttpResponse
from schemas.api.shared.metadata import ApiResponseMetaData

# --- HTTP Responses ---

def create_http_response(
    request_id: str,
    success: bool,
    message: str,
    data: Any | None = None,
    status_code: int = 200
) -> JSONResponse:
    meta = ApiResponseMetaData(
        request_id=request_id,
        success=success,
        message=message,
        timestamp=datetime.now(timezone.utc)
    )
    response = ApiHttpResponse(
        meta=meta,
        data=data
    )
    return JSONResponse(
        content=response.model_dump(mode="json"),
        status_code=status_code
    )