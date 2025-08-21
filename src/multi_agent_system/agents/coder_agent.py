from .base_agent import BaseAgent
import database_personal as database  # Step 1: Fix the imports
import os

class CoderAgent(BaseAgent):
    def __init__(self, supabase, ai_model):  # Step 2: Fix constructor
        super().__init__(supabase, ai_model, agent_name="CoderAgent")
        self.agent_type = "coder"
        self.comprehensive_prompts = {}

    def load_comprehensive_prompts(self):  # Step 3: Fix prompt loading logic
        """Loads all prompts relative to the project's structure."""
        try:
            prompts_dict = {}
            # This code correctly finds your prompts folder
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

            # This part can be customized for each agent
            self.comprehensive_prompts = {
                'core_system': self._build_coder_system_prompt(prompts_dict)
            }
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}
    
    def _build_coder_system_prompt(self, prompts_dict):  # Customize this helper for each agent
        """Builds the system prompt for the Coder agent."""
        core_identity = prompts_dict.get('00_core_identity', 'You are a helpful coding assistant.')
        ai_interactions = prompts_dict.get('04_ai_interactions', '')
        return f"{core_identity}\n\n{ai_interactions}"

    async def process(self, user_input, context, routing_info=None):
        """Process coding and development requests."""
        try:
            # Load comprehensive prompts
            if not self.comprehensive_prompts:
                self.load_comprehensive_prompts()  # NO 'await' here
            
            assumptions = routing_info.get('assumptions', {}) if routing_info else {}
            
            system_prompt = self.comprehensive_prompts.get('core_system', "You are a helpful coding assistant.")
            
            user_prompt = f"""
User Input: {user_input}
Context: {context}
Routing Info: {routing_info}

Process this coding request following all prompt guidelines.
"""
            
            # Step 4: Fix AI model call with await
            response = await self.ai_model.generate_content([system_prompt, user_prompt])
            response_text = response.text
            
            # Log the coding action
            user_id = context.get('user_id')
            if user_id:
                # Step 5: Fix database calls
                database.log_action(
                    supabase=self.supabase,
                    user_id=user_id,
                    action_type="coding_processed",
                    entity_type="coding",
                    action_details={
                        "coding_type": assumptions.get('coding_type', 'general')
                    },
                    success_status=True
                )
            
            return {
                "message": response_text,
                "actions": ["coding_processed"]
            }
            
        except Exception as e:
            return {
                "message": "I encountered an error while processing the coding request.",
                "actions": ["coding_error"],
                "error": str(e)
            }
