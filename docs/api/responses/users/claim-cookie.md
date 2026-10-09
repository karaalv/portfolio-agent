# Claim access cookie

Claim the access token received in a WebSocket cookie message.
The endpoint verifies the token, confirms the anonymous user
exists and rejects blocked IP addresses or users before setting
the cookie. It does not create users or issue a new token.

<!-- General Info -->

---

* **URL:** `/api/users/claim-cookie`
* **Method:** `POST`
* **Authentication:** Signed JWT in `claim_token`; no existing
  authentication cookie is required.
* **URL Parameters:** None.
* **Request Headers:**

  * `Content-Type: application/json`.
  * `Origin`: must exactly match an entry in `CORS_ORIGINS`.
  * `X-Request-ID`: optional request tracing identifier.

* **Request Body:**

  ```json
  {
      "claim_token": "<SignedAccessToken>"
  }
  ```

  `claim_token` is a required, non-empty string. The user ID
  comes from its verified `sub` claim.

<!-- Successful Responses -->

---

* **Successful Response:** Access cookie claimed

  * **Code:** `200`
  * **Response Object:**

    ```json
    {
        "meta": {
            "request_id": "<UniqueRequestID>",
            "success": true,
            "message": "Access cookie claimed successfully.",
            "timestamp": "<ISO8601Timestamp>"
        },
        "data": null
    }
    ```

  * **Description:** Sets the `JWT` cookie to the supplied
    token. Cookie attributes are `HttpOnly`, `Secure`,
    `SameSite=Lax` and `Path=/`. `Domain` comes from the required
    `COOKIE_DOMAIN` environment variable.
  * **Expiry:** `Expires` matches the signed token's `exp`.
    `Max-Age` uses its remaining lifetime, rounded down to
    whole seconds. Claiming does not restart the six-day TTL.

<!-- Unsuccessful Responses -->

---

* **Unsuccessful Response:** Access rejected or service failure

  * **Code:** `400`, `401`, `403`, `404`, `429` or `500`.
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

  * **Description:** No cookie is set. Status and message:

    | Code | Message |
    | --- | --- |
    | `400` | `Client IP address is missing.` |
    | `401` | `Access token is invalid or expired.` |
    | `403` | `Origin is not allowed.` |
    | `403` | `Access is blocked.` |
    | `404` | `User does not exist.` |
    | `429` | `Rate limit exceeded. Try again later.` |

    `500` reports unavailable token validation, user retrieval,
    block checks or rate-limit services. Internal exception
    details and blocking reasons are not included.

* **Unsuccessful Response:** Invalid request body

  * **Code:** `422`
  * **Response Object:** FastAPI's validation response:

    ```json
    {
        "detail": [
            {
                "type": "missing",
                "loc": ["body", "claim_token"],
                "msg": "Field required",
                "input": {}
            }
        ]
    }
    ```

  * **Description:** Missing, empty or non-string tokens and
    malformed JSON fail body validation. The example shows
    a missing token; validation details depend on the error.
    No cookie is set.

<!-- Notes -->

---

**Notes:**

* The IP's `APPLICATION` rate limit and block checks apply
  at the users router level before the endpoint executes.
* Origin middleware protects `/users`, `/agent` and
  `/agent-memory` before route dependencies run.
* Set `COOKIE_DOMAIN` in each environment's configuration.
  Use a hostname such as `example.com`, without a scheme,
  path or port. Startup rejects missing or blank values.
  The API host must match this domain or be its subdomain.
* Browser requests must use `credentials: 'include'` to accept
  the cookie when the frontend and API have different origins.
* HTTPS is required for the secure cookie. `SameSite=Lax`
  assumes the frontend and API are on the same site, including
  separate subdomains. Cross-site deployments need a reviewed
  cookie policy in `api/config/cookies.py`.
* Repeated claims reuse the supplied token without extending
  its expiry. A token that expires during the checks is denied.
