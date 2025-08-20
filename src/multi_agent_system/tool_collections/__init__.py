# tool_collections/__init__.py
# Initialize and register all tool collections

import inspect

# --- [THE FIX] ---
# Import the SINGLE, UNIFIED tool_registry from the correct file in the project's root directory.
# This also requires adding the root path to sys.path so the import can be found.
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from enhanced_tools import tool_registry
# --- [END OF FIX] ---


# This function registers your new, enhanced AI tools.
def register_tools():
    """Register additional tools from external modules."""
    try:
        # Import your new, primary toolset
        import enhanced_ai_tools
        
        # Register AI tools with the unified tool registry
        for attr_name in dir(enhanced_ai_tools):
            obj = getattr(enhanced_ai_tools, attr_name)
            
            # Use inspect.isfunction() to ensure we only register actual functions.
            if not attr_name.startswith('_') and inspect.isfunction(obj):
                
                print(f"Registering discovered tool: {attr_name}")
                tool_registry.register_tool(
                    name=attr_name,
                    func=obj,
                    category='ai_tools', # Or another category if you prefer
                    description=getattr(obj, '__doc__', f"AI tool: {attr_name}")
                )

    except ImportError:
        print("Could not import enhanced_ai_tools module for tool registration")
    
# Run the registration when the module is imported
register_tools()