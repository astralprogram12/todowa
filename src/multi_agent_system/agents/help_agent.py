from .base_agent import BaseAgent
import database_personal as database
import os

class HelpAgent(BaseAgent):
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model, agent_name="HelpAgent")
        self.agent_type = "help"
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
                'core_system': self._build_help_system_prompt(prompts_dict)
            }
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}
    
    def _build_help_system_prompt(self, prompts_dict):
        """Builds the system prompt for the Help agent."""
        core_identity = prompts_dict.get('00_core_identity', 'You are a helpful support agent.')
        ai_interactions = prompts_dict.get('04_ai_interactions', '')
        return f"{core_identity}\n\n{ai_interactions}"

    async def process(self, user_input, context, routing_info=None):
        """
        Process help and support requests.
        routing_info contains assumptions and confidence from IntentClassifierAgent.
        """
        try:
            # Use routing_info assumptions if available
            assumptions = routing_info.get('assumptions', {}) if routing_info else {}
            
            # Load comprehensive prompts
            if not self.comprehensive_prompts:
                self.load_comprehensive_prompts()
            
            system_prompt = self.comprehensive_prompts.get('core_system', "You are a helpful support agent.")
            
            # Add routing info to context if available
            enhanced_context = context.copy()
            if routing_info:
                enhanced_context['routing_info'] = routing_info
                enhanced_context['intent_assumptions'] = assumptions
            
            # Determine help type and provide appropriate assistance
            user_prompt = f"""
User Input: {user_input}
Context: {enhanced_context}

This is a help request. Provide clear, actionable help information.
"""

            # FIXED: Remove await from synchronous AI call
            response = self.ai_model.generate_content([system_prompt, user_prompt])
            response_text = response.text
            
            # Determine help category and provide structured assistance
            help_category = assumptions.get('help_category', 'general')
            
            # Log the help request
            user_id = context.get('user_id')
            if user_id:
                # FIXED: Use approved action_type and entity_type for database constraints
                database.log_action(
                    supabase=self.supabase,
                    user_id=user_id,
                    action_type="chat_interaction",  # Use approved database action_type
                    entity_type="system",           # Use approved database entity_type
                    action_details={
                        "help_category": help_category,
                        "feature": assumptions.get('feature'),
                        "problem_type": assumptions.get('problem_type')
                    },
                    success_status=True
                )
            
            # CRITICAL: Always return a message
            return {
                "message": response_text,
                "actions": ["help_provided"],
                "data": {
                    "help_category": help_category,
                    "feature": assumptions.get('feature'),
                    "problem_type": assumptions.get('problem_type')
                }
            }
            
        except Exception as e:
            # CRITICAL: Always return a message, never empty dict
            return {
                "message": "I'm here to help! Please let me know what specific assistance you need and I'll do my best to guide you.",
                "actions": ["help_error"],
                "error": str(e)
            }
