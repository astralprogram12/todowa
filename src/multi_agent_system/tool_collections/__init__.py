# tool_collections/__init__.py
# Final version using the correct registration method from the enhanced tool system.

import inspect
import sys
import os

# Add project root to the path to find the enhanced_tools module
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

# Import the single, unified tool_registry
from enhanced_tools import tool_registry


def register_tools():
    """Register additional tools from the enhanced_ai_tools module."""
    try:
        import enhanced_ai_tools
        
        # Register discovered tools with the unified tool registry
        for attr_name in dir(enhanced_ai_tools):
            obj = getattr(enhanced_ai_tools, attr_name)
            
            # Use inspect.isfunction() to ensure we only register actual functions.
            if not attr_name.startswith('_') and inspect.isfunction(obj):
                
                print(f"Registering discovered tool: {attr_name}")
                
                # --- [THE FIX] ---
                # Changed from the old 'register_tool' to the new 'register' method
                # to match the method in your EnhancedToolRegistry class.
                tool_registry.register(
                    name=attr_name,
                    func=obj,
                    category='ai_tools', # Or another category if you prefer
                    description=getattr(obj, '__doc__', f"AI tool: {attr_name}")
                )
                # --- [END OF FIX] ---

    except ImportError:
        print("Could not import enhanced_ai_tools module for tool registration")

# Run the registration when the module is imported
register_tools()