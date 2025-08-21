# base_agent.py
# Final version with correct import path and class name.

import os

# --- [THE FIX] ---
# Import the 'EnhancedAgentToolsMixin' class from its correct location
# inside the 'src/multi_agent_system' package.
from src.multi_agent_system.enhanced_agent_tools_mixin import EnhancedAgentToolsMixin
# --- End of Fix ---

class BaseAgent(EnhancedAgentToolsMixin):
    """Base agent class using the ENHANCED tool system."""

    def __init__(self, supabase, ai_model, agent_name=None):
        """Initialize the base agent."""
        super().__init__()  # Initialize the EnhancedAgentToolsMixin
        self.supabase = supabase
        self.ai_model = ai_model
        self.agent_name = agent_name or self.__class__.__name__
        self.prompts = {}
        
    def load_prompts(self, prompts_dir):
        """Load prompt files from the specified directory."""
        try:
            print(f"Loading prompts for {self.agent_name}")
            v1_dir = os.path.join(prompts_dir, 'v1')
            if not os.path.exists(v1_dir):
                print(f"Warning: v1 prompt directory not found at {v1_dir}")
                return {}
            
            for file_name in os.listdir(v1_dir):
                if file_name.endswith('.md'):
                    prompt_name = file_name.replace('.md', '')
                    file_path = os.path.join(v1_dir, file_name)
                    with open(file_path, 'r') as f:
                        self.prompts[prompt_name] = f.read()
            
            return self.prompts
        except Exception as e:
            print(f"Error loading prompts: {e}")
            return {}
            
    async def process(self, user_input, context, routing_info=None):
        """Process user input and return a response."""
        # Set the tool context for this specific request.
        user_id = context.get('user_id')
        if user_id:
            self.initialize_tools(self.supabase, user_id)
        
        raise NotImplementedError("Subclasses must implement this method")
    
    def _log_action(self, user_id, action_type, entity_type, entity_id=None, 
                   action_details=None, success_status=True, error_details=None):
        """Log an action performed by the agent."""
        try:
            # --- [THE FIX] ---
            # Changed from 'database' back to the correct 'database_personal'
            from database_personal import log_action
            # --- [END OF FIX] ---
            
            log_action(
                supabase=self.supabase, user_id=user_id, action_type=action_type,
                entity_type=entity_type, entity_id=entity_id, action_details=action_details or {},
                success_status=success_status, error_details=error_details
            )
        except Exception as e:
            print(f"!!! AGENT LOGGING ERROR: {e}")
    # ... other helper methods in your base agent ...