# Delete agent memory

Delete all model memory belonging to the authenticated visitor.
This removes chat messages, function calls, tool outputs and
reasoning artefacts through `delete_agent_memory`.

<!-- General Info -->

---

* **URL:** `/api/agent-memory/delete-memory`
* **Method:** `DELETE`
* **Authentication:** JWT access cookie.
* **URL Parameters:** None.
* **Request Body:** None.
* **Request Headers:** Allowed `Origin`; optional `X-Request-ID`.

<!-- Successful Responses -->

---

* **Successful Response:** Agent memory deleted

  * **Code:** `200`
  * **Response Object:**

    ```json
    {
        "meta": {
            "request_id": "<UniqueRequestID>",
            "success": true,
            "message": "Agent memory deleted successfully.",
            "timestamp": "<ISO8601Timestamp>"
        },
        "data": null
    }
    ```

  * **Description:** Clears the visitor's stored memory. Also
    succeeds when no records exist. The anonymous user record
    and authentication cookie are retained.

<!-- Unsuccessful Responses -->

---

* **Unsuccessful Response:** Access or deletion failure

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
    `429`. Service failures return `500`; deletion failure uses
    `Unable to delete agent memory.` without internal details.

<!-- Notes -->

---

**Notes:**

* User identity comes exclusively from the verified JWT. A
  supplied `user_id` query parameter cannot change the target.
* Origin checks, IP and user blocks, and `APPLICATION` rate
  limits apply. Send the JWT cookie with the request.
* Deletion does not cancel an ongoing agent turn. Later writes
  from that turn or future interactions can create new memory.
