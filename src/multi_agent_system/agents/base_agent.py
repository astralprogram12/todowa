# base_agent.py
# Updated Base Agent class that all specialized agents inherit from

import os

# --- [THE FIX] ---
# The import path now correctly points to the file named 'enhanced_agent_tools_mixin.py'
from src.multi_agent_system.enhanced_agent_tools_mixin import AgentToolsMixin
# --- End of Fix ---

class BaseAgent(AgentToolsMixin):
    """Base agent class with common functionality for all agents."""

    def __init__(self, supabase, ai_model, agent_name=None):
        """Initialize the base agent with required dependencies."""
        super().__init__()  # Initialize the AgentToolsMixin
        self.supabase = supabase
        self.ai_model = ai_model
        self.agent_name = agent_name or self.__class__.__name__
        self.context = {}
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
                        print(f"Loaded prompt: {prompt_name}")
            
            return self.prompts
        except Exception as e:
            print(f"Error loading prompts: {e}")
            return {}
    
    async def process(self, user_input, context, routing_info=None):
        """Process user input and return a response."""
        raise NotImplementedError("Subclasses must implement this method")
    
    def _apply_ai_assumptions(self, context, routing_info):
        """Apply AI assumptions to enhance processing context."""
        if not routing_info or not routing_info.get('assumptions'):
            return context
        
        enhanced_context = context.copy()
        enhanced_context.update({
            'ai_assumptions': routing_info['assumptions'],
            'ai_confidence': routing_info.get('confidence', 0.6),
            'ai_reasoning': routing_info.get('reasoning', '')
        })
        
        print(f"[{self.agent_name}] Applying AI assumptions: {routing_info['assumptions']}")
        return enhanced_context
    
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
    
    async def _get_user_timezone(self, user_id):
        """Get the user's timezone from their preferences."""
        try:
            tool_result = await self.use_tool("get_user_memory", user_id=user_id, key="timezone")
            
            if tool_result['status'] == 'success' and tool_result['result']:
                return tool_result['result']
            
            preferences = self.supabase.table("user_preferences").select("*").eq("user_id", user_id).execute()
            if preferences.data:
                return preferences.data[0].get("timezone", "UTC")
            
            return "UTC"
        except Exception as e:
            print(f"!!! ERROR GETTING USER TIMEZONE: {e}")
            return "UTC"
    
    async def convert_utc_to_user_timezone(self, user_id, utc_time_str):
        """Convert a UTC time string to the user's local timezone."""
        try:
            tool_result = await self.use_tool(
                "convert_utc_to_user_timezone", supabase=self.supabase,
                user_id=user_id, utc_time_str=utc_time_str
            )
            
            if tool_result['status'] == 'success':
                return tool_result['result']
            else:
                return utc_time_str
        except Exception as e:
            print(f"!!! TIME CONVERSION ERROR: {e}")
            return utc_time_str
    
    def ai_confusion_helper(self, user_id, content_description, user_input=None, context_hint=None):
        """Generate a helpful response when the AI is confused."""
        if user_input:
            return f"I'll help you with '{user_input}'. Let me assist you with that."
        return f"I'll help you with that. {content_description}"
    
    async def get_tool_suggestions(self, user_input):
        """Get tool suggestions based on user input."""
        return self.suggest_tools(user_input)
    
    async def execute_tools_chain(self, tools_chain, context):
        """Execute a chain of tools in sequence."""
        results = []
        
        for tool_spec in tools_chain:
            tool_name = tool_spec.get('name')
            tool_params = tool_spec.get('params', {})
            
            if 'user_id' in tool_params and not tool_params['user_id'] and 'user_id' in context:
                tool_params['user_id'] = context['user_id']
            
            tool_result = await self.use_tool(tool_name, **tool_params)
            results.append(tool_result)
            
            if tool_result['status'] == 'error':
                break
        
        return results