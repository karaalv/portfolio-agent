# Anonymous visitor authentication

## Identity and access tokens

The agent operates without login sessions. Each visitor has a
server-generated `user_id`. A signed JWT authenticates that
identity and scopes access to the visitor's records.

Access tokens use `HS256` with the environment's `JWT_SECRET`.
The secret is read from the process environment when tokens are
created or validated, after environment loading. A missing or
blank secret is a configuration failure.

Each token contains:

- `sub`: the visitor's `user_id`.
- `iat`: the issuance time as a UTC NumericDate.
- `exp`: the expiry time, six days after issuance.

Tokens are signed, not encrypted. They must not contain secrets
or other sensitive visitor data. There are no refresh tokens or
application-level frontend tokens.

## Issuance and cookie claiming

1. A visitor sends their first message over WebSocket.
2. The WebSocket controller creates the anonymous user, binds
   the connection to that identity and issues an access token.
3. The server sends the token to the frontend over WebSocket.
4. The frontend submits it to a dedicated HTTP cookie-claim
   endpoint.
5. That endpoint validates the token and sets an `HttpOnly`,
   `Secure` cookie with a lifetime bounded by token expiry.
6. Subsequent HTTP requests and WebSocket handshakes use the
   cookie to authenticate the visitor.

Opening the site or establishing a WebSocket connection does
not create a user. Cookie claiming does not change the identity
already bound to the original connection.

## Validation and request scoping

Authentication verifies the signature using the fixed `HS256`
algorithm, checks expiry and requires `sub`, `iat` and `exp`.
The subject must be a non-empty string. User identity comes
exclusively from the verified token, not a client-supplied ID.

Expired, malformed or otherwise invalid tokens cannot grant
access to existing visitor data. A new anonymous interaction
may receive a new identity through the issuance flow.

## API protections

The API must serve traffic over HTTPS and secure WebSockets.
WebSocket handshakes must check an explicit Origin allowlist;
HTTP CORS settings alone do not protect WebSocket connections.
The cookie-claim endpoint must also enforce the allowed origins.

The cookie's `SameSite` policy must match the deployment's site
relationship. Prefer `Lax` or `Strict` where possible; cross-site
cookies require `SameSite=None` and `Secure`. Cookie path and
domain must permit the intended API and WebSocket requests.

Long-lived WebSocket connections must enforce token expiry and
stop authenticated operations once the token expires.

## Expiry and data retention

Token expiry is fixed at six days from issuance. Data retention
is separately based on seven days of visitor inactivity. Issuing
a token must coincide with creating the user or recording their
activity, providing a one-day buffer before inactivity cleanup.

An unexpired token does not guarantee that its user record still
exists, for example after explicit deletion. Controllers must
still handle missing records explicitly.

## Implementation boundary

JWT creation and validation are implemented in
`authorisation/jwt`. Cookie claiming, HTTP dependencies and
WebSocket authentication will be connected during the API
refactor.
