# tool_collections/__init__.py
# Initialize and register all tool collections

# Import the tool registry
from ..tools import tool_registry

# Import tool collections
from . import database_tools
from . import time_tools
from . import memory_tools
from . import nlp_tools

# Create a function to register additional tool collections
def register_tools():
    """Register additional tools from external modules."""
    try:
        # Try to import and register AI tools
        import ai_tools
        
        # Register AI tools with the tool registry
        for attr_name in dir(ai_tools):
            # Skip private attributes and non-callable attributes
            if attr_name.startswith('_') or not callable(getattr(ai_tools, attr_name)):
                continue
            
            # Get the function
            func = getattr(ai_tools, attr_name)
            
            # Register the function as a tool
            tool_registry.register_tool(
                name=attr_name,
                func=func,
                category='ai_tools',
                description=getattr(func, '__doc__', f"AI tool: {attr_name}")
            )
    except ImportError:
        print("Could not import ai_tools module for tool registration")
    
    # Register other external tools here as needed

# Run the registration when the module is imported
register_tools()
