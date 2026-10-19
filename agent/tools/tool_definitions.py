"""
The single retrieval function exposed to the portfolio model.
"""

from openai.types.responses import ToolParam

from schemas.agent.tools import AgentToolName

AGENT_TOOL_DEFINITIONS: list[ToolParam] = [
	{
		'type': 'function',
		'name': AgentToolName.FETCH_CONTEXT,
		'description': (
			'Retrieve grounded information about Alvin '
			"Karanja's "
			'background, experience, projects, and skills. '
			'Use before making portfolio claims when this turn '
			'has no sufficient retrieved context. Empty results '
			'mean the requested facts cannot be confirmed '
			'from the portfolio corpus.'
		),
		'strict': True,
		'parameters': {
			'type': 'object',
			'properties': {
				'user_input': {
					'type': 'string',
					'description': (
						'The current visitor message, '
						'copied verbatim.'
					),
				}
			},
			'required': ['user_input'],
			'additionalProperties': False,
		},
	}
]
