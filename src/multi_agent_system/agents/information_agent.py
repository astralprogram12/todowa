from .base_agent import BaseAgent
import database_personal as database
import os

class InformationAgent(BaseAgent):
    """Agent for providing information without leaking technical details."""
    
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model, agent_name="InformationAgent")
        self.comprehensive_prompts = {}

    def load_comprehensive_prompts(self):
        try:
            prompts_dict = {}
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
            v1_dir = os.path.join(project_root, "prompts", "v1")
            
            if os.path.exists(v1_dir):
                for file_name in os.listdir(v1_dir):
                    if file_name.endswith('.md'):
                        prompt_name = file_name.replace('.md', '')
                        file_path = os.path.join(v1_dir, file_name)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            prompts_dict[prompt_name] = f.read()

            self.comprehensive_prompts = {
                'core_system': self._build_information_system_prompt(prompts_dict)
            }
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}
    
    def _build_information_system_prompt(self, prompts_dict):
        core_identity = prompts_dict.get('00_core_identity', 'You are a helpful information assistant.')
        information_specialized = prompts_dict.get('14_information_specialized', '')
        leak_prevention = """
        
CRITICAL: Respond only with helpful, natural information. Never include:
- Technical details, system info, or internal processes
- JSON, code blocks, or technical formatting
- References to agents, databases, or system architecture

Be conversational and informative like a knowledgeable friend.
        """
        return f"{core_identity}\n\n{information_specialized}{leak_prevention}"

    async def process(self, user_input: str, context: dict, routing_info: dict) -> dict:
        try:
            if not self.comprehensive_prompts:
                self.load_comprehensive_prompts()
            
            assumptions = routing_info.get('assumptions', {}) if routing_info else {}
            system_prompt = self.comprehensive_prompts.get('core_system', "You are a helpful information assistant.")
            
            user_prompt = f"""
User asked: {user_input}

Provide a helpful, informative response. Be natural and conversational.
Do not include any technical details or system information.
"""
            
            # Make AI call (synchronous)
            response = self.ai_model.generate_content([system_prompt, user_prompt])
            response_text = response.text
            
            # Clean the response to prevent leaks
            clean_message = self._clean_response(response_text)
            
            # Log action (internal only)
            user_id = context.get('user_id')
            if user_id:
                self._log_action(
                    user_id=user_id,
                    action_type="add_journal",
                    entity_type="journal",
                    action_details={"type": "information_request"},
                    success_status=True
                )
            
            # Return ONLY clean user message - no technical details
            return {
                "message": clean_message
            }
            
        except Exception as e:
            print(f"ERROR in InformationAgent: {e}")
            return {
                "message": "I'm having trouble finding that information right now. Could you try rephrasing your question?"
            }
