"""Anonymous user record stored in MongoDB."""

from datetime import datetime

from pydantic import BaseModel


class AnonymousUser(BaseModel):
    """Identity and activity timestamps for an anonymous user."""

    user_id: str
    last_active_at: datetime
    created_at: datetime
