# agent_tools_mixin.py
# Mixin class to add tool capabilities to agents

import inspect
from typing import Dict, Any, List, Callable, Optional
from .tools import tool_registry

class AgentToolsMixin:
    """Mixin class that adds tool capabilities to agents."""
    
    def __init__(self):
        """Initialize the mixin."""
        self._tool_registry = tool_registry
    
    def get_available_tools(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get a list of available tools, optionally filtered by category.
        
        Args:
            category: Optional category to filter by
            
        Returns:
            List of tool information dictionaries
        """
        return self._tool_registry.list_tools(category)
    
    def get_tool_categories(self) -> List[str]:
        """Get a list of available tool categories.
        
        Returns:
            List of category names
        """
        return self._tool_registry.list_categories()
    
    async def use_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Use a tool by name with the provided parameters.
        
        Args:
            tool_name: The name of the tool
            **kwargs: Parameters to pass to the tool
            
        Returns:
            The result of the tool call
        """
        # Special handling for tools that require agent-specific parameters
        if 'supabase' not in kwargs and hasattr(self, 'supabase'):
            kwargs['supabase'] = self.supabase
        
        if 'ai_model' not in kwargs and hasattr(self, 'ai_model'):
            kwargs['ai_model'] = self.ai_model
        
        return await self._tool_registry.call_tool(tool_name, **kwargs)
    
    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """Get information about a specific tool.
        
        Args:
            tool_name: The name of the tool
            
        Returns:
            Tool information dictionary
        """
        try:
            tool = self._tool_registry.get_tool(tool_name)
            return {
                'name': tool_name,
                'category': tool['category'],
                'description': tool['description'],
                'required_params': tool['required_params'],
                'optional_params': tool['optional_params']
            }
        except KeyError:
            return {'error': f"Tool '{tool_name}' not found"}
    
    def suggest_tools(self, user_input: str, top_n: int = 3) -> List[Dict[str, Any]]:
        """Suggest tools based on user input.
        
        Args:
            user_input: The user input to analyze
            top_n: Number of tools to suggest
            
        Returns:
            List of suggested tool information dictionaries
        """
        # This is a simplified implementation
        # A real implementation would use more sophisticated matching
        user_input_lower = user_input.lower()
        
        # Get all tools
        all_tools = self._tool_registry.list_tools()
        
        # Calculate a simple relevance score for each tool
        scored_tools = []
        for tool in all_tools:
            score = 0
            
            # Check if tool name appears in input
            if tool['name'].lower() in user_input_lower:
                score += 3
            
            # Check if any word in the tool name appears in input
            for word in tool['name'].lower().split('_'):
                if word in user_input_lower:
                    score += 1
            
            # Check if category appears in input
            if tool['category'].lower() in user_input_lower:
                score += 2
            
            # Add the tool and its score
            scored_tools.append((tool, score))
        
        # Sort by score (descending) and take top_n
        scored_tools.sort(key=lambda x: x[1], reverse=True)
        top_tools = [tool for tool, score in scored_tools[:top_n]]
        
        return top_tools
