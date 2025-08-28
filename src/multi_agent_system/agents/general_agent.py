from .base_agent import BaseAgent
import database_personal as database
import os

class GeneralAgent(BaseAgent):
    """Agent for general conversation without technical leaks."""
    
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model, agent_name="GeneralAgent")
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
                'core_system': self._build_general_system_prompt(prompts_dict)
            }
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}
    
    def _build_general_system_prompt(self, prompts_dict):
        core_identity = prompts_dict.get('00_core_identity', 'You are a friendly, helpful assistant.')
        ai_interactions = prompts_dict.get('04_ai_interactions', '')
        general_specialized = prompts_dict.get('18_general_specialized', '')
        leak_prevention = """
        
CRITICAL: Be conversational and natural. Never include:
- System details, technical information, or internal processes
- JSON, debugging info, or technical formatting
- References to agents, databases, or system architecture

Respond like a helpful, knowledgeable friend in natural conversation.
        """
        return f"{core_identity}\n\n{ai_interactions}\n\n{general_specialized}{leak_prevention}"

    async def process(self, user_input, context, routing_info=None):
        try:
            if not self.comprehensive_prompts:
                self.load_comprehensive_prompts()
            
            system_prompt = self.comprehensive_prompts.get('core_system', 'You are a friendly, helpful assistant.')
            
            user_prompt = f"""
User said: {user_input}

Respond in a natural, conversational way. Be helpful and engaging.
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
                    action_details={"type": "general_conversation"},
                    success_status=True
                )
            
            # Return ONLY clean user message - no technical details
            return {
                "message": clean_message
            }
            
        except Exception as e:
            print(f"ERROR in GeneralAgent: {e}")
            return {
                "message": "I'm here to help! How can I assist you today?"
            }
