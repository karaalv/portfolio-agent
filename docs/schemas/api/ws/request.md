# WebSocket requests

Implemented in `schemas/api/ws/request.py`.

`WebSocketRequest` validates client messages. Both supported
request types use a string payload, so no payload union or
separate request variants are needed.

| Field | Type | Meaning |
| --- | --- | --- |
| `type` | `WebSocketRequestType` | Message discriminator. |
| `payload` | `str` | Agent input or heartbeat text. |

## Supported types

- `agent_message`: text submitted to the portfolio agent.
- `heartbeat`: application heartbeat text, such as `pong`.

```json
{
  "type": "agent_message",
  "payload": "Tell me about Alvin's projects."
}
```

The controller will validate incoming JSON with
`WebSocketRequest.model_validate_json(...)`. Parsing does not
perform authentication, rate limiting or agent execution.
