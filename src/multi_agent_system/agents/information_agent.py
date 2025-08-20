# src/multi_agent_system/agents/information_agent.py (CORRECTED & FINAL)

from .base_agent import BaseAgent
import json
# Import the single, consolidated database_personal module
import database_personal

class InformationAgent(BaseAgent):
    """
    Agent responsible for providing factual information and storing new knowledge.
    """
    
    def __init__(self, supabase, ai_model):
        """Initializes the InformationAgent with correct parameters."""
        super().__init__(supabase, ai_model, agent_name="InformationAgent")

    async def process(self, user_input: str, context: dict, routing_info: dict) -> dict:
        """
        Processes a user's request for information, generates a response,
        and stores the new knowledge in the user's journal.
        """
        try:
            assumptions = routing_info.get('assumptions', {}) if routing_info else {}
            
            # load_prompts is synchronous and should not be awaited.
            # This part may be removed later as per the bug report's recommendation (P3 bug).
            system_prompt = self.load_prompts("prompts/v1") 
            
            enhanced_context = context.copy()
            if routing_info:
                enhanced_context['routing_info'] = routing_info
                enhanced_context['intent_assumptions'] = assumptions
            
            user_prompt = f"""
User Input: {user_input}
Context: {enhanced_context}
Provide a clear and accurate response to the user's information request based on the context and your general knowledge.
Incorporate these assumptions from the intent classifier: {assumptions}
"""
            # Use the correct AI model (self.ai_model) and method (generate_content)
            response = self.ai_model.generate_content(
                [system_prompt, user_prompt]
            )
            response_text = response.text

            # Determine if this new knowledge is valuable enough to store
            should_store = self._should_store_information(user_input)
            
            result = {
                "status": "success",
                "message": response_text,
                "actions": [{"agent": self.agent_name, "action": "information_provided"}]
            }
            
            if should_store:
                self._store_information_exchange(user_input, response_text, context)
                result["actions"].append({"action": "knowledge_stored_in_journal"})
            
            return result
            
        except Exception as e:
            print(f"!!! ERROR in InformationAgent process: {e}")
            return {
                "status": "error",
                "message": "I'm having trouble retrieving that information right now. Please try rephrasing your question.",
                "error": str(e)
            }

    def _should_store_information(self, user_input: str) -> bool:
        """Determine if this information exchange should be stored as knowledge."""
        # Simple heuristic: store questions that ask for explanations or definitions.
        store_keywords = ['how to', 'what is', 'what are', 'explain', 'definition', 'procedure']
        return any(keyword in user_input.lower() for keyword in store_keywords)

    def _store_information_exchange(self, user_input: str, response: str, context: dict):
        """
        Store the valuable question and answer in the JOURNALS table for future reference.
        """
        try:
            user_id = context.get('user_id')
            if not user_id:
                print("Cannot store information exchange, user_id not found in context.")
                return

            # Use the correct add_journal_entry function from the consolidated database_personal module.
            database_personal.add_journal_entry(
                supabase=self.supabase,
                user_id=user_id,
                title=f"Learned: {user_input[:60]}...", # Truncate for a clean title
                content=f"Q: {user_input}\nA: {response}", # Store the full Q&A in the content
                category="learned_knowledge"
            )
            print(f"Stored new knowledge in journal for user {user_id}")
        except Exception as e:
            # Log the error but don't crash the main agent flow
            print(f"!!! database_personal ERROR in _store_information_exchange: {e}")