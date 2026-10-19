"""Structured verdicts for LLM-based test evaluation."""

from pydantic import BaseModel, Field


class LLMJudgement(BaseModel):
	"""Record whether supplied data meets the test rubric."""

	satisfactory: bool = Field(
		description='True only when all rubric criteria are met.'
	)
	reason: str = Field(
		description='Brief explanation of the verdict.'
	)
