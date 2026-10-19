# WebSocket requests

Implemented in `schemas/api/ws/request.py`.

`WebSocketRequest` validates client messages. Both supported
request types use a string payload, so no payload union or
separate request variants are needed.

| Field | Type | Meaning |
| --- | --- | --- |
| `type` | `WebSocketRequestType` | Message discriminator. |
| `payload` | `str` | Agent input or heartbeat text. |
| `request_id` | `str \| None` | Optional correlation ID. |

## Supported types

- `agent_message`: text submitted to the portfolio agent.
- `heartbeat`: application heartbeat text, such as `pong`.

```json
{
  "type": "agent_message",
  "payload": "Tell me about Alvin's projects.",
  "request_id": "client-message-001"
}
```

The request helper checks raw UTF-8 content size before validating
JSON with `WebSocketRequest.model_validate_json(...)`.
It generates an ID when
`request_id` is missing, null or empty. Agent messages update
the manager's current ID; heartbeat requests do not update it.
Parsing does not
perform authentication, rate limiting or agent execution.
