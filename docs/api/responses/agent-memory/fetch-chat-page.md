# Fetch chat page

Retrieve one page of the authenticated visitor's visible chat
messages. Internal tool calls, tool outputs and reasoning items
are excluded by `retrieve_agent_chat_page`.

<!-- General Info -->

---

* **URL:** `/api/agent-memory/fetch-chat-page?offset=0`
* **Method:** `GET`
* **Authentication:** JWT access cookie.
* **URL Parameters:**

  * `offset` (integer, optional): Number of visible messages to
    skip from newest to oldest. Defaults to `0`; minimum `0`.

* **Request Body:** None.
* **Request Headers:** Allowed `Origin`; optional `X-Request-ID`.

<!-- Successful Responses -->

---

* **Successful Response:** Chat page retrieved

  * **Code:** `200`
  * **Response Object:**

    ```json
    {
        "meta": {
            "request_id": "<UniqueRequestID>",
            "success": true,
            "message": "Chat page retrieved successfully.",
            "timestamp": "<ISO8601Timestamp>"
        },
        "data": [
            {
                "memory_id": "<MemoryID>",
                "user_id": "<VerifiedUserID>",
                "memory_source": "user",
                "created_at": "<ISO8601Timestamp>",
                "content": "Hello"
            }
        ]
    }
    ```

  * **Description:** Returns up to `AGENT_MEMORY_PAGE_SIZE`
    messages, currently `30`. Each item is an `AgentChatMemory`;
    `memory_source` is `user` or `agent`. Datetimes are sent as
    UTC ISO 8601 strings. An empty page returns `data: []`.

<!-- Unsuccessful Responses -->

---

* **Unsuccessful Response:** Access or retrieval failure

  * **Code:** `400`, `401`, `403`, `429` or `500`.
  * **Response Object:**

    ```json
    {
        "meta": {
            "request_id": "<UniqueRequestID>",
            "success": false,
            "message": "<ErrorMessage>",
            "timestamp": "<ISO8601Timestamp>"
        },
        "data": null
    }
    ```

  * **Description:** Missing client IP returns `400`. Missing,
    invalid or expired JWT returns `401`. Invalid Origin or
    blocked IP/user returns `403`. Exhausted allowance returns
    `429`. Service failures return `500`; retrieval failure uses
    `Unable to retrieve chat history.` without internal details.

* **Unsuccessful Response:** Invalid offset

  * **Code:** `422`
  * **Response Object:** FastAPI validation response:

    ```json
    {
        "detail": [
            {
                "type": "greater_than_equal",
                "loc": ["query", "offset"],
                "msg": "<ValidationError>",
                "input": "-1",
                "ctx": {"ge": 0}
            }
        ]
    }
    ```

  * **Description:** Rejects negative or non-integer offsets.
    Validation details depend on the submitted value.

<!-- Notes -->

---

**Notes:**

* The server obtains the user ID from the verified JWT. Clients
  cannot select another user's history through parameters.
* Offset `0` selects the newest page. Every returned page is
  ordered oldest to newest. Prepend older pages to the chat.
* Increase the offset by the number of returned messages.
  An empty page means there are no more visible messages.
* This is offset pagination, without a stable snapshot. New
  messages or deletion between requests can shift page windows.
* Origin checks, IP and user blocks, and `APPLICATION` rate
  limits apply. Send the JWT cookie with the request.
