"""
This module contains the cover letter 
constructor and associated utilities.
The main interface function can be found 
in the `main.py` file in the agent tool
package.
"""
import textwrap
from typing import Any
from common.utils import TerminalColors, Timer, get_timestamp
from agent.tools.schemas import ResearchPlan
from api.common.socket_manager import SocketManager
from agent.memory.schemas import AgentMemory, AgentCanvas
from openai_client.main import normal_response, structured_response
from agent.tools.utils import researcher
from rag.query_planner import query_planner
from rag.query_executor import retrieve_documents_sequential, refine_context
from api.common.socket_registry import get_connection_registry

class LetterConstructor:
    """
    Class to construct cover letters
    on user input.

    Class manages the construction process
    and associated state management for
    the operation.
    """
    def __init__(
        self, 
        user_id: str,
        context_seed: str,
        verbose: bool
    ):
        # Input
        self.user_id = user_id
        self.context_seed = context_seed
        self.verbose = verbose
        # Models
        self._planner_model = "gpt-4.1-mini"
        self._refiner_model = "gpt-4.1-nano"
        self._formatter_model = "gpt-4.1-nano"
        self._response_model = "gpt-4.1-nano"
        # Content
        self.title = ""
        self.research = ""
        self.letter = ""
        self.acknowledgment = ""
        self.summary = ""
        # Utils
        self.message_id = f"streaming_{get_timestamp()}"
        self.timer = Timer(start=False)
        self._passthrough_prompt = "Obey the system prompt"
        # Socket connection
        socket_connection = get_connection_registry(user_id)
        if socket_connection is None:
            raise ValueError(
                "No active WebSocket connection found for user."
            )
        self.socket_manager: SocketManager = socket_connection

    # --- Utilities ---

    async def _send_message_ws(
        self,
        type: str,
        data: Any,
        success: bool = True,
        message: str = "Data sent successfully"
    ):
        await self.socket_manager.send_message(
            type=type,
            data=data,
            success=success,
            message=message
        )

    async def _update_writing_state_ws(self):
        """
        Used to update the client
        writing state with messages
        and progress updates.
        """
        update = AgentMemory(
            id=self.message_id,
            user_id=self.user_id,
            source="agent",
            content=self.acknowledgment + self.summary,
            illusion=True,
            agent_canvas=AgentCanvas(
                title=self.title,
                id=self.message_id + "_canvas",
                content=self.letter
            )
        )

        await self._send_message_ws(
            type="agent_writing",
            data=update.model_dump(),
        )

    async def _get_research_plan(self) -> ResearchPlan:
        """
        Constructs a research plan based on the
        context seed provided by the user.
        
        Returns:
            ResearchPlan: The constructed research plan.
        """
        system_prompt = textwrap.dedent(f"""
            You are an expert research planner for a cover letter
            generation tool. You are part of a pipeline that
            generates targeted research plans from a given
            context seed.

            Your role is to produce a concise list of research
            prompts that will guide a research agent in
            gathering only the most relevant and high-value
            information for the cover letter generation task.

            The context seed may include:
            - Job description details
            - URLs to job postings
            - Company names or entities to research

            Rules:
            1. If a URL is provided, include it as its own
            list item for the research agent.
            2. If a company or entity is mentioned, create a
            query to research its mission, values, focus,
            key offerings, and the address of its main
            headquarters.
            3. If no research-worthy information is present
            in the context seed, output an empty list.
            4. Focus only on information that will help
            tailor a cover letter — e.g., relevant skills,
            experiences, and achievements that align with
            the job description and company mission.
            5. Keep queries succinct, specific, and free from
            irrelevant or generic searches.
            6. Output no more than 3 queries.

            Your output should be a clear, actionable list
            ready for execution by the research agent.

            The context is as follows:
            {self.context_seed}
        """)

        research_plan = await structured_response(
            system_prompt=system_prompt,
            user_input=self._passthrough_prompt,
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
    
    async def _refine_research(self):
        """
        Refines the research conducted by the
        research agent, focusing on extracting
        the most relevant information for the
        cover letter generation task.
        """
        system_prompt = textwrap.dedent(f"""
            You are an expert research refiner for a cover 
            letter generation tool. Your role is to distill 
            the research findings into a concise summary 
            that highlights the most relevant information 
            for the cover letter generation task.

            Your output should focus on:
            - Key skills and experiences that align with 
            the job description
            - Achievements and contributions that 
            demonstrate the candidate's value
            - Key aspects of the entity if named, such as 
            company values, mission statements and culture.

            Ensure your summary is clear, actionable, and 
            free of irrelevant details.

            The research is as follows:
            {self.research}
        """)

        refined_research = await normal_response(
            system_prompt=system_prompt,
            user_input=self._passthrough_prompt,
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
    
    async def _perform_research(self):
        """
        Performs research based on the
        research plan, research is added
        to class instance.
        """
        research_plan = await self._get_research_plan()
        queries: list[str] = research_plan.queries

        if len(queries) > 0:
            await self._send_message_ws(
                type="agent_writing_phase",
                data="Researching job description and requirements"
            )

        if len(queries) > 3:
            queries = queries[:3]

        for plan in queries:
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
            streaming_context="agent_writing_thinking",
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
    
    async def _acknowledge_request(self):
        """
        Acknowledges the user's request and provides
        a brief summary of the information being used
        to create a cover letter.
        """
        acknowledgment_prompt = textwrap.dedent(f"""
            You are an acknowledgment model in a cover letter 
            generation pipeline for my personal portfolio website.

            Your task is to confirm to the user that their cover 
            letter request is being processed using the provided 
            context. Give a brief, clear confirmation summarizing 
            what the user requested—no extra details or unrelated 
            content.
                                                    
            Note: You are addressing a user on my website, so your 
            response should follow the style:
                                                    
            "Thank you for your request, I will now begin writing 
            a cover letter for <role> at <company>."

            Context for request:
            {self.context_seed}
        """)

        response = await normal_response(
            system_prompt=acknowledgment_prompt,
            user_input=self._passthrough_prompt,
            model=self._response_model
        )

        title_prompt = textwrap.dedent(f"""
            You are part of a cover letter generation tool.
            Generate a short, professional title for the cover
            letter based on the user's request and context.

            Rules:
            - Keep it concise (max 6 words).
            - Clearly reflect the target role or request.
            - Format it as a standalone title (no extra text).

            Example:
            Request: software engineering position
            Title: "Software Engineer Application"

            Context for request:
            {self.context_seed}
        """)

        title = await normal_response(
            system_prompt=title_prompt,
            user_input=self._passthrough_prompt,
            model=self._response_model
        )
        self.title = title

        if self.verbose:
            print(
                f"{TerminalColors.magenta}"
                f"Acknowledgment:\n"
                f"{TerminalColors.reset}"
                f"{response}"
            )

        self.acknowledgment = response
        await self._update_writing_state_ws()

    async def _summarise_request(self):
        """
        Summarises the resume creation process.
        """
        summary_prompt = textwrap.dedent(f"""
            You are part of a cover letter generation tool.
            Your task is to read the generated cover letter
            and produce a very brief summary of its contents.

            Rules:
            - Base the summary only on what is written in the 
            cover letter.
            - Keep it concise (1-3 sentences max).
            - Do not add new information or commentary.
            - Continue to use first person in the response,
            respond as if you are the one who created the
            resume.
                                            
            Note: You are addressing a visitor on my website,
            so respond in a friendly, professional style such as:

            "I have finished writing the cover letter, it covers"
            the following points: [summary of the letter].

            The generated cover letter is:
            {self.letter}
        """)

        response = await normal_response(
            system_prompt=summary_prompt,
            user_input=self._passthrough_prompt,
            model=self._response_model
        )

        if self.verbose:
            print(
                f"{TerminalColors.cyan}"
                f"Summary:\n"
                f"{TerminalColors.reset}"
                f"{response}"
            )

        self.summary = response
        await self._update_writing_state_ws()
        
        # End writing state on client
        await self._send_message_ws(
            type="agent_writing_phase",
            data="<complete>"
        )

    # --- Letter Sections ---

    async def _header_section(self):
        """
        Constructs the header section 
        of the cover letter.
        """
        await self._send_message_ws(
            type="agent_writing_phase",
            data="Writing header section..."
        )

        header = "<div align='center'><h2>Alvin Karanja</h2></div>\n\n"
        header += "<br>London, United Kingdom\n\n"
        header += "**Email:** alviinkaranjja@gmail.com\n\n"
        header += "**LinkedIn:** /in/alvin-n-karanja\n\n"
        header += "**Website:** alvinkaranja.dev\n\n"

        if self.verbose:
            print(
                f"{TerminalColors.yellow}"
                f"Header Section:\n"
                f"{TerminalColors.reset}"
                f"{header}\n"
            )

        self.letter += header
        await self._update_writing_state_ws()

    async def _address_section(self):
        """
        Constructs the address section of 
        the resume.
        """
        await self._send_message_ws(
            type="agent_writing_phase",
            data="Writing letter address..."
        )

        formatter_prompt = textwrap.dedent(f"""
            You are part of a cover letter generation tool, 
            and your task is to refine the address section of 
            the cover letter. You will be given the research 
            context for the cover letter and the initial input 
            context for the cover letter generation task. 
            Your job is to simply format the address section.

            The address section should include:
            - the name of the contact if passed
            - the current month and year
            - the name of the company if present
            - the address of the company if present
            - the contact information for the company if present
            - the result should be in markdown, with each item 
            on a new line, thus each item should have a double
            newline character appended to the end.

            Example:
            March 2023
            Acme Corp
            123 Main St, Anytown, USA
            (123) 456-7890

            Output format rules:
            1. The first token must be the content itself
            (not 'Sure,' 'Here,' 'I will,' etc.). No preamble
            or explanation.

            Use the following information:
            Current date: {get_timestamp()}
            
            job description: 
            {self.context_seed}
            
            research context: 
            {self.research}
            
            current cover letter: 
            {self.letter}
        """)

        formatted_address = await normal_response(
            system_prompt=formatter_prompt,
            user_input=self._passthrough_prompt,
            model=self._response_model
        )

        if self.verbose:
            print(
                f"{TerminalColors.yellow}"
                f"Formatted Address:\n"
                f"{TerminalColors.reset}"
                f"{formatted_address}"
            )

        self.letter += "<br><br>" +formatted_address
        await self._update_writing_state_ws()

    async def _opening_section(self):
        """
        Constructs opening paragraph.
        """
        await self._send_message_ws(
            type="agent_writing_phase",
            data="Writing opening paragraph..."
        )

        input_refiner_prompt = textwrap.dedent(f"""
            You are part of a cover letter generation tool, tasked
            with creating a single, precise query to retrieve
            relevant context from a RAG system for the opening
            paragraph.

            The opening paragraph should:
            - Express genuine interest in the target role.
            - Highlight relevant background in the domain.

            Example: For a software engineering role, you might ask:
            "What background and interest do you have in software
            engineering?"

            Rules:
            - Output only one prompt — no alternatives or commentary.
            - Make it specific to the given context.
            - Include both technical and soft skills if relevant.

            Context for generation:
            - Research findings: 
            {self.research}
            
            - Job description: 
            {self.context_seed}
        """)

        opening_query = await normal_response(
            system_prompt=input_refiner_prompt,
            user_input=self._passthrough_prompt,
            model=self._refiner_model
        )

        if self.verbose:
            print(
                f"{TerminalColors.cyan}"
                f"Opening Section Query:\n"
                f"{TerminalColors.reset}"
                f"{opening_query}"
            )

        opening_section_context = await self._fetch_context(
            opening_query
        )

        # Writer 
        writer_prompt = textwrap.dedent(f"""
            You are part of a cover letter generation tool.
            Your task is to write the opening section of the
            cover letter using the provided context.

            The opening section must:
            - Begin with: Dear [Hiring Manager's Name],
            (if no name is provided, use "Dear Hiring Manager,")
            - Place the paragraph on the next line after the
            "Dear" greeting.
            - Include one paragraph expressing interest in the
            role.
            - Mention relevant background or experience.
            - Be compelling but not overly dramatic.
            - Be polite, relevant, and show genuine interest.
            - Use markdown formatting, to separate paragraphs,
            use a double newline character appended to the end.

            Output format rules:
            1. Keep it to one paragraph, using personal context
            to connect skills/experience with the job description.
            2. The first token must be the content itself
            (not 'Sure,' 'Here,' 'I will,' etc.). No preamble
            or explanation.

            Information provided:
            - Research context:
            {self.research}
            
            - Current cover letter:
            {self.letter}
            
            - Personal context:
            {opening_section_context}
        """)

        opening_section = await normal_response(
            system_prompt=writer_prompt,
            user_input=self._passthrough_prompt,
            model=self._response_model
        )

        if self.verbose:
            print(
                f"{TerminalColors.yellow}"
                f"Opening Section:\n"
                f"{TerminalColors.reset}"
                f"{opening_section}"
            )

        self.letter += "<br><br>" + opening_section
        await self._update_writing_state_ws()

    async def _body_section(self):
        """
        Writes body section of cover letter.
        """
        await self._send_message_ws(
            type="agent_writing_phase",
            data="Developing main body section..."
        )

        input_refiner_prompt = textwrap.dedent(f"""
            You are part of a cover letter generation tool.
            Your task is to create a single, precise query to
            retrieve relevant context from a RAG system for the
            main body of the cover letter.

            The retrieved context should help:
            - Demonstrate skills and experiences relevant to
            the role.
            - Address specific requirements and responsibilities
            in the job description.
            - Cite relevant projects that show alignment with
            the role, covering both technical and soft skills.

            Example: For a software engineering role, you might
            ask: "What experiences and projects have you worked
            on that demonstrate your skills in software
            engineering?"

            Output format rules:
            1. Output only one prompt — no alternatives or extra
            commentary.
            2. Make it specific to the provided context.
            3. Include both technical and soft skills if relevant.
            4. The first token must be the content itself
            (not 'Sure,' 'Here,' 'I will,' etc.). No preamble
            or explanation.

            Context for generation:
            - Research findings: 
            {self.research}
            
            - Job description:
            {self.context_seed}
        """)

        body_query = await normal_response(
            system_prompt=input_refiner_prompt,
            user_input=self._passthrough_prompt,
            model=self._refiner_model
        )

        if self.verbose:
            print(
                f"{TerminalColors.cyan}"
                f"Body Section Query:\n"
                f"{TerminalColors.reset}"
                f"{body_query}"
            )

        body_context = await self._fetch_context(
            body_query
        )

        # Writer
        writer_prompt = textwrap.dedent(f"""
            You are part of a cover letter generation tool.
            Your task is to write the body section of the
            cover letter using the provided context.

            The body section must:
            - Address specific requirements and responsibilities
            in the job description.
            - Cite relevant projects that show alignment with
            the role, covering both technical and soft skills.
            - Use markdown formatting, to separate paragraphs,
            use a '<br>' character appended to the end.
            - Be compelling and clearly link projects and
            experience to job requirements.
            - Consist of two comprehensive paragraphs that cite
            multiple projects and experiences positioning me
            as a strong candidate.
            - Mention that the system the user is interacting
            with is a completely custom automation solution,
            showing my ability to work with complex, tailored
            systems and demonstrating creativity and self-
            motivation.

            Keep it concise, compelling, and focused on
            demonstrating qualifications for the role.

            Output format rules:
            1. The first token must be the content itself
               (not 'Sure,' 'Here,' 'I will,' etc.). No preamble
               or explanation.

            Information provided:
            - Research context:
            {self.research}
            
            - Current cover letter:
            {self.letter}
            
            - Personal context:
            {body_context}
        """)

        body_section = await normal_response(
            system_prompt=writer_prompt,
            user_input=self._passthrough_prompt,
            model=self._response_model
        )

        if self.verbose:
            print(
                f"{TerminalColors.yellow}"
                f"Body Section:\n"
                f"{TerminalColors.reset}"
                f"{body_section}"
            )

        self.letter += "<br><br>" + body_section
        await self._update_writing_state_ws()

    async def _closing_section(self):
        """
        Write closing section of the cover
        letter.
        """
        await self._send_message_ws(
            type="agent_writing_phase",
            data="Writing closing statement..."
        )

        input_refiner_prompt = textwrap.dedent(f"""
            You are part of a cover letter generation tool.
            Your task is to create a single, precise query
            to retrieve relevant context from a RAG system
            for the closing section of the cover letter.

            The retrieved context should help:
            - Show alignment with company vision and values.
            - Cite personal beliefs and motivations that
            align with the company's mission.
            - Highlight what I can contribute to the company
            and its goals.

            Example:
            "What beliefs and values drive your work and
            motivate you?"

            Output format rules:
            1. Output only one prompt — no alternatives or
            extra commentary.
            2. Make it specific to the provided context.
            3. Only consider soft skills and psychological
            attributes.
            4. The first token must be the content itself
            (not 'Sure,' 'Here,' 'I will,' etc.). No preamble
            or explanation.

            Context for generation:
            - Research findings:
            {self.research}
            
            - Job description:
            {self.context_seed}
        """)

        closing_query = await normal_response(
            system_prompt=input_refiner_prompt,
            user_input=self._passthrough_prompt,
            model=self._refiner_model
        )

        if self.verbose:
            print(
                f"{TerminalColors.cyan}"
                f"Closing Section Query:\n"
                f"{TerminalColors.reset}"
                f"{closing_query}"
            )

        closing_context = await self._fetch_context(
            closing_query
        )

        # Writer
        writer_prompt = textwrap.dedent(f"""
            You are part of a cover letter generation tool.
            Your task is to write the closing section of the
            cover letter using the provided context.

            The first paragraph of the closing section must:
            - Show alignment with company vision and values.
            - Cite personal beliefs and motivations that align
            with the company's mission.
            - Highlight what I can contribute to the company
            and its goals.
            - Highlight what about my psychology makes me a
            strong fit for the company and its culture.
            - The result should be in markdown, with different
            paragraphs separated by a double newline character.

            The final paragraph must:
            - Thank the reader for considering my application.
            - Express eagerness to learn from the team associated
            with the role and to contribute to the company's
            mission.

            Keep it concise, compelling, and focused on
            demonstrating qualifications for the role.

            Output format rules:
            1. The first token must be the content itself
               (not 'Sure,' 'Here,' 'I will,' etc.). No preamble
               or explanation.

            Information provided:
            - Research context: 
            {self.research}
            
            - Current cover letter: 
            {self.letter}
            
            - Personal context: 
            {closing_context}
        """)

        closing_section = await normal_response(
            system_prompt=writer_prompt,
            user_input=self._passthrough_prompt,
            model=self._response_model
        )

        if self.verbose:
            print(
                f"{TerminalColors.yellow}"
                f"Closing Section:\n"
                f"{TerminalColors.reset}"
                f"{closing_section}"
            )

        self.letter += "<br><br>" + closing_section
        await self._update_writing_state_ws()

    async def _signature(self):
        """
        Write signature section of
        the cover letter.
        """
        await self._send_message_ws(
            type="agent_writing_phase",
            data="Signing off letter..."
        )

        signature = "\n\n<br>\n\n"
        signature += "Kind regards,\n\n"
        signature += "Alvin Karanja (AI)"

        if self.verbose:
            print(
                f"{TerminalColors.yellow}"
                f"Signature Section:\n"
                f"{TerminalColors.reset}"
                f"{signature}"
            )

        self.letter += signature + "<br><br>"
        await self._update_writing_state_ws()

    async def construct_letter(self) -> dict[str, str]:
        """
        Construct cover letter by doing
        each section sequentially.
        """
        self.timer.start()

        await self._acknowledge_request()
        acknowledgment_time = self.timer.elapsed()

        await self._perform_research()
        research_time = self.timer.elapsed()

        # Build cover letter
        await self._header_section()
        header_time = self.timer.elapsed()

        await self._address_section()
        address_time = self.timer.elapsed()

        await self._opening_section()
        opening_time = self.timer.elapsed()

        await self._body_section()
        body_time = self.timer.elapsed()

        await self._closing_section()
        closing_time = self.timer.elapsed()

        await self._signature()
        signature_time = self.timer.elapsed()

        await self._summarise_request()
        summarise_time = self.timer.elapsed()

        total_time = self.timer.stop()

        if self.verbose:
            print("\n--- Cover Letter generation Time ---\n")
            print(f"Acknowledgment Time: {acknowledgment_time:.2f} seconds")
            print(f"Research Time: {research_time:.2f} seconds")
            print(f"Header Time: {header_time:.2f} seconds")
            print(f"Address Time: {address_time:.2f} seconds")
            print(f"Opening Time: {opening_time:.2f} seconds")
            print(f"Body Time: {body_time:.2f} seconds")
            print(f"Closing Time: {closing_time:.2f} seconds")
            print(f"Signature Time: {signature_time:.2f} seconds")
            print(f"Summarise Time: {summarise_time:.2f} seconds")
            print(f"Total Time: {total_time:.2f} seconds")

        return {
            "letter": self.letter.strip(),
            "response": self.acknowledgment.strip() + self.summary.strip(),
            "title": self.title.strip()
        }