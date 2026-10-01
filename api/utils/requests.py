"""
Utility functions for API requests,
such as creating standardized request objects.
"""
from fastapi import Request


def get_request_id(request: Request) -> str:
    """
    Extract request ID from the request header
    or request state if not found in headers.
    """
    header_request_id = request.headers.get('X-Request-ID')
    if header_request_id:
        return header_request_id
    return getattr(request.state, 'request_id', '')