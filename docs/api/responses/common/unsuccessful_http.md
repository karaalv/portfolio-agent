# Unsuccessful HTTP Response

Whenever an HTTP request to the Portfolio Agent API fails due to client errors (4xx) or server errors (5xx), the API will return an unsuccessful response with the appropriate status code and a response object containing error details.

---

* **URL:** `/api/*`

* **Method:** `*`

---

* **Unsuccessful Response:** Error details sent

  * **Code:** `4xx` for client errors (e.g., bad request, unauthorized, forbidden, not found) or `5xx` for server errors (e.g., internal server error, service unavailable).

  * **Response Object:**

        ```json
        {
            "meta":{
                "request_id": "<UniqueRequestID>",
                "success": false,
                "message": "<ErrorMessage>",
                "timestamp": "<ISO8601Timestamp>"
            },
            "data": null,
        }
        ```

  * **Description:** The message field in the meta object will contain a human-readable error message describing the reason for the failure. The success field will be set to false to indicate that the request was unsuccessful. The request_id can be used for debugging and support purposes to trace the specific request that resulted in the error.

---

***Notes:*** This response format is used for all unsuccessful HTTP responses across the Portfolio Agent API to provide consistent error handling and messaging to clients. Clients should check the status code and the message field in the response to understand the reason for the failure and take appropriate action (e.g., retrying the request, correcting the request parameters, or contacting support).
