The following document describes the schema for the agent's memory.

```python
class AgentMemory(BaseModel):
    memory_id: str
    user_id: str
    memory_source: AgentMemorySource
    created_at: datetime
    content: str
```

Note that the enum `AgentMemorySource` defines the possible sources of the memory, such as `user` or `agent`.

```python
class AgentMemorySource(StrEnum):
    USER = 'user'
    AGENT = 'agent'
```
