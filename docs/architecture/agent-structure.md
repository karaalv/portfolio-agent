# Portfolio agent structure

Status: proposed structure for the agent refactor. The streaming model will be
designed after this restructuring.

## Scope

The agent answers questions about Alvin Karanja's background, work, and
projects using retrieved portfolio context. Its only exposed tool is
`fetch_context`. CV and cover-letter generation, their supporting tools, and
the associated usage-limit logic will be removed. The agent should not invent
personal details when retrieval does not support an answer.

## Package responsibilities

| Module | Responsibility |
| --- | --- |
| `agent/main.py` | Orchestrate a user turn, prompt construction, model calls, tool calls, and memory writes. Streaming will be added separately. |
| `agent/tools/dispatch.py` | Validate and execute tool calls. Initially dispatch only `fetch_context` to `rag.main.fetch_context`. |
| `agent/tools/tool_definitions.py` | Expose only the `fetch_context` tool definition to the model. |
| `agent/prompts/agent.py` | Define the agent's portfolio identity, purpose, knowledge boundary, and answer grounding. |
| `agent/prompts/behaviour.py` | Define response behaviour and presentation rules. Specific rules remain to be decided. |
| `agent/prompts/memory.py` | Format retrieved conversation entries into prompt text without database access. |
| `agent/memory/insertion.py` | Store user and agent messages in `application.memories`. |
| `agent/memory/retrieval.py` | Fetch messages by `user_id` and provide the memory prompt to orchestration. |
| `agent/memory/deletion.py` | Delete a user's messages when memory is cleared. |
| `schemas/agent/memory.py` | Define the stored message model and related memory types. |

The memory schema belongs under `schemas/agent` because these records are part
of the agent's conversation model. A single `memory.py` file is sufficient
until the schema grows enough to justify a package.

## Memory flow

1. Store the visitor's message using `user_id`.
2. Retrieve relevant recent messages for that `user_id`.
3. Pass the retrieved records to `agent.prompts.memory` for formatting.
4. Combine the agent, behaviour, and memory prompts before the model call.
5. Store the completed agent response.

`agent.memory.retrieval` owns the database query and the convenience function
that returns prompt-ready memory. `agent.prompts.memory` owns formatting only.
This follows Mwalika's actual boundary while keeping prompt code independent
of MongoDB.

Conversation compression and user summaries will be removed. Retrieval still
needs a bounded recent-message window so an active visitor's prompt cannot
grow without limit. The window size will be chosen during implementation.

Deleting memory must delete the matching records from `application.memories`.
It must not copy them into another database first. Inactive users and their
messages remain subject to the [seven-day retention policy](../system-features/data-retention.md).

## Removal during implementation

- CV and cover-letter tool definitions, constructors, canvas memory, and their
  agent orchestration branches.
- Compression and conversation-summary code and fields.
- Generation-specific usage limits and messaging.
- Prompt instructions referring to removed capabilities.

The existing `rag` package remains the retrieval implementation behind
`fetch_context` for this phase. Its internal simplification is a separate
decision from reducing the agent's exposed tools.

## Prompt decision to settle

The current prompt tells the agent to impersonate Alvin. Before writing the
new `agent/prompts/agent.py`, decide whether it should speak as Alvin in the
first person or identify itself as a portfolio assistant speaking about him.


## Execution timing

`agent.observability.AgentTimer` records one interaction across
all recursive model rounds. Callers can pass a fresh timer to
`agent_chat` and inspect its immutable `records` snapshot after
execution. Terminal output is handled separately by
`agent.logging.terminal.log_agent_timing`.

- Interaction duration includes history retrieval, persistence,
  model rounds, tools and response queueing.
- OpenAI duration runs from starting stream consumption until
  the terminal event. It includes local limiter waits, network
  latency and streamed output handling. Final output persistence,
  stream cleanup and subsequent tool execution are excluded.
- Tool duration covers each individual dispatch, including RAG
  planning, retrieval and context refinement. Parallel tool calls
  have independent spans and retain their call IDs in the names.

Durations use a monotonic performance clock. Nested and parallel
spans overlap, so their sum is not the total interaction time.
Records are emitted in completion order. Stream status retains
the SDK terminal event name; a stream without a terminal event
is marked `interrupted`. Other spans record completion, an
exception or cancellation. A completed tool span means dispatch
returned, including a recoverable failure packaged for replay.

The input and context refiners use the separate
`INPUT_REFINER_REASONING` and `CONTEXT_REFINER_REASONING` settings
in `rag.config`, both defaulting to `LOW`.

## AI conversation traces

Each `agent_chat` invocation captures one explicit PostHog
`$ai_trace` event when it finishes, including failed and cancelled
turns. Its trace ID matches the OpenTelemetry turn trace and the
ID passed to every nested generation and embedding call.

- `$ai_input_state` contains the current visitor message.
- `$ai_output_state` contains the assembled visible assistant text
  across response rounds, including partial text on failure.
  No emitted text produces an empty output list.
- `$ai_latency` measures the whole turn, including persistence and
  response cleanup. The event timestamp records its start.
- `$ai_span_name` is `Portfolio chat`. The event includes the turn,
  AI session and optional browser replay session identifiers.
- Non-completed outcomes set `$ai_is_error`; `$ai_error` records
  the exception class or outcome without copying exception details.

Generation events retain their detailed model inputs and outputs.
The root trace provides the visitor-question-to-answer view; it
omits system prompts, retrieved history and internal tool payloads.
Capture runs in development, staging and production, not testing.
Capture failures are logged without replacing the agent outcome.
Existing traces are not backfilled.
