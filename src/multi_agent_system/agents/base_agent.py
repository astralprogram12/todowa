# base_agent.py
# Fixed version following the universal template

import database_personal as database  # Step 1: Fix the imports
import os

class BaseAgent:
    """Base agent class with correct architecture."""

    def __init__(self, supabase, ai_model, agent_name=None):  # Step 2: Fix constructor
        """Initialize the base agent with correct parameters."""
        self.supabase = supabase
        self.ai_model = ai_model
        self.agent_name = agent_name or self.__class__.__name__
        self.prompts = {}
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
                'core_system': self._build_base_system_prompt(prompts_dict)
            }
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}

    def _build_base_system_prompt(self, prompts_dict):  # Customize this helper for each agent
        """Builds the system prompt for the base agent."""
        core_identity = prompts_dict.get('00_core_identity', 'You are a helpful assistant.')
        return f"{core_identity}"
        
    async def process(self, user_input, context, routing_info=None):
        """Process user input and return a response."""
        raise NotImplementedError("Subclasses must implement this method")
    
    def _log_action(self, user_id, action_type, entity_type, entity_id=None, 
                   action_details=None, success_status=True, error_details=None):
        """Log an action performed by the agent."""
        try:
            # Step 5: Fix database calls
            database.log_action(
                supabase=self.supabase,
                user_id=user_id,
                action_type=action_type,
                entity_type=entity_type,
                entity_id=entity_id,
                action_details=action_details or {},
                success_status=success_status,
                error_details=error_details
            )
        except Exception as e:
            print(f"!!! AGENT LOGGING ERROR: {e}")
