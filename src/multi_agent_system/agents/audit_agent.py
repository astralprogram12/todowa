from .base_agent import BaseAgent
import database_personal as database
import os

class AuditAgent(BaseAgent):
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model, agent_name="AuditAgent")
        self.agent_type = "audit"
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
                'core_system': self._build_audit_system_prompt(prompts_dict)
            }
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}
    
    def _build_audit_system_prompt(self, prompts_dict):
        """Builds the system prompt for the Audit agent."""
        core_identity = prompts_dict.get('00_core_identity', 'You are a helpful audit agent.')
        safety_validation = prompts_dict.get('07_safety_validation', '')
        return f"{core_identity}\n\n{safety_validation}"

    async def process(self, user_input, context, routing_info=None):
        """Process audit and security requests."""
        try:
            # Load comprehensive prompts
            if not self.comprehensive_prompts:
                self.load_comprehensive_prompts()
            
            assumptions = routing_info.get('assumptions', {}) if routing_info else {}
            
            system_prompt = self.comprehensive_prompts.get('core_system', "You are a helpful audit agent.")
            
            user_prompt = f"""
User Input: {user_input}
Context: {context}
Routing Info: {routing_info}

Process this audit request following all prompt guidelines.
"""
            
            # FIXED: Remove await from synchronous AI call
            response = self.ai_model.generate_content([system_prompt, user_prompt])
            response_text = response.text
            
            # Log the audit action
            user_id = context.get('user_id')
            if user_id:
                # FIXED: Use approved action_type and entity_type for database constraints
                database.log_action(
                    supabase=self.supabase,
                    user_id=user_id,
                    action_type="chat_interaction",  # Use approved database action_type
                    entity_type="system",           # Use approved database entity_type
                    action_details={
                        "audit_type": assumptions.get('audit_type', 'general')
                    },
                    success_status=True
                )
            
            # CRITICAL: Always return a message
            return {
                "message": response_text,
                "actions": ["audit_processed"]
            }
            
        except Exception as e:
            # CRITICAL: Always return a message, never empty dict
            return {
                "message": "I encountered an error while processing the audit request. Please try again.",
                "actions": ["audit_error"],
                "error": str(e)
            }
