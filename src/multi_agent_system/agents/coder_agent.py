from .base_agent import BaseAgent
import database_personal as database
import os

class CoderAgent(BaseAgent):
    """Agent for coding assistance without technical leaks."""
    
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model, agent_name="CoderAgent")
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
                'core_system': self._build_coder_system_prompt(prompts_dict)
            }
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}
    
    def _build_coder_system_prompt(self, prompts_dict):
        core_identity = prompts_dict.get('00_core_identity', 'You are a helpful coding assistant.')
        coder_specialized = prompts_dict.get('10_coder_specialized', '')
        leak_prevention = """
        
CRITICAL: Provide coding help naturally. Never include:
- System details, technical information about internal processes
- JSON, debugging info, or internal technical formatting
- References to agents, databases, or system architecture

Respond like a helpful programming mentor. Code examples are fine, but no system internals.
        """
        return f"{core_identity}\n\n{coder_specialized}{leak_prevention}"

    async def process(self, user_input, context, routing_info=None):
        try:
            if not self.comprehensive_prompts:
                self.load_comprehensive_prompts()
            
            system_prompt = self.comprehensive_prompts.get('core_system', 'You are a helpful coding assistant.')
            
            user_prompt = f"""
User needs coding help: {user_input}

Provide helpful programming assistance. Use code examples when helpful.
Do not include any system internals or technical architecture details.
"""
            
            # Make AI call (synchronous)
            response = self.ai_model.generate_content([system_prompt, user_prompt])
            response_text = response.text
            
            # For coding, we want to preserve code blocks but remove system details
            # Don't over-clean code examples
            clean_message = self._clean_response(response_text)
            
            if not clean_message.strip():
                clean_message = "I'd be happy to help with your coding question! Could you provide more details about what you're working on?"
            
            # Log action (internal only)
            user_id = context.get('user_id')
            if user_id:
                self._log_action(
                    user_id=user_id,
                    action_type="chat_interaction",
                    entity_type="system",
                    action_details={"type": "coding_assistance"},
                    success_status=True
                )
            
            # Return ONLY clean user message
            return {
                "message": clean_message
            }
            
        except Exception as e:
            print(f"ERROR in CoderAgent: {e}")
            return {
                "message": "I'd be happy to help with your coding question! What programming challenge are you working on?"
            }
