# tools.py
# Tools system for the multi-agent architecture

import inspect
import time
import asyncio
import traceback
from typing import Dict, Any, List, Callable, Optional

# --- [ADDED] Path Correction to Find Root-Level Modules ---
# This code is crucial. It finds the project's root directory
# and adds it to Python's path, allowing us to import 'services.py'.
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.append(project_root)
# --- End Path Correction ---

# --- [ADDED] Import services.py with error handling ---
try:
    import services
except ImportError:
    print("!!! CRITICAL WARNING: services.py could not be imported. The send_reply_message tool will fail.")
    services = None
# --- End Added Section ---


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
            
            # We will ignore certain parameters that are injected by the system
            injected_params = ['supabase', 'ai_model', 'supabase_client', 'user_id']
            
            if required_params is None:
                # Assume all parameters without defaults are required
                required_params = [p.name for p in sig.parameters.values() 
                                 if p.default == inspect.Parameter.empty and p.name not in injected_params]
            
            if optional_params is None:
                # Get parameters with defaults
                optional_params = {p.name: p.default for p in sig.parameters.values() 
                                  if p.default != inspect.Parameter.empty and p.name not in injected_params}
        
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
        """Get a tool by name."""
        if name not in self.tools:
            raise KeyError(f"Tool '{name}' not found in registry")
        return self.tools[name]
    
    def list_tools(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available tools, optionally filtered by category."""
        if category:
            if category not in self.categories: return []
            return [{
                'name': name, 'category': self.tools[name]['category'], 'description': self.tools[name]['description'],
                'required_params': self.tools[name]['required_params'], 'optional_params': self.tools[name]['optional_params']
            } for name in self.categories[category]]
        else:
            return [{
                'name': name, 'category': info['category'], 'description': info['description'],
                'required_params': info['required_params'], 'optional_params': info['optional_params']
            } for name, info in self.tools.items()]
    
    def list_categories(self) -> List[str]:
        """List all available tool categories."""
        return list(self.categories.keys())
    
    async def call_tool(self, name: str, **kwargs) -> Dict[str, Any]:
        """Call a tool by name with the provided parameters."""
        start_time = time.time()
        
        try:
            tool = self.get_tool(name)
            missing_params = [param for param in tool['required_params'] if param not in kwargs]
            if missing_params:
                raise ValueError(f"Missing required parameters for tool '{name}': {', '.join(missing_params)}")
            
            for param, default in tool['optional_params'].items():
                if param not in kwargs:
                    kwargs[param] = default
            
            func = tool['func']
            if asyncio.iscoroutinefunction(func):
                result = await func(**kwargs)
            else:
                result = func(**kwargs)
            
            execution_time = time.time() - start_time
            return {
                'status': 'success', 'tool': name, 'result': result,
                'execution_time': execution_time
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            traceback_str = traceback.format_exc()
            print(f"ERROR calling tool '{name}': {error_msg}\n{traceback_str}")
            return {
                'status': 'error', 'tool': name, 'error': error_msg,
                'traceback': traceback_str, 'execution_time': execution_time
            }

# Create a global registry instance
tool_registry = ToolRegistry()

# Decorator for registering tools
def register_tool(name: str, category: str = 'general', description: str = '',
                required_params: List[str] = None, optional_params: Dict[str, Any] = None):
    """Decorator for registering a function as a tool."""
    def decorator(func):
        tool_registry.register_tool(
            name=name, func=func, category=category, description=description,
            required_params=required_params, optional_params=optional_params
        )
        return func
    return decorator

# ==============================================================================
# --- [ADDED] DEFINE AND REGISTER YOUR TOOLS BELOW ---
# ==============================================================================

@register_tool(
    name="send_reply_message",
    category="communication",
    description="Sends a final text message reply to the user. This is the last step in your process to communicate your findings or conversational response."
)
def send_reply_message(phone_number: str, message: str, **kwargs):
    """
    Sends a final reply message to the user via the Fonnte API.
    The **kwargs parameter is included to gracefully accept system-injected
    arguments like 'user_id' or 'supabase_client' without causing an error.
    
    Args:
        phone_number (str): The recipient's phone number.
        message (str): The text content to send to the user.
    """
    print(f"TOOL EXECUTED: send_reply_message to {phone_number}")
    
    if not services:
        error_msg = "services.py could not be loaded. Cannot send message."
        print(f"TOOL ERROR: {error_msg}")
        return {"status": "error", "message": error_msg}
        
    try:
        # The services function handles the actual API call
        result = services.send_fonnte_message(phone_number, message)
        
        # The tool should return a structured dictionary
        if result and result.get("status"):
            return {"status": "ok", "message": "Message sent successfully."}
        else:
            reason = result.get("reason", "Unknown Fonnte API error")
            return {"status": "error", "message": f"Failed to send message: {reason}"}
            
    except Exception as e:
        return {"status": "error", "message": f"An unexpected error occurred while sending message: {str(e)}"}

# --- Add any other tools here using the @register_tool decorator ---
# For example:
#
# @register_tool(
#     name="get_user_tasks",
#     category="database",
#     description="Retrieves the list of active tasks for a user."
# )
# def get_user_tasks(user_id: str, supabase_client, **kwargs):
#     # ... your database logic here ...
#     return {"status": "ok", "tasks": []}