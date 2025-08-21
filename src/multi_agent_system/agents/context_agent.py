from .base_agent import BaseAgent
import database_personal as database
import os

class ContextAgent(BaseAgent):
    """Agent for context management without technical leaks."""
    
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model, agent_name="ContextAgent")
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
                'core_system': self._build_context_system_prompt(prompts_dict)
            }
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}
    
    def _build_context_system_prompt(self, prompts_dict):
        core_identity = prompts_dict.get('00_core_identity', 'You are a helpful assistant with good memory.')
        context_memory = prompts_dict.get('03_context_memory', '')
        leak_prevention = """
        
CRITICAL: Help with memory and context naturally. Never include:
- System details, technical information, or internal processes
- JSON, debugging info, or technical formatting
- References to agents, databases, or system architecture

Respond like an assistant with excellent memory for past conversations.
        """
        return f"{core_identity}\n\n{context_memory}{leak_prevention}"

    async def process(self, user_input, context, routing_info=None):
        try:
            if not self.comprehensive_prompts:
                self.load_comprehensive_prompts()
            
            system_prompt = self.comprehensive_prompts.get('core_system', 'You are a helpful assistant with good memory.')
            
            user_prompt = f"""
User is asking about past context or wants to reference previous conversations: {user_input}

Help them by recalling relevant information or acknowledging the context.
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
                    action_type="chat_interaction",
                    entity_type="system",
                    action_details={"type": "context_management"},
                    success_status=True
                )
            
            # Return ONLY clean user message
            return {
                "message": clean_message
            }
            
        except Exception as e:
            print(f"ERROR in ContextAgent: {e}")
            return {
                "message": "I'm here to help! I try to remember our conversations to assist you better. What can I help you with?"
            }
