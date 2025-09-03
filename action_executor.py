#!/usr/bin/env python3
"""
Action Executor
This module is responsible for taking the JSON output from specialized agents
and executing the corresponding tool functions.
"""

import logging
from typing import Dict, Any, List
from database import DatabaseManager

# --- CORRECT IMPORTS ---
# Import the registry from tools.py
from tools import tool_registry 
# Import the context function from ai_tools.py
from ai_tools import set_context
# We import ai_tools itself to make sure Python runs it and the @tool decorators register the functions
import ai_tools

logger = logging.getLogger(__name__)

class ActionExecutor:
    """
    Executes a list of actions by dispatching them to the correct, registered tool.
    """
    
    def __init__(self, db_manager: DatabaseManager, user_id: str):
        """
        Initializes the ActionExecutor for a specific user.
        """
        if not db_manager or not user_id:
            raise ValueError("ActionExecutor requires a valid DatabaseManager and user_id.")
            
        self.db_manager = db_manager
        self.user_id = user_id

        # This call sets the global context for the tool decorator
        set_context(self.db_manager.supabase, self.user_id)

    def execute_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Executes a list of actions using the tool registry's execution method.
        """
        all_results = []
        if not actions:
            return all_results

        for i, action in enumerate(actions, 1):
            tool_name = action.get('type')
            
            ### <<< THIS IS THE PERMANENT FIX >>> ###
            # Instead of looking for a 'parameters' key, we build the params dictionary
            # from all other keys in the action. This correctly handles the "flat" JSON
            # structure produced by your AI agent.
            params = {key: value for key, value in action.items() if key != 'type'}
            
            logger.info(f"▶️ Executing action {i}/{len(actions)}: {tool_name} with params: {params}")

            if tool_name in tool_registry:
                try:
                    # Execute the tool by name, unpacking the correctly built params dictionary
                    result = tool_registry.execute(name=tool_name, **params)
                    all_results.append(result)
                    
                except Exception as e:
                    error_msg = f"Error executing tool '{tool_name}': {e}"
                    logger.exception(error_msg)
                    all_results.append({"success": False, "error": error_msg})
            else:
                error_msg = f"Error: Tool '{tool_name}' not found in registry."
                logger.error(error_msg)
                all_results.append({"success": False, "error": error_msg})
                
        return all_results