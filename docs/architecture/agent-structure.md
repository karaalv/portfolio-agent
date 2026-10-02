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
