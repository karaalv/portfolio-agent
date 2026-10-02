"""Anonymous user record stored in MongoDB."""

from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator
from shared.time.get import get_utc_datetime_now


class AnonymousUser(BaseModel):
    """
    Identity and activity timestamps 
    for an anonymous user.
    """

    user_id: str
    last_active_at: datetime = Field(
        default_factory=get_utc_datetime_now
    )
    created_at: datetime = Field(
        default_factory=get_utc_datetime_now
    )


    @field_validator('last_active_at', 'created_at')
    @classmethod
    def normalise_datetimes(cls, value: datetime) -> datetime:
        """Normalise naive UTC dates to timezone-aware UTC datetimes."""
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

