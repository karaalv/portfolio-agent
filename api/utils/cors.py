"""
Utility functions for CORS configuration,
such as parsing allowed origins from environment variables.
"""

from os import getenv


def get_allowed_origins() -> list[str]:
    raw_origins = getenv('CORS_ORIGINS', '').split(',')
    return [
        origin.strip() for origin in raw_origins 
        if origin.strip()
    ]