import logging
import json
from typing import Dict, Any, Optional

# The agent directly uses the tools and database manager
from database import DatabaseManager
from ai_tools import internet_search

logger = logging.getLogger(__name__)

class GeneralFallbackAgent:
    """
    An expert reasoning agent that handles complex queries using a two-step
    "research and synthesize" process. It models a sophisticated cognitive workflow
    to access personal data and the live internet, providing insightful,
    evidence-based answers.
    """
    def __init__(self, ai_model=None, supabase=None):
        self.ai_model = ai_model
        self.supabase = supabase

    # --- API CALL 1: EXPERT TRIAGE & PLANNING ---
    def _determine_data_needs(self, user_command: str) -> Dict[str, Any]:
        """
        Analyzes the user's command to create a sophisticated data-gathering plan.
        Adopts the persona of a Cognitive Triage Specialist.
        """
        prompt = f"""
        You are a Cognitive Triage Specialist. Your function is to analyze a user's request with deep understanding and create an optimal plan for gathering the information needed to provide a comprehensive answer.

        ### Guiding Principles:
        1.  **User-Centricity:** Your primary goal is to understand the *underlying intent* of the user's question, not just the literal words. What do they truly want to know?
        2.  **Information Hierarchy:** Personal data provides intimate context about the user's life. Web data provides factual, external context. Prioritize `personal_data` for questions about the user, and `web_search` for questions about the world. Use both for hybrid questions.
        3.  **Efficiency:** Do not call a tool if the answer can be derived from general knowledge (e.g., "hello", "thank you", "write a poem").

        ### Information Sources (Your Toolbox):
        1.  `personal_data`: Accesses the user's recent tasks and journal entries.
            - **Use Case:** Questions about productivity, personal feelings, summaries of their recent life, or requests for personalized advice.
            - **Example Triggers:** "What should I focus on?", "How have I been feeling?", "Summarize my work on the 'Q3 Report'."

        2.  `internet_search`:  
            - **Description**: Searches the live internet for real-time or external information.
            - **Use When**: The user asks about current events, news, facts about the world, or any topic requiring up-to-the-minute information.
            - **Example Triggers**: "Who won the F1 race yesterday?", "What are the reviews for the new Acme phone?", "What is the capital of Tanzania?"

        ### User Command Analysis:
        Analyze the following command. Based on your principles, create a plan. If you need to search the web, formulate an expert-level search query that rephrases the user's question into keywords a search engine will understand best.

        **User Command:** "{user_command}"

        ### Your Plan (JSON Output Only):
        Respond ONLY with a valid JSON object in the following format.
        {{
          "thought": "Your concise, step-by-step reasoning for the chosen plan. Explain WHY you selected the tools.",
          "data_needed": ["personal_data" | "web_search" | ...],
          "search_query": "Your expertly crafted search query, or null if not needed."
        }}
        """
        try:
            response = self.ai_model.generate_content(prompt)
            response_text = response.text.strip().replace('```json', '').replace('```', '')
            return json.loads(response_text)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Fallback Triage Parse Error: {e}. Defaulting to a direct answer.")
            return {"thought": "Triage model failed to parse. I will attempt a direct answer from my own knowledge.", "data_needed": [], "search_query": None}

    # --- API CALL 2: EXPERT SYNTHESIS & ANSWERING ---
    def _synthesize_answer(self, user_command: str, personal_data: Dict, web_results: Dict) -> str:
        """
        Takes all gathered information and synthesizes it into a final, expert-level response.
        """
        prompt = f"""
        You are an Expert Knowledge Synthesizer. Your role is to transform raw data into a clear, insightful, and helpful answer for the user.

        ### The Golden Rule of Synthesis:
        **Answer the user's original question directly. Use the provided research as *evidence* to support your answer, not as a summary of the research itself.** The user wants an answer, not a book report.

        ### Methodology for Your Response:
        1.  **Re-read the Core Question:** Begin by deeply understanding the user's original command.
        2.  **Review All Evidence:** Scrutinize the `personal_data` and `web_results`. Identify the most relevant pieces of information.
        3.  **Prioritize Personal Context:** If personal data is available, use it to frame the answer. This makes your response feel personal and relevant.
        4.  **Integrate External Facts:** Weave in facts from the web results to provide objective, up-to-date information.
        5.  **Handle Conflicts & Gaps:** If the data is contradictory or incomplete, acknowledge it. For example, "One source suggests X, while another suggests Y," or "I couldn't find specific information on Z."
        6.  **Cite Your Sources:** For any fact taken from the web, you MUST include the source link in parentheses at the end of the sentence, like this: (https://example.com/article).
        7.  **Adopt an Expert Persona:** Your tone should be helpful, confident, and clear. You are not just a machine reporting data; you are an insightful assistant providing a synthesized conclusion.

        ---
        ### **User's Original Command:**
        "{user_command}"

        ### **Collected Research Evidence:**

        **1. User's Personal Data (Recent Tasks & Journals):**
        {json.dumps(personal_data, indent=2, default=str)}

        **2. Web Search Results:**
        {json.dumps(web_results, indent=2, default=str)}
        ---

        Now, following all rules and your expert methodology, formulate the final, comprehensive response for the user.
        """
        try:
            response = self.ai_model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Fallback Synthesis Error: {e}")
            return "I successfully gathered the information, but encountered an issue while synthesizing the final answer. Please try rephrasing your question."

    # --- MAIN ORCHESTRATOR ---
    def process_command(self, user_command: str, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Orchestrates the internal "Triage -> Fetch -> Synthesize" workflow.
        """
        if not self.ai_model or not self.supabase:
            return {"success": False, "actions": [], "response": "Fallback Agent is not properly configured."}

        # 1. API Call 1: Triage and create a plan
        plan = self._determine_data_needs(user_command)
        logger.info(f"GeneralFallbackAgent Plan: {plan.get('thought')}")
        
        data_needed = plan.get("data_needed", [])
        personal_data = {}
        web_results = {}

        # 2. Internal Action: Fetch data based on the plan
        user_id = user_context.get('user_info', {}).get('user_id')
        if user_id:
            if "personal_data" in data_needed:
                logger.info("Fetching personal data...")
                db_manager = DatabaseManager(self.supabase, user_id)
                personal_data = db_manager.get_recent_tasks_and_journals()

            if "web_search" in data_needed and plan.get("search_query"):
                search_query = plan["search_query"]
                logger.info(f"Performing expert web search for: '{search_query}'")
                web_results = internet_search(search_query)
        else:
            logger.warning("No user_id found; cannot fetch personal data.")

        # 3. API Call 2: Synthesize the final answer
        final_answer = self._synthesize_answer(user_command, personal_data, web_results)

        # Return the final, complete response. The "actions" list is always empty
        # because this agent performs its own actions internally.
        return {
            "success": True,
            "actions": [],
            "response": final_answer
        }