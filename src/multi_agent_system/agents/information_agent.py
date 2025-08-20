from .base_agent import BaseAgent
import database_personal  # Fix #4: Proper database import
import json

class InformationAgent(BaseAgent):
    """
    Agent responsible for providing factual information and storing new knowledge.
    """
    
    def __init__(self, supabase, ai_model):  # Fix #1: Correct constructor
        """Initializes the InformationAgent with correct parameters."""
        super().__init__(supabase, ai_model, agent_name="InformationAgent")

    async def process(self, user_input: str, context: dict, routing_info: dict) -> dict:
        """
        Processes a user's request for information, generates a response,
        and stores the new knowledge in the user's journal.
        """
        try:
            assumptions = routing_info.get('assumptions', {}) if routing_info else {}
            
            # Fix #3: Load prompts synchronously (no await)
            prompts_dict = self.load_prompts("prompts")
            system_prompt = prompts_dict.get("00_core_identity", "You are a helpful information agent.")
            
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
            
            # Fix #2: Correct AI model call with array parameter
            response = await self.ai_model.generate_content([
                system_prompt, user_prompt
            ])
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
        # Simple heuristic: store if the request is substantial and specific
        return len(user_input.strip()) > 20 and any(word in user_input.lower() for word in 
            ['what is', 'explain', 'how does', 'tell me about', 'definition', 'meaning'])
    
    def _store_information_exchange(self, user_input: str, response: str, context: dict):
        """Store the information exchange in the user's journal."""
        try:
            user_id = context.get('user_id')
            if user_id:
                database_personal.log_action(
                    supabase=self.supabase,
                    user_id=user_id,
                    action_type="information_stored",
                    entity_type="knowledge",
                    action_details={
                        "question": user_input,
                        "response": response[:500]  # Truncate for storage
                    },
                    success_status=True
                )
        except Exception as e:
            print(f"Error storing information exchange: {e}")
