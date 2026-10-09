"""Expose visitor chat pages and deletion of agent memory."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from agent.chat.retrieval import retrieve_agent_chat_page
from agent.memory.deletion import delete_agent_memory
from api.dependencies.auth import ApplicationUserId
from api.utils.requests import get_request_id
from api.utils.responses import create_http_response

agent_memory_router = APIRouter()


@agent_memory_router.get('/fetch-chat-page')
async def fetch_chat_page(
	request: Request,
	user_id: ApplicationUserId,
	offset: Annotated[int, Query(ge=0)] = 0,
) -> JSONResponse:
	"""Return one visible chat page for the verified visitor."""
	try:
		messages = await retrieve_agent_chat_page(
			user_id=user_id,
			offset=offset,
		)
		data = [
			message.model_dump(mode='json')
			for message in messages
		]
	except Exception as exc:
		raise HTTPException(
			status_code=500,
			detail='Unable to retrieve chat history.',
		) from exc
	return create_http_response(
		request_id=get_request_id(request),
		success=True,
		message='Chat page retrieved successfully.',
		data=data,
	)


@agent_memory_router.delete('/delete-memory')
async def delete_memory(
	request: Request,
	user_id: ApplicationUserId,
) -> JSONResponse:
	"""Delete every stored model artefact for the visitor."""
	try:
		await delete_agent_memory(user_id=user_id)
	except Exception as exc:
		raise HTTPException(
			status_code=500,
			detail='Unable to delete agent memory.',
		) from exc
	return create_http_response(
		request_id=get_request_id(request),
		success=True,
		message='Agent memory deleted successfully.',
		data=None,
	)
