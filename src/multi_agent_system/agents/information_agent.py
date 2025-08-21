from .base_agent import BaseAgent
import database_personal as database
import json
import os

class InformationAgent(BaseAgent):
    """
    Agent responsible for providing factual information and storing new knowledge.
    """
    
    def __init__(self, supabase, ai_model):
        """Initializes the InformationAgent with correct parameters."""
        super().__init__(supabase, ai_model, agent_name="InformationAgent")
        self.comprehensive_prompts = {}

    def load_comprehensive_prompts(self):
        """Loads all prompts relative to the project's structure."""
        try:
            prompts_dict = {}
            # Use relative pathing to avoid hardcoded paths
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
            v1_dir = os.path.join(project_root, "prompts", "v1")
            
            if os.path.exists(v1_dir):
                for file_name in os.listdir(v1_dir):
                    if file_name.endswith('.md'):
                        prompt_name = file_name.replace('.md', '')
                        file_path = os.path.join(v1_dir, file_name)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            prompts_dict[prompt_name] = f.read()
            else:
                print(f"WARNING: Prompts directory not found at {v1_dir}")

            self.comprehensive_prompts = {
                'core_system': self._build_information_system_prompt(prompts_dict)
            }
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}
    
    def _build_information_system_prompt(self, prompts_dict):
        """Builds the system prompt for the Information agent."""
        core_identity = prompts_dict.get('00_core_identity', 'You are a helpful information provider.')
        ai_interactions = prompts_dict.get('04_ai_interactions', '')
        return f"{core_identity}\n\n{ai_interactions}"

    async def process(self, user_input: str, context: dict, routing_info: dict) -> dict:
        """
        Processes a user's request for information, generates a response,
        and stores the new knowledge in the user's journal.
        """
        try:
            assumptions = routing_info.get('assumptions', {}) if routing_info else {}
            
            # Load comprehensive prompts
            if not self.comprehensive_prompts:
                self.load_comprehensive_prompts()
            
            system_prompt = self.comprehensive_prompts.get('core_system', "You are a helpful information agent.")
            
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
            
            # FIXED: Remove await from synchronous AI call
            response = self.ai_model.generate_content([system_prompt, user_prompt])
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
            # CRITICAL: Always return a message, never empty dict
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
                # FIXED: Use approved action_type and entity_type for database constraints
                database.log_action(
                    supabase=self.supabase,
                    user_id=user_id,
                    action_type="add_journal",  # Use approved database action_type
                    entity_type="journal",     # Use approved database entity_type
                    action_details={
                        "question": user_input,
                        "response": response[:500]  # Truncate for storage
                    },
                    success_status=True
                )
        except Exception as e:
            print(f"Error storing information exchange: {e}")
