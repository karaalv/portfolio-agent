# HTTP response schemas

`ApiHttpResponse` is the standard HTTP response envelope. Each endpoint
defines the type of `data`; it may be `None` when there is no response data.

```python
class ApiHttpResponse(BaseModel):
	meta: ApiResponseMetaData
	data: Any | None
```

Implemented in `schemas/api/http/responses.py`. The `meta` field uses the
[shared API metadata](../shared/metadata.md) model.
