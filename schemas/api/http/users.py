"""Validate request bodies for anonymous visitor endpoints."""

from pydantic import BaseModel, Field


class ClaimCookieRequest(BaseModel):
	"""Carry the access token received over WebSocket."""

	claim_token: str = Field(
		min_length=1,
		description='Signed access token for the JWT cookie.',
	)
