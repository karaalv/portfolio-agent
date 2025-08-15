"""
This module acts as the main interface
for specific agent tools. The rag system
is managed in the rag package.
"""
from common.utils import handle_exceptions_async, TerminalColors
from agent.tools.resume_constructor import ResumeConstructor
from agent.tools.letter_constructor import LetterConstructor

@handle_exceptions_async("agent.tools.main: Generate Resume")
async def generate_resume(
    user_id: str,
    context_seed: str,
    verbose: bool
) -> dict[str, str]:
    """
    Generate a resume for the user based on
    their context and research.
    """

    resume_constructor = ResumeConstructor(
        user_id=user_id,
        context_seed=context_seed,
        verbose=verbose
    )

    response = await resume_constructor.construct_resume()

    if verbose:
        print(
            f"{TerminalColors.blue}"
            f"\n--- Resume construction result ---\n"
            f"{TerminalColors.reset}"
            f"{response}"
        )

    return response

@handle_exceptions_async("agent.tools.main: Generate Letter")
async def generate_letter(
    user_id: str,
    context_seed: str,
    verbose: bool
):
    """
    Generate a cover letter for the user based
    on their context and research.
    """

    letter_constructor = LetterConstructor(
        user_id=user_id,
        context_seed=context_seed,
        verbose=verbose
    )

    response = await letter_constructor.construct_letter()

    if verbose:
        print(
            f"{TerminalColors.blue}"
            f"\n--- Cover letter construction result ---\n"
            f"{TerminalColors.reset}"
            f"{response}"
        )

    return response
