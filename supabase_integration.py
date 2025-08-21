# supabase_integration.py
# Module for integrating Supabase with the multi-agent system

import os
import sys
import importlib

def setup_supabase_integration():
    """Set up the Supabase integration for the multi-agent system."""
    
    # Add user_input_files to path if not already there
    user_input_files_dir = os.path.join('/workspace', 'user_input_files')
    if user_input_files_dir not in sys.path:
        sys.path.append(user_input_files_dir)
        print(f"Added {user_input_files_dir} to sys.path")
    
    # Add the multi-agent system to the path
    multi_agent_system_dir = os.path.join('/workspace', 'multi_agent_system')
    if multi_agent_system_dir not in sys.path:
        sys.path.append(multi_agent_system_dir)
        print(f"Added {multi_agent_system_dir} to sys.path")
    
    # Add the enhanced multi-agent system to the path
    enhanced_dir = os.path.join('/workspace', 'enhanced_multi_agent_system')
    if enhanced_dir not in sys.path:
        sys.path.append(enhanced_dir)
        print(f"Added {enhanced_dir} to sys.path")
    
    # Copy the enhanced database tools to the multi-agent system
    try:
        # Import the original tools registry
        from multi_agent_system.code.src.multi_agent_system.tools import tool_registry
        
        # Import the enhanced database tools
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "enhanced_database_tools", 
            os.path.join(enhanced_dir, "tool_collections", "database_tools.py")
        )
        enhanced_database_tools = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(enhanced_database_tools)
        
        # Register the enhanced tools with the original registry
        for attr_name in dir(enhanced_database_tools):
            attr = getattr(enhanced_database_tools, attr_name)
            if callable(attr) and hasattr(attr, "__name__") and not attr_name.startswith("_"):
                # Get the original metadata from the function
                name = getattr(attr, "__tool_name__", attr_name)
                category = getattr(attr, "__tool_category__", "database")
                description = getattr(attr, "__tool_description__", attr.__doc__ or "")
                
                # Register the tool
                tool_registry.register_tool(
                    name=name,
                    func=attr,
                    category=category,
                    description=description
                )
                print(f"Registered enhanced tool: {name}")
        
        return True
    except Exception as e:
        print(f"Error setting up Supabase integration: {e}")
        return False

# Run the setup when this module is imported
success = setup_supabase_integration()
print(f"Supabase integration setup {'succeeded' if success else 'failed'}")
