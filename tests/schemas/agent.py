"""
Captured live agent events used to verify replay and storage.
"""

from dataclasses import dataclass, field

from openai.types.responses import ResponseInputParam


@dataclass
class AgentTrace:
	"""
	Record model inputs, completed outputs and streamed text.
	"""

	inputs: list[ResponseInputParam] = field(
		default_factory=list
	)
	outputs: list[ResponseInputParam] = field(
		default_factory=list
	)
	deltas: list[str] = field(default_factory=list)
	closed: int = 0
