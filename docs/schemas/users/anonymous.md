# Anonymous user schema

`AnonymousUser` is the Pydantic model for anonymous users in the
Portfolio Agent API. It stores the user's identifier and creation and last
activity timestamps.

```python
class AnonymousUser(BaseModel):
    user_id: str
    last_active_at: datetime
    created_at: datetime
```

Implemented in `schemas/users/anonymous.py`. The datetime fields are stored
as UTC dates in MongoDB. See the [MongoDB data model](../../architecture/mongodb-data-model.md)
for its database and collection.
