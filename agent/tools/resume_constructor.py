"""
This module contains the resume constructor
system and associated utilities. The main
interface function can be found in the
`main.py` file in the agent tools package.
"""
import textwrap
from common.utils import TerminalColors
from agent.tools.schemas import ResearchPlan
from openai_client.main import normal_response, structured_response
from agent.tools.utils import researcher
from rag.query_planner import query_planner
from rag.query_executor import retrieve_documents_sequential, refine_context

class ResumeConstructor:
    """
    Class to construct resume based 
    on user input. 

    The class manages the construction
    process and associated state management
    for the operation.
    """
    def __init__(
        self, 
        user_id: str,
        context_seed: str,
        verbose: bool
    ):
        self.user_id = user_id
        self.context_seed = context_seed
        self.verbose = verbose
        self._planner_model = "gpt-4.1"
        self._refiner_model = "gpt-4.1-mini"
        self._formatter_model = "gpt-4.1-mini"
        self.research = ""
        self.resume = ""

    # --- Utilities ---

    async def _get_research_plan(self) -> ResearchPlan:
        """
        Constructs a research plan based on the
        context seed provided by the user.
        
        Returns:
            ResearchPlan: The constructed research plan.
        """

        system_prompt = textwrap.dedent(f"""
            You are an expert research planner for a resume
            generation tool. You are part of a pipeline that
            generates targeted research plans from a given
            context seed.

            Your role is to produce a concise list of research
            prompts that will guide a research agent in
            gathering only the most relevant and high-value
            information for the resume generation task.

            The context seed may include:
            - Job description details
            - URLs to job postings
            - Company names or entities to research

            Rules:
            1. If a URL is provided, include it as its own
            list item for the research agent.
            2. If a company or entity is mentioned, create a
            query to research its mission, values, focus,
            and key offerings.
            3. If no research-worthy information is present
            in the context seed, output an empty list.
            4. Ensure the plan targets information that will
            help tailor a resume — such as specific skills,
            experiences, and achievements aligned with the
            job description and company mission.
            5. Keep the search plan succinct, focused, and
            free of irrelevant or generic queries.
            6. Output no more than 3 queries.

            Your output should be a clear, actionable list
            ready for execution by the research agent.
        """)

        research_plan = await structured_response(
            system_prompt=system_prompt,
            user_input=self.context_seed,
            response_format=ResearchPlan,
            model=self._planner_model
        )

        if self.verbose:
            print(
                f"{TerminalColors.magenta}"
                f"Research Plan:\n"
                f"{TerminalColors.reset}"
                f"{research_plan}\n"
            )

        return research_plan

    async def _perform_research(self):
        """
        Performs research based on the
        research plan, research is added
        to class instance.
        """
        research_plan = await self._get_research_plan()

        for plan in research_plan.queries:
            research = await researcher(plan)
            
            if self.verbose:
                print(
                    f"{TerminalColors.cyan}"
                    f"Research Results for '{plan}':\n"
                    f"{TerminalColors.reset}"
                    f"{research}\n"
                )
            
            self.research += research

        await self._refine_research()

    async def _refine_research(self):
        """
        Refines the research conducted by the
        research agent, focusing on extracting
        the most relevant information for the
        resume generation task.
        """
        system_prompt = textwrap.dedent(f"""
            You are an expert research refiner for a resume
            generation tool. Your role is to distill the
            research findings into a concise summary that
            highlights the most relevant information for
            the resume generation task.

            Your output should focus on:
            - Key skills and experiences that align with
              the job description
            - Achievements and contributions that demonstrate
              the candidate's value
            - Any other information that would help tailor
              the resume to the specific job opportunity

            Ensure your summary is clear, actionable, and
            free of irrelevant details.
        """)

        refined_research = await normal_response(
            system_prompt=system_prompt,
            user_input=self.research,
            model=self._refiner_model
        )

        if self.verbose:
            print(
                f"{TerminalColors.cyan}"
                f"Refined Research:\n"
                f"{TerminalColors.reset}"
                f"{refined_research}\n"
            )

        self.research = refined_research

    async def _fetch_context(
        self, 
        section_query: str
    ) -> str:
        """
        Fetches context from the RAG system
        based on the information needed for 
        the specific section.
        """
        plan = await query_planner(section_query)
        context = await retrieve_documents_sequential(
            user_id=self.user_id,
            query_plan=plan,
            verbose=self.verbose
        )
        refined_context = await refine_context(
            user_input=section_query,
            retrieval_results=context
        )

        if self.verbose:
            print(
                f"{TerminalColors.green}"
                f"Context for '{section_query}':\n"
                f"{TerminalColors.reset}"
                f"{refined_context}\n"
            )

        return refined_context
    
    # --- Resume Sections ---

    def _header_section(self):
        """
        Constructs the header section of the 
        resume.
        """
        header = "## Alvin Karanja\n <br>"
        header += "**Email:** alviinkaranjja@gmail.com - "
        header += "**LinkedIn:** [Alvin Karanja](https://www.linkedin.com/in/alvin-n-karanja/) - "
        header += "**GitHub:** [karaalv](https://github.com/karaalv) - "
        header += "**Portfolio:** [alvinkaranja.dev](https://alvinkaranja.dev)"
        header += "\n"

        if self.verbose:
            print(
                f"{TerminalColors.yellow}"
                f"Header Section:\n"
                f"{TerminalColors.reset}"
                f"{header}"
            )

        self.resume += header

    async def _skills_section(self):
        """
        Constructs the skills section of the 
        resume.
        """
        # Input Refinement
        input_refiner_prompt = textwrap.dedent(f"""
            You are part of a resume generation tool, responsible
            for creating the skills section of the resume.

            Using the job description and research findings,
            produce one clear, precise prompt for the RAG system
            that will retrieve the most relevant skills for the
            target role. The prompt should focus on skills,
            technologies, and methodologies that are directly
            aligned with the role and industry context.

            Example (for a software engineer):
            "What are your skills related to software development,
            programming languages, and frameworks such as Python,
            Java, React, and Agile methodologies?"

            Rules:
            - Output only one prompt, no alternatives or extra text.
            - Make the prompt specific to the provided context.
            - Ensure it covers both technical and soft skills
            if relevant to the role.

            Context for resume creation:
            - Research findings: {self.research}
            - Job description: {self.context_seed}
        """)

        skills_query = await normal_response(
            system_prompt=input_refiner_prompt,
            user_input=self.context_seed,
            model=self._refiner_model
        )

        if self.verbose:
            print(
                f"{TerminalColors.cyan}"
                f"Skills Section Prompt:\n"
                f"{TerminalColors.reset}"
                f"{skills_query}\n"
            )

        skills_context = await self._fetch_context(skills_query)

        # Formatter
        formatter_prompt = textwrap.dedent(f"""
            You are part of a resume generation tool, responsible
            for formatting the skills section.

            Using the job description, company research, and
            contextual details about the individual's skills,
            produce a succinct, well-organized skills list
            tailored to the target role and company.

            Current resume context:
            {self.resume}

            Output format rules:
            1. Use markdown.
            2. Group related skills on the same line, separated
            by commas.
            3. Start each line with a bold skill category name,
            followed by a colon, e.g.:
            **Programming Languages**: Python, Java, JavaScript
            **Frameworks**: React, Angular, Django
            **Tools**: Git, Docker, Jenkins
            4. Only include relevant skills for the role and
            company — remove unrelated or redundant items.

            Context for resume creation:
            - Research findings: {self.research}
            - Job description: {self.context_seed}
            - Skills context: {skills_context}
        """)

        formatted_skills = await normal_response(
            system_prompt=formatter_prompt,
            user_input=skills_context,
            model=self._formatter_model
        )

        title = "### Skills\n---"
        skills_section = f"{title}\n{formatted_skills}\n"

        if self.verbose:
            print(
                f"{TerminalColors.yellow}"
                f"Formatted Skills Section:\n"
                f"{TerminalColors.reset}"
                f"{skills_section}"
            )

        self.resume += skills_section

    async def _experience_section(self):
        """
        Constructs the experience section of the
        resume.
        """
        # Input Refinement
        input_refiner_prompt = textwrap.dedent(f"""
            You are part of a resume generation tool, responsible
            for creating the experience section of the resume.

            Using the job description and research findings,
            produce one clear, precise prompt for the RAG system
            that will retrieve the most relevant experience for the
            target role. The prompt should focus on job titles,
            responsibilities, and achievements that are directly
            aligned with the role and industry context.

            Example (for a software engineer):
            "What is your experience related to software development,
            programming languages, and frameworks such as Python,
            Java, React, and Agile methodologies?"

            Rules:
            - Output only one prompt, no alternatives or extra text.
            - Make the prompt specific to the provided context.
            - Ensure it covers both technical and soft skills
            if relevant to the role.

            Context for resume creation:
            - Research findings: {self.research}
            - Job description: {self.context_seed}
        """)

        experience_query = await normal_response(
            system_prompt=input_refiner_prompt,
            user_input=self.context_seed,
            model=self._refiner_model
        )

        if self.verbose:
            print(
                f"{TerminalColors.cyan}"
                f"Experience Section Prompt:\n"
                f"{TerminalColors.reset}"
                f"{experience_query}\n"
            )

        experience_context = await self._fetch_context(experience_query)

        # Formatter
        formatter_prompt = textwrap.dedent(f"""
            You are part of a resume generation tool, responsible
            for formatting the experience section.

            Using the job description, company research, and
            contextual details about the individual's experience,
            produce a concise, well-structured experience list
            tailored to the target role and company.

            Current resume context:
            {self.resume}

            Output format rules:
            1. Use markdown.
            2. Company name: bold on its own line.
            3. Role title: italicized, placed on the line
            immediately after the company name.
            Example:
            **Company Name**
            *Job Title*
            4. For each role, list relevant tasks and
            accomplishments as bullet points:
            - Start with the broad skill in bold,
                followed by a colon and a short,
                specific description of the task
                or achievement.
            - Example:
                - **Project Management**: Led a team of
                5 engineers to deliver X in Y months.
            5. Ensure all bullet points are:
            - Relevant to the target role and company.
            - Quantified where possible (metrics, %
                improvements, timelines, etc.).
            - Highlighting standout or unique
                contributions.

            Context for resume creation:
            - Research findings: {self.research}
            - Job description: {self.context_seed}
            - Experience context: {experience_context}
        """)

        formatted_experience = await normal_response(
            system_prompt=formatter_prompt,
            user_input=experience_context,
            model=self._formatter_model
        )

        title = "### Experience\n---"
        experience_section = f"{title}\n{formatted_experience}\n"
        
        if self.verbose:
            print(
                f"{TerminalColors.yellow}"
                f"Formatted Experience Section:\n"
                f"{TerminalColors.reset}"
                f"{experience_section}"
            )
        
        self.resume += experience_section
    
    async def _projects_section(self):
        """
        Constructs the projects section of the
        resume.
        """
        # Input Refinement
        input_refiner_prompt = textwrap.dedent(f"""
            You are part of a resume generation tool, responsible
            for creating the projects section of the resume.

            Using the job description and research findings,
            produce one clear, precise prompt for the RAG system
            that will retrieve the most relevant projects for the
            target role. The prompt should focus on project titles,
            descriptions, technologies used, and outcomes that are
            directly aligned with the role and industry context.

            Example (for a software engineer):
            "What projects have you worked on related to software
            development, programming languages, and frameworks such
            as Python, Java, React, and Agile methodologies?"

            Rules:
            - Output only one prompt, no alternatives or extra text.
            - Make the prompt specific to the provided context.
            - Ensure it covers both technical and soft skills
              if relevant to the role.

            Context for resume creation:
            - Research findings: {self.research}
            - Job description: {self.context_seed}
        """)

        projects_query = await normal_response(
            system_prompt=input_refiner_prompt,
            user_input=self.context_seed,
            model=self._refiner_model
        )

        if self.verbose:
            print(
                f"{TerminalColors.cyan}"
                f"Projects Section Prompt:\n"
                f"{TerminalColors.reset}"
                f"{projects_query}\n"
            )

        projects_context = await self._fetch_context(projects_query)

        # Formatter
        formatter_prompt = textwrap.dedent(f"""
            You are part of a resume generation tool, responsible
            for formatting the projects section.

            Using the job description, company research, and
            contextual details about the individual's projects,
            produce a concise, well-structured project list
            tailored to the target role and company.

            Current projects context:
            {projects_context}

            Output format rules:
            1. Use markdown.
            2. Project title: bold on its own line.
            3. Under the title, list relevant technologies used.
            Format as:
            Technologies: Python, React, Docker
            4. For each project, list outcomes as bullet points:
            - Begin with a bold tag naming a key skill
                relevant to the role and/or company values.
            - Follow with a brief, quantified description
                of the contribution or achievement.
            - Example:
                - **Leadership**: Led a team of 5 to deliver
                a feature increasing engagement by 20%.
            5. Include only projects relevant to the job
            description or company values.
            - Exclude unrelated work experience.
            - Exclude irrelevant coursework unless it
                directly supports the role.

            Context for resume creation:
            - Research findings: {self.research}
            - Job description: {self.context_seed}
            - Projects context: {projects_context}
        """)

        formatted_projects = await normal_response(
            system_prompt=formatter_prompt,
            user_input=projects_context,
            model=self._formatter_model
        )

        title = "### Projects\n---"
        projects_section = f"{title}\n{formatted_projects}\n"

        if self.verbose:
            print(
                f"{TerminalColors.yellow}"
                f"Formatted Projects Section:\n"
                f"{TerminalColors.reset}"
                f"{projects_section}"
            )

        self.resume += projects_section
    
    async def _education_section(self):
        """
        Constructs the education section of the
        resume.
        """
        # Input Refinement
        input_refiner_prompt = textwrap.dedent(f"""
            You are part of a resume generation tool, responsible
            for creating the education section of the resume.

            Using the job description and research findings,
            produce one clear, precise prompt for the RAG system
            that will retrieve the most relevant education details
            for the target role. The prompt should focus on degrees,
            institutions, and relevant coursework that are directly
            aligned with the role and industry context.

            Example (for a software engineer):
            "What is your educational background related to software
            development, programming languages, and frameworks such
            as Python, Java, React, and Agile methodologies?"

            Rules:
            - Output only one prompt, no alternatives or extra text.
            - Make the prompt specific to the provided context.
            - Ensure it covers both technical and soft skills
              if relevant to the role.

            Context for resume creation:
            - Research findings: {self.research}
            - Job description: {self.context_seed}
        """)

        education_query = await normal_response(
            system_prompt=input_refiner_prompt,
            user_input=self.context_seed,
            model=self._refiner_model
        )

        if self.verbose:
            print(
                f"{TerminalColors.cyan}"
                f"Education Section Prompt:\n"
                f"{TerminalColors.reset}"
                f"{education_query}\n"
            )

        education_context = await self._fetch_context(education_query)

        # Formatter
        formatter_prompt = textwrap.dedent(f"""
            You are part of a resume generation tool, responsible
            for formatting the education section.

            Using the job description, company research, and
            contextual details about the individual's education,
            produce a concise, well-structured education list
            tailored to the target role and company.

            Current education context:
            {education_context}

            Output format rules:
            1. Use markdown.
            2. Institution name: bold on its own line.
            3. Degree title: italicized, placed immediately
            after the institution name.
            Example:
            **University of Example**
            *Bachelor of Science in Computer Science*
            4. Below the degree title, include notable
            achievements (degree classification, awards,
            leadership roles, notable activities) if relevant.
            5. List relevant modules as bullet points:
            - Begin with the module name in bold.
            - Follow with a short description linking
                the module to the role's requirements or
                company values.
            - Example:
                - **Financial Analytics**: Applied
                statistical models to financial datasets
                for predictive insights.
            6. Keep only content relevant to the job
            description and company values. Remove
            unrelated or generic entries.

            Context for resume creation:
            - Research findings: {self.research}
            - Job description: {self.context_seed}
            - Education context: {education_context}
        """)

        formatted_education = await normal_response(
            system_prompt=formatter_prompt,
            user_input=education_context,
            model=self._formatter_model
        )

        title = "### Education\n---"
        education_section = f"{title}\n{formatted_education}\n"

        if self.verbose:
            print(
                f"{TerminalColors.cyan}"
                f"Education Section:\n"
                f"{TerminalColors.reset}"
                f"{education_section}\n"
            )

        self.resume += education_section

    async def construct_resume(self) -> str:
        """
        Construct the resume doing each
        section sequentially, intermediary
        results are streamed to client, final
        resume is returned.
        """
        # Research phase
        await self._perform_research()

        # Build resume
        self._header_section()
        await self._skills_section()
        await self._experience_section()
        await self._projects_section()
        await self._education_section()

        return self.resume.strip()