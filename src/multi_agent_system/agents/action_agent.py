from .base_agent import BaseAgent
import database_personal as database
import os

class ActionAgent(BaseAgent):
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model, agent_name="ActionAgent")
        self.agent_type = "action"
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
                'core_system': self._build_action_system_prompt(prompts_dict)
            }
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}
    
    def _build_action_system_prompt(self, prompts_dict):
        """Builds the system prompt for the Action agent."""
        core_identity = prompts_dict.get('00_core_identity', 'You are a helpful action manager.')
        action_schema = prompts_dict.get('01_action_schema', '')
        return f"{core_identity}\n\n{action_schema}"

    async def process(self, user_input, context, routing_info=None):
        """
        Process action requests with comprehensive prompt system.
        routing_info contains assumptions and confidence from IntentClassifierAgent.
        """
        try:
            # Load comprehensive prompts
            if not self.comprehensive_prompts:
                self.load_comprehensive_prompts()
            
            # Use routing_info assumptions if available
            assumptions = routing_info.get('assumptions', {}) if routing_info else {}
            
            # Add routing info to context if available
            enhanced_context = context.copy()
            if routing_info:
                enhanced_context['routing_info'] = routing_info
                enhanced_context['intent_assumptions'] = assumptions
            
            # Use comprehensive prompt system
            return await self._process_with_comprehensive_prompts(user_input, enhanced_context, routing_info)
            
        except Exception as e:
            # CRITICAL: Always return a message, never empty dict
            return {
                "message": f"I encountered an error while trying to perform that action: {str(e)}",
                "actions": ["action_error"],
                "error": str(e)
            }
    
    async def _process_with_comprehensive_prompts(self, user_input, context, routing_info):
        """Process action with comprehensive prompt system."""
        assumptions = routing_info.get('assumptions', {}) if routing_info else {}
        
        # Build comprehensive prompt using all relevant prompts
        system_prompt = self.comprehensive_prompts.get('core_system', 'You are a helpful action management agent.')
        
        user_prompt = f"""
User Input: {user_input}
Context: {context}
Routing Info: {routing_info}

Process this action request following all prompt guidelines.
"""
        
        # FIXED: Remove await from synchronous AI call
        response = self.ai_model.generate_content([system_prompt, user_prompt])
        response_text = response.text
        
        # Log the action
        user_id = context.get('user_id')
        if user_id:
            # FIXED: Use approved action_type and entity_type for database constraints
            database.log_action(
                supabase=self.supabase,
                user_id=user_id,
                action_type="schedule_ai_action",  # Use approved database action_type
                entity_type="ai_action",          # Use approved database entity_type
                action_details={
                    "action_type": assumptions.get('action_type', 'general'),
                    "comprehensive_prompts_used": True
                },
                success_status=True
            )
        
        # CRITICAL: Always return a message
        return {
            "message": response_text,
            "actions": ["action_processed"],
            "data": {
                "action_type": assumptions.get('action_type', 'general')
            }
        }
