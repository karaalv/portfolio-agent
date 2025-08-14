"""
This module acts as the main interface
for specific agent tools. The rag system
is managed in the rag package.
"""
from common.utils import handle_exceptions_async
from agent.tools.resume_constructor import ResumeConstructor

@handle_exceptions_async("agent.tools.main: Generate Resume")
async def generate_resume(
    user_id: str,
    context_seed: str,
    verbose: bool
) -> str:
    """
    Generate a resume for the user based on
    their context and research.
    """

    resume_constructor = ResumeConstructor(
        user_id=user_id,
        context_seed=context_seed,
        verbose=verbose
    )

    return await resume_constructor.construct_resume()

async def generate_letter(
    user_id: str,
    context_seed: str,
    verbose: bool
):
    # TODO Complete cover letter generation logic
    pass
