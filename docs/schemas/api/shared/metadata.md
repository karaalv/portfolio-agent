# Shared API metadata

`ApiResponseMetaData` is a Pydantic model included with API responses. It
identifies the request, records whether it succeeded, and provides a message
and timestamp.

```python
class ApiResponseMetaData(BaseModel):
    request_id: str
    success: bool
    message: str
    timestamp: datetime
```

Implemented in `schemas/api/shared/metadata.py`.
