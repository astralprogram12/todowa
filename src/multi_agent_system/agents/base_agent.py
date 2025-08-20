# base_agent.py
# Final version, using ONLY the enhanced tool system.

import os

# --- [THE FIX] ---
# Import the correct mixin from the correct file in the root directory.
from enhanced_agent_tools_mixin import EnhancedAgentToolsMixin
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
        
        # Initialize the tools with the necessary context as soon as the agent is created.
        if supabase and hasattr(self, 'user_id'): # user_id will be set by context
            self.initialize_tools(supabase, self.user_id)

    # --- This method is now handled by the mixin, so we can simplify/remove it ---
    # async def use_tool(...): is replaced by self.execute_tool(...) from the mixin
    
    def load_prompts(self, prompts_dir):
        """Load prompt files from the specified directory."""
        # ... (this function can remain the same)
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
        # --- [THE FIX] Update context before processing ---
        # Set the user_id for the tool context for THIS specific request.
        self.user_id = context.get('user_id')
        self.initialize_tools(self.supabase, self.user_id)
        # --- [END OF FIX] ---
        raise NotImplementedError("Subclasses must implement this method")
    
    def _log_action(self, user_id, action_type, entity_type, entity_id=None, 
                   action_details=None, success_status=True, error_details=None):
        """Log an action performed by the agent."""
        try:
            from database_personal import log_action
            log_action(
                supabase=self.supabase, user_id=user_id, action_type=action_type,
                entity_type=entity_type, entity_id=entity_id, action_details=action_details or {},
                success_status=success_status, error_details=error_details
            )
        except Exception as e:
            print(f"!!! AGENT LOGGING ERROR: {e}")

    # ... other helper methods in your base agent can remain ...