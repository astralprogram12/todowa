# Updated Base Agent class that all specialized agents inherit from
# Now integrates the tools system via the AgentToolsMixin

import os
from ..agent_tools_mixin import AgentToolsMixin

class BaseAgent(AgentToolsMixin):
    """Base agent class with common functionality for all agents."""

    def __init__(self, supabase, ai_model, agent_name=None):
        """Initialize the base agent with required dependencies.
        
        Args:
            supabase: The Supabase client for database operations
            ai_model: The AI model for natural language processing
            agent_name: Optional name for the agent
        """
        super().__init__()  # Initialize the AgentToolsMixin
        self.supabase = supabase
        self.ai_model = ai_model
        self.agent_name = agent_name or self.__class__.__name__
        self.context = {}
        self.prompts = {}
    
    def load_prompts(self, prompts_dir):
        """Load prompt files from the specified directory.
        
        Args:
            prompts_dir: The directory containing prompt files
        
        Returns:
            A dictionary of prompt content keyed by prompt name
        """
        try:
            print(f"Loading prompts for {self.agent_name}")
            v1_dir = os.path.join(prompts_dir, 'v1')
            if not os.path.exists(v1_dir):
                print(f"Warning: v1 prompt directory not found at {v1_dir}")
                return {}
            
            # Load all prompt files in the v1 directory
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
    
    async def process(self, user_input, context):
        """Process user input and return a response.
        
        Args:
            user_input: The input text from the user
            context: The context of the conversation
            
        Returns:
            A response to the user input
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def _log_action(self, user_id, action_type, entity_type, entity_id=None, 
                   action_details=None, success_status=True, error_details=None):
        """Log an action performed by the agent.
        
        Args:
            user_id: The ID of the user who initiated the action
            action_type: The type of action performed
            entity_type: The type of entity the action was performed on
            entity_id: The ID of the entity the action was performed on
            action_details: Additional details about the action
            success_status: Whether the action was successful
            error_details: Details about any errors that occurred
        """
        try:
            from database_personal import log_action
            
            log_action(
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
            # Don't let logging errors break the main functionality
            print(f"!!! AGENT LOGGING ERROR: {e}")
    
    async def _get_user_timezone(self, user_id):
        """Get the user's timezone from their preferences.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            The user's timezone (e.g., 'America/New_York') or UTC as default
        """
        try:
            # Use the time_tools via the tools system
            tool_result = await self.use_tool(
                "get_user_memory",
                user_id=user_id,
                key="timezone"
            )
            
            if tool_result['status'] == 'success' and tool_result['result']:
                return tool_result['result']
            
            # Fall back to preferences table if memory doesn't have timezone
            preferences = self.supabase.table("user_preferences").select("*").eq("user_id", user_id).execute()
            if preferences.data:
                return preferences.data[0].get("timezone", "UTC")
            
            return "UTC"  # Default timezone
        except Exception as e:
            print(f"!!! ERROR GETTING USER TIMEZONE: {e}")
            return "UTC"  # Fallback to UTC
    
    async def convert_utc_to_user_timezone(self, user_id, utc_time_str):
        """Convert a UTC time string to the user's local timezone.
        
        Args:
            user_id: The ID of the user
            utc_time_str: The UTC time string to convert
            
        Returns:
            The time string in the user's local timezone
        """
        try:
            # Use the time_tools via the tools system
            tool_result = await self.use_tool(
                "convert_utc_to_user_timezone",
                supabase=self.supabase,
                user_id=user_id,
                utc_time_str=utc_time_str
            )
            
            if tool_result['status'] == 'success':
                return tool_result['result']
            else:
                return utc_time_str  # Return the original string if conversion fails
        except Exception as e:
            print(f"!!! TIME CONVERSION ERROR: {e}")
            return utc_time_str  # Return the original string if conversion fails
    
    def ai_confusion_helper(self, user_id, content_description, user_input=None, context_hint=None):
        """Generate a helpful response when the AI is confused about user input.
        
        Args:
            user_id: The ID of the user
            content_description: Description of what the AI is confused about
            user_input: The original user input that caused confusion
            context_hint: Hint about the context of the conversation
            
        Returns:
            A helpful response to guide the user
        """
        # TODO: Implement advanced confusion handling logic
        # For now, return a simple response
        if user_input:
            return f"I'm not sure I understand what you mean by '{user_input}'. {content_description}"
        return f"I'm having trouble understanding. {content_description}"
    
    async def get_tool_suggestions(self, user_input):
        """Get tool suggestions based on user input.
        
        Args:
            user_input: The user input to analyze
            
        Returns:
            List of suggested tools
        """
        return self.suggest_tools(user_input)
    
    async def execute_tools_chain(self, tools_chain, context):
        """Execute a chain of tools in sequence.
        
        Args:
            tools_chain: List of tool specs, each containing name and params
            context: The context of the conversation
            
        Returns:
            Results of the tools chain execution
        """
        results = []
        
        for tool_spec in tools_chain:
            tool_name = tool_spec.get('name')
            tool_params = tool_spec.get('params', {})
            
            # Add context parameters if needed
            if 'user_id' in tool_params and not tool_params['user_id'] and 'user_id' in context:
                tool_params['user_id'] = context['user_id']
            
            # Execute the tool
            tool_result = await self.use_tool(tool_name, **tool_params)
            results.append(tool_result)
            
            # If a tool fails, stop the chain
            if tool_result['status'] == 'error':
                break
        
        return results
