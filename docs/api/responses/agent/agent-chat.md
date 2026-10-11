# Agent chat WebSocket

Connect an anonymous visitor to the portfolio agent. The socket
handles sequential text requests and uses the process-local
registry for outbound messages and connection cleanup.

<!-- General Info -->

---

* **URL:** `/api/agent/ws/agent-chat`
* **Method:** WebSocket upgrade.
* **Authentication:** Optional JWT query token.
* **URL Parameters:**

  * `access_token` (string, optional): Signed visitor token.
    Supplied tokens must pass validation, user block checks
    and application rate limits. An invalid supplied token
    does not create an anonymous identity.
  * `request_id` (string, optional): Handshake correlation ID.
    Missing or empty values receive a generated UUID string.

* **Client Messages:**

  ```json
  {
      "type": "agent_message",
      "payload": "Tell me about Alvin's projects.",
      "request_id": "message-001"
  }
  ```

  `type` is `agent_message` or `heartbeat`. Both require a
  string `payload`. `request_id` is an optional string or null;
  missing, null or empty values receive generated UUID strings.

<!-- Successful Responses -->

---

* **Successful Response:** New visitor token

  * **Response Object:**

    ```json
    {
        "meta": {
            "request_id": "<HandshakeRequestID>",
            "success": true,
            "message": "Set user token",
            "timestamp": "<UTCISO8601Timestamp>"
        },
        "type": "set_user_token",
        "payload": "<SignedAccessToken>"
    }
    ```

  * **Description:** Without an access token, create a user
    and user usage record. Accept and register the socket,
    then queue this response immediately after registration.
    Issue it only once. The client submits the token to
    `/api/users/claim-cookie` to claim its authentication cookie.
    Existing token holders do not receive a replacement token.

* **Successful Response:** Heartbeat

  * **Response Object:**

    ```json
    {
        "meta": {
            "request_id": "<CurrentRequestID>",
            "success": true,
            "message": "Heartbeat",
            "timestamp": "<UTCISO8601Timestamp>"
        },
        "type": "heartbeat",
        "payload": "ping"
    }
    ```

  * **Description:** The manager sends periodic heartbeats.
    Client heartbeat messages are ignored by the chat loop and
    do not consume agent-message capacity or change the
    manager's current request ID.

## Agent stream messages

Text deltas use the following envelope. Append `payload.payload`
to the displayed response in `sequence_number` order.

```json
{
    "meta": {
        "request_id": "message-001",
        "success": true,
        "message": "Agent delta",
        "timestamp": "<UTCISO8601Timestamp>"
    },
    "type": "agent_delta",
    "payload": {
        "stream_id": "<StreamID>",
        "timestamp": "<UTCISO8601Timestamp>",
        "type": "text",
        "user_id": "<UserID>",
        "memory_id": "<MemoryID>",
        "sequence_number": 0,
        "payload": "Hello"
    }
}
```

| Event | Payload |
| --- | --- |
| `agent_start` | `Agent turn started.` |
| `tool_message` | Array of requested tool names. |
| `agent_delta` | Incremental `StreamManagerItem`. |
| `agent_end` | `Agent turn ended.` |

Failed responses emit an `error` saying the response could not
be generated. Stream errors or missing completion emit an
`error` saying the response was interrupted. Incomplete model
responses emit a `warning` saying the response is incomplete.
Each notification asks the visitor to try again. Raw provider
error details are logged internally and not sent to the client.

The event mapping follows the
[Responses streaming reference](https://developers.openai.com/api/reference/resources/responses/streaming-events).

<!-- Unsuccessful Responses -->

---

* **Unsuccessful Response:** Connection rejection or closure

  * **Close Codes:**

    | Code | Meaning |
    | --- | --- |
    | `1008` | Invalid token, blocked access or bad request. |
    | `1009` | Input byte or token limit exceeded. |
    | `1013` | Rate-limit timeout or exhausted queue capacity. |
    | `1011` | Internal access or processing failure. |
    | `1001` | Server shutdown or inactive connection cleanup. |

  * **Description:** Access failures before acceptance reject
    the handshake; browser clients may observe an HTTP denial
    rather than a WebSocket close frame. Accepted connections
    use close frames. Cleanup removes registry tracking.

<!-- Notes -->

---

* Each agent request acquires IP and user `AGENT_MESSAGE`
  allowances before invoking `agent_chat`.
* The manager retains the current agent request ID. It stamps
  copied response metadata at enqueue time, so an already
  queued response keeps its ID when the next request arrives.
  Response helpers do not require request ID arguments.
* Heartbeats and token delivery use the same outbound queue.
  A heartbeat may arrive before the token response.
* An accepted agent turn emits `agent_start`, incremental
  `agent_delta` events and one `agent_end`. Tool rounds also
  emit `tool_message` before executing the requested tools.
  Start and end events surround the entire recursive turn.
* `agent_delta` carries a `StreamManagerItem` containing
  `stream_id`, `timestamp`, `type`, `user_id`, `memory_id`,
  `sequence_number` and incremental text in `payload`.
  `tool_message` carries an array of unique tool names in JSON.
* Failed model responses and stream errors emit `error` with a
  retry message. Incomplete responses emit `warning`. These
  stop the current turn and are followed by `agent_end`.
  The connection can receive another request afterwards.
* `agent_end` signifies lifecycle completion, not successful
  generation. Partial deltas are not persisted as completed
  output if the model round fails or is incomplete.
* The complete UTF-8 JSON envelope must not exceed 16 KiB.
  This guard runs before parsing and applies to heartbeats too.
* Agent payloads must not exceed 10,000 `o200k_base` tokens.
  Count original input before cleaning or truncation. Exceeding
  either hard limit persists a 24-hour user block and closes all
  that user's local connections with `1009`. Other visitors
  sharing the IP are not blocked. Sockets are closed even when
  block persistence fails, but that failure cannot guarantee a
  lasting block.
* Accepted text is Unicode-normalised, cleaned of control
  characters and obvious repetition, and capped at 2,000
  characters. Uninterrupted strings longer than 100 characters
  are removed. Personal data and URLs are not redacted.
* Empty cleaned input receives a `warning` and does not invoke
  the agent or create a block. The connection remains usable.
* Uvicorn has a separate 64 KiB transport limit configured in
  `run.py`. Messages above that limit are rejected before the
  application guard receives them, so that guard cannot persist
  a user block for those messages.
