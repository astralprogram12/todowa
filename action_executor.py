"""
Action Executor for the Multi-Agent System.

This module is a critical component of the AI assistant, responsible for
translating the structured output from specialized agents into concrete
actions. It receives a list of actions, where each action specifies a tool
to be used and the parameters for that tool. The `ActionExecutor` then
dispatches these calls to the appropriate functions registered in the
`tool_registry`.
"""

import logging
from typing import Dict, Any, List
from database import DatabaseManager
from tools import tool_registry
import ai_tools

logger = logging.getLogger(__name__)

class ActionExecutor:
    """
    Executes a list of actions by dispatching them to registered tools.

    This class iterates through a list of action dictionaries, identifies the
    specified tool for each, and executes it with the provided parameters.
    It serves as the bridge between the AI's decisions and the system's
    functional capabilities.

    Attributes:
        db_manager (DatabaseManager): An instance of the DatabaseManager for
                                      tools that require database access.
        user_id (str): The UUID of the user, to ensure actions are performed
                       in the correct context.
    """
    
    def __init__(self, db_manager: DatabaseManager, user_id: str):
        """
        Initializes the ActionExecutor for a specific user.

        Args:
            db_manager: A valid `DatabaseManager` instance.
            user_id: The UUID of the user performing the actions.

        Raises:
            ValueError: If `db_manager` or `user_id` is not provided.
        """
        if not db_manager or not user_id:
            raise ValueError("ActionExecutor requires a valid DatabaseManager and user_id.")
            
        self.db_manager = db_manager
        self.user_id = user_id

    def execute_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Executes a list of actions using the tool registry.

        This method processes a list of action dictionaries. For each action,
        it extracts the tool name and parameters, then calls the corresponding
        function from the `tool_registry`. It collects the results of each
        execution, including any errors, and returns them.

        Args:
            actions: A list of dictionaries, where each dictionary represents
                     an action with a 'type' (the tool name) and other keys
                     as parameters.

        Returns:
            A list of dictionaries, where each dictionary is the result of an
            executed action. The result typically includes a 'success' status
            and either the returned data or an error message.
        """
        all_results = []
        if not actions:
            return all_results

        for i, action in enumerate(actions, 1):
            tool_name = action.get('type')
            params = {key: value for key, value in action.items() if key != 'type'}
            
            logger.info(f"▶️ Executing action {i}/{len(actions)}: {tool_name} with params: {params}")

            if tool_name in tool_registry:
                try:
                    # Inject the db_manager for tools that require it.
                    if tool_name != "internet_search":
                        params['db_manager'] = self.db_manager

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