"""Configure hard limits for incoming WebSocket messages."""

MAX_CONTENT_SIZE_BYTES = 16 * 1024
MAX_TRANSPORT_MESSAGE_BYTES = 64 * 1024
MAX_INPUT_TOKENS = 10_000
INPUT_TOKEN_ENCODING = 'o200k_base'
