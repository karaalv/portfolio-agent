# WebSocket responses

Implemented in `schemas/api/ws/response.py`.

Every response contains `meta`, `type` and `payload`.
`meta` uses `ApiResponseMetaData`, including the request ID,
success flag, message and UTC timestamp.

Response helpers generate fallback request IDs. Before queueing
output, the connection manager replaces the ID with its current
request ID in a copied envelope. Callers do not pass request IDs
to response helpers. Queued IDs remain stable after subsequent
requests update manager state.

## Discriminated variants

`WebSocketResponse` is a type alias for a Pydantic discriminated
union. Each concrete model fixes its `type` with `Literal` and
validates the corresponding payload. A union on `payload` alone
would allow mismatched message types and payloads.

| `type` | Payload |
| --- | --- |
| `heartbeat` | `str` |
| `agent_start` | `str` |
| `agent_end` | `str` |
| `agent_response` | `StreamManagerItem` |
| `tool_message` | `set[str]` |
| `set_user_token` | `str` |
| `warning` | `str` |
| `error` | `str` |

Concrete models are named `WebSocketHeartbeatResponse`,
`WebSocketAgentStartResponse`, `WebSocketAgentEndResponse`,
`WebSocketAgentResponse`, `WebSocketToolResponse`,
`WebSocketSetUserTokenResponse`, `WebSocketWarningResponse`
and `WebSocketErrorResponse`.

## Construction and validation

Construct a concrete model or use the corresponding response
helper in `api/websocket/helpers/responses.py`. The union alias
is not an envelope constructor.

For validation of an arbitrary server message:

```python
from pydantic import TypeAdapter

from schemas.api.ws.response import WebSocketResponse

adapter = TypeAdapter(WebSocketResponse)
response = adapter.validate_json(raw_json)
```

Serialise with `response.model_dump(mode='json')`. Tool payload
sets become JSON arrays. They contain unique values and have no
guaranteed ordering. Agent payloads retain the existing stream
item fields, including stream and memory identifiers.

## Metadata semantics

Helpers require `request_id` and a correctly typed `payload`.
An optional `message` overrides the metadata description.
Error helpers set `meta.success` to false. Other helpers,
including advisory warnings, set it to true.

Heartbeat helpers use `ping` when called by the manager. Each
heartbeat gets a fresh request ID. User tokens must only be
sent to their intended connection and must not be logged.
