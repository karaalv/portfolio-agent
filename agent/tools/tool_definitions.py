"""
This module contains the tool definitions 
for the agent.
"""
import textwrap
from openai.types.responses import ToolParam

agent_tools: list[ToolParam] = [
    # RAG System Tool
    {
        "type": "function",
        "name": "fetch_context",
        "description": textwrap.dedent("""
            A tool for retrieving contextually relevant
            information from the Retrieval-Augmented Generation
            (RAG) system.

            This tool must be used whenever the user's request
            requires specific knowledge about Alvin Karanja,
            including details about his background, experience,
            projects, or any profile-related information.

            Do not attempt to answer such questions based on
            general knowledge or assumptions—always invoke this
            tool to ensure the response is accurate, grounded,
            and context-aware.

            The tool returns content that enables the agent to
            respond as Alvin with informed, precise answers.
        """),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "user_input": {
                    "type": "string",
                    "description": (
                        "The user's input exactly as received, "
                        "verbatim. This is used to trigger the "
                        "appropriate retrieval process."
                    )
                }
            },
            "required": ["user_input"],
            "additionalProperties": False
        }
    },
    # Resume Generation Tool
    {
        "type": "function",
        "name": "generate_resume",
        "description": textwrap.dedent("""
            Generates a professional, tailored resume for the
            user. Invoke this tool only when the user explicitly
            requests a resume or CV.

            The resume will be customised to match the target
            role, company, and industry, using either:
            1. A detailed description of the position and
            relevant skills and experience.
            2. A URL to a job posting — if a URL is provided,
            it must be explicitly included in the
            `context_seed`.

            The input `context_seed` will be used by a research
            system to gather additional supporting information
            before generation, so it must be complete, specific,
            and strictly limited to job-related details.
                                       
            Do not include any personal information,
            details from conversation history, or
            unrelated content in the `context_seed`.
            It should only contain information about the
            job posting and target role.
        """),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "context_seed": {
                    "type": "string",
                    "description": textwrap.dedent("""
                        All relevant, job-specific context for
                        generating the resume. This may include:
                        - A detailed summary of the role, required
                        skills, and relevant experience.
                        - A URL to a job posting (must be explicitly
                        included here if provided).
                        - The company name and any other details
                        useful for tailoring the resume.

                        Only invoke this tool when sufficient
                        job-related context is available to produce
                        an accurate, high-quality resume. If
                        information is incomplete, prompt the user
                        for missing details before calling it.
                    """)
                }
            },
            "required": ["context_seed"],
            "additionalProperties": False
        }
    },
    # Cover Letter Generation Tool
    {
        "type": "function",
        "name": "generate_letter",
        "description": textwrap.dedent("""
            Generates a professional, tailored cover letter for
            the user. Invoke this tool only when the user
            explicitly requests a cover letter.

            The letter will be customised to match the target
            role, company, and industry, using either:
            1. A detailed description of the position and the
            user's relevant skills and experience.
            2. A URL to a job posting — if a URL is provided,
            it must be explicitly included in the
            `context_seed`.

            The input `context_seed` will be used by a research
            system to gather additional supporting information
            before generation, so it must be complete, specific,
            and strictly limited to job-related details.
        """),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "context_seed": {
                    "type": "string",
                    "description": textwrap.dedent("""
                        All relevant, job-specific context for
                        generating the cover letter. This may include:
                        - A detailed summary of the role, required
                        skills, and relevant experience.
                        - A URL to a job posting (must be explicitly
                        included here if provided).
                        - The company name and any other details
                        useful for tailoring the letter.

                        Do not include any personal information,
                        details from conversation history, or
                        unrelated content in the `context_seed`.
                        It should only contain information about the
                        job posting and target role.

                        Only invoke this tool when sufficient
                        job-related context is available to produce
                        an accurate, high-quality cover letter. If
                        information is incomplete, prompt the user
                        for missing details before calling it.
                    """)
                }
            },
            "required": ["context_seed"],
            "additionalProperties": False
        }
    }
]