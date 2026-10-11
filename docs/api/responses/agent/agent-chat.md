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

<!-- Unsuccessful Responses -->

---

* **Unsuccessful Response:** Connection rejection or closure

  * **Close Codes:**

    | Code | Meaning |
    | --- | --- |
    | `1008` | Invalid token, blocked access or bad request. |
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
* Agent output publishing is still pending in `agent.main`.
  The endpoint invokes the agent, but currently does not deliver
  its text stream, tool messages or turn lifecycle responses.
* Message safety checks remain a TODO before agent invocation.
