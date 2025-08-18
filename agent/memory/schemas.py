"""
This module contains the schemas for 
agent memory management
"""
from pydantic import BaseModel, Field
from common.utils import get_timestamp
from typing import Optional

class AgentCanvas(BaseModel):
    """
    Represents canvas content associated
    with a specific user interaction
    """
    id: str = Field(
        ...,
        description="The unique identifier for "
                    "the agent's canvas"
    )
    title: str = Field(
        ...,
        description="The title of the canvas"
    )
    content: Optional[str] = Field(
        default=None,
        description="The content of the canvas, if any"
    )

class AgentMemory(BaseModel):
    """
    Represents a memory of a single
    interaction with the agent
    """
    id: str = Field(
        ...,
        description="The unique identifier for "
                    "the agent's memory"
    )
    user_id: str = Field(
        ...,
        description="The unique identifier for "
                    "the user associated with the memory"
    )
    source: str = Field(
        ...,
        description="The source of the memory either"
                    "user | agent"
    )
    content: str = Field(
        ...,
        description="The content of the memory"
    )
    created_at: str = Field(
        default_factory=get_timestamp,
        description="The timestamp when the memory was created"
    )
    illusion: bool = Field(
        default=False,
        description="Illusion flag to indicate if message "
                    "is should be \"streamed\" in UI"
    )
    agent_canvas: Optional[AgentCanvas] = Field(
        default=None,
        description="The canvas associated with the memory"
    )