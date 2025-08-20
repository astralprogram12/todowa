# tools.py
# Tools system for the multi-agent architecture

from typing import Dict, Any, List, Callable, Optional
import inspect
import time
import asyncio
import traceback

class ToolRegistry:
    """Registry for tools that agents can use.
    
    The ToolRegistry provides a way to register, discover, and use tools
    across the multi-agent system. Tools are functions with metadata that
    can be called by agents to perform specific tasks.
    """
    
    def __init__(self):
        """Initialize the tool registry."""
        self.tools = {}
        self.categories = {}
    
    def register_tool(self, name: str, func: Callable, category: str = 'general', 
                     description: str = '', required_params: List[str] = None,
                     optional_params: Dict[str, Any] = None) -> None:
        """Register a tool in the registry.
        
        Args:
            name: The name of the tool
            func: The function to call when the tool is used
            category: The category of the tool
            description: A description of what the tool does
            required_params: List of required parameter names
            optional_params: Dictionary of optional parameters with default values
        """
        # Extract parameters from function signature if not provided
        if required_params is None or optional_params is None:
            sig = inspect.signature(func)
            all_params = list(sig.parameters.keys())
            
            if required_params is None:
                # Assume all parameters without defaults are required
                required_params = [p.name for p in sig.parameters.values() 
                                 if p.default == inspect.Parameter.empty]
            
            if optional_params is None:
                # Get parameters with defaults
                optional_params = {p.name: p.default for p in sig.parameters.values() 
                                  if p.default != inspect.Parameter.empty}
        
        # Register the tool
        self.tools[name] = {
            'func': func,
            'category': category,
            'description': description,
            'required_params': required_params or [],
            'optional_params': optional_params or {}
        }
        
        # Update category mapping
        if category not in self.categories:
            self.categories[category] = []
        if name not in self.categories[category]:
            self.categories[category].append(name)
    
    def get_tool(self, name: str) -> Dict[str, Any]:
        """Get a tool by name.
        
        Args:
            name: The name of the tool
            
        Returns:
            The tool information dictionary
            
        Raises:
            KeyError: If the tool is not found
        """
        if name not in self.tools:
            raise KeyError(f"Tool '{name}' not found in registry")
        return self.tools[name]
    
    def list_tools(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available tools, optionally filtered by category.
        
        Args:
            category: Optional category to filter by
            
        Returns:
            List of tool information dictionaries
        """
        if category:
            # Return tools in the specified category
            if category not in self.categories:
                return []
            return [{
                'name': name,
                'category': self.tools[name]['category'],
                'description': self.tools[name]['description'],
                'required_params': self.tools[name]['required_params'],
                'optional_params': self.tools[name]['optional_params']
            } for name in self.categories[category]]
        else:
            # Return all tools
            return [{
                'name': name,
                'category': info['category'],
                'description': info['description'],
                'required_params': info['required_params'],
                'optional_params': info['optional_params']
            } for name, info in self.tools.items()]
    
    def list_categories(self) -> List[str]:
        """List all available tool categories.
        
        Returns:
            List of category names
        """
        return list(self.categories.keys())
    
    async def call_tool(self, name: str, **kwargs) -> Dict[str, Any]:
        """Call a tool by name with the provided parameters.
        
        Args:
            name: The name of the tool
            **kwargs: Parameters to pass to the tool
            
        Returns:
            The result of the tool call
            
        Raises:
            KeyError: If the tool is not found
            ValueError: If required parameters are missing
        """
        start_time = time.time()
        
        try:
            # Get the tool
            tool = self.get_tool(name)
            
            # Validate required parameters
            missing_params = [param for param in tool['required_params'] if param not in kwargs]
            if missing_params:
                raise ValueError(f"Missing required parameters for tool '{name}': {', '.join(missing_params)}")
            
            # Add default values for missing optional parameters
            for param, default in tool['optional_params'].items():
                if param not in kwargs:
                    kwargs[param] = default
            
            # Call the tool function
            func = tool['func']
            if asyncio.iscoroutinefunction(func):
                # If the function is async, await it
                result = await func(**kwargs)
            else:
                # Otherwise, call it directly
                result = func(**kwargs)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Return the result
            return {
                'status': 'success',
                'tool': name,
                'result': result,
                'execution_time': execution_time
            }
            
        except Exception as e:
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Log the error
            error_msg = str(e)
            traceback_str = traceback.format_exc()
            print(f"ERROR calling tool '{name}': {error_msg}\n{traceback_str}")
            
            # Return an error result
            return {
                'status': 'error',
                'tool': name,
                'error': error_msg,
                'traceback': traceback_str,
                'execution_time': execution_time
            }

# Create a global registry instance
tool_registry = ToolRegistry()

# Decorator for registering tools
def register_tool(name: str, category: str = 'general', description: str = '',
                required_params: List[str] = None, optional_params: Dict[str, Any] = None):
    """Decorator for registering a function as a tool.
    
    Args:
        name: The name of the tool
        category: The category of the tool
        description: A description of what the tool does
        required_params: List of required parameter names
        optional_params: Dictionary of optional parameters with default values
        
    Returns:
        The original function
    """
    def decorator(func):
        tool_registry.register_tool(
            name=name,
            func=func,
            category=category,
            description=description,
            required_params=required_params,
            optional_params=optional_params
        )
        return func
    return decorator
