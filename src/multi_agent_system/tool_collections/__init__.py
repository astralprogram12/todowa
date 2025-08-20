# tool_collections/__init__.py
# Initialize and register all tool collections

import inspect # <--- [THE FIX] Import the inspect module

# Import the tool registry
from ..tools import tool_registry

# Import tool collections (if you have others, they can be listed here)
# from . import database_tools # Example

# Create a function to register additional tool collections
def register_tools():
    """Register additional tools from external modules."""
    try:
        # Try to import and register AI tools
        # NOTE: Your log mentioned 'enhanced_ai_tools'. If your file is named that,
        # change 'ai_tools' to 'enhanced_ai_tools' in the line below.
        import ai_tools
        
        # Register AI tools with the tool registry
        for attr_name in dir(ai_tools):
            obj = getattr(ai_tools, attr_name)
            
            # --- [THE FIX] ---
            # Use inspect.isfunction() to ensure we only register actual functions.
            # This will correctly ignore classes (like AIToolsError), variables, etc.
            if not attr_name.startswith('_') and inspect.isfunction(obj):
                
                print(f"Registering discovered tool: {attr_name}")
                # Register the function as a tool
                tool_registry.register_tool(
                    name=attr_name,
                    func=obj,
                    category='ai_tools', # Or another category if you prefer
                    description=getattr(obj, '__doc__', f"AI tool: {attr_name}")
                )
            # --- [END OF FIX] ---

    except ImportError:
        print("Could not import ai_tools module for tool registration")
    
    # Register other external tools here as needed

# Run the registration when the module is imported
register_tools()