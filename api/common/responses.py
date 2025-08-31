"""
This module contains response constructors
for the API.
"""

from typing import Any, Optional

from fastapi.responses import JSONResponse

from api.common.schemas import APIResponse, MetaData

# --- HTTP Response Constructors ---


def success_response(
	message: str,
	data: Optional[Any] = None,
	status_code: int = 200,
) -> JSONResponse:
	"""
	Constructs a successful API response.

	Args:
		message (str): A message describing the success.
		data (Optional[Any]): The data to include in the response.
		status_code (int): The HTTP status code for the response.

	Returns:
		JSONResponse: The constructed JSON response.
	"""
	response = APIResponse(
		metadata=MetaData(success=True, message=message),
		data=data,
	)

	return JSONResponse(
		status_code=status_code,
		content=response.model_dump(),
	)


def error_response(
	message: str,
	status_code: int = 500,
	errors: Optional[Any] = None,
) -> JSONResponse:
	"""
	Constructs an error API response.

	Args:
		message (str): A message describing the error.
		status_code (int): The HTTP status code for the response.
		errors (Optional[Any]): Additional error details.

	Returns:
		JSONResponse: The constructed JSON response.
	"""
	response = APIResponse(
		metadata=MetaData(success=False, message=message),
		data=errors,
	)

	return JSONResponse(
		status_code=status_code,
		content=response.model_dump(),
	)
