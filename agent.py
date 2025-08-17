import json
import logging
from datetime import date, datetime, timezone # <-- MODIFIED
from typing import Dict, List, Tuple, Any, Optional
import utils
from prompt_assembler import PromptAssembler
from datetime import datetime, timezone  # ensure timezone import is present

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SmartTaskAgent:

    # --- YOUR CURRENT _build_prompt FUNCTION ---
    def _build_prompt(self, history, context) -> str:
        assembler = PromptAssembler(root_dir="prompts", version="v1")
        user_context = context.get("user_context", {}) or {}
        memory_context = context.get("memory_context", {}) or {}
        category_context = context.get("category_context", {}) or {}
        task_context = {"tasks": context.get("tasks", [])}
        reminders_context = context.get("reminders_context", {}) or {}
        ai_actions_context = context.get("ai_actions_context", {}) or {}

        return assembler.build_full_prompt(
            user_context=user_context,
            memory_context=memory_context,
            category_context=category_context,
            task_context=task_context,
            reminders_context=reminders_context,
            ai_actions_context=ai_actions_context,
            conversation_history=history,
            current_utc_iso=datetime.now(timezone.utc).isoformat(),
        )
    
    # --- _parse_response FUNCTION ---
    def _parse_response(self, response_text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Parse the AI's raw text response into a message and a list of actions."""
        if not response_text:
            return "I didn't receive a proper response. Could you try again?", []
        
        logger.debug(f"Raw AI Output:\n{response_text}")
        
        conversational_reply = response_text.strip()
        actions = []
        
        try:
            # Assumes you have a utility function to safely extract JSON from a string
            parsed_json = utils.extract_json_block(response_text)
            
            if parsed_json and isinstance(parsed_json, dict):
                json_start_index = response_text.find("```json")
                if json_start_index != -1:
                    conversational_reply = response_text[:json_start_index].strip()
                
                actions = parsed_json.get("actions", [])
                
        except Exception as e:
            logger.error(f"Error parsing JSON response: {e}")
            actions = []
        
        if not conversational_reply:
            conversational_reply = "OK."
        
        return conversational_reply, actions
    
    # --- run_agent_one_shot METHOD (INSIDE THE CLASS) ---
    def run_agent_one_shot(
        self, 
        model: Any, 
        history: List[Dict[str, str]], 
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        This is the main method OF THE CLASS that runs the agent logic.
        """
        logger.info("AGENT CLASS: Running in One-Shot Mode...")
        
        context = context or {}
        
        if not history:
            return "I didn't receive any message. How can I help?", []
        
        try:
            full_prompt = self._build_prompt(history, context)
            
            ai_response = model.generate_content(full_prompt)
            response_text = getattr(ai_response, 'text', str(ai_response or ""))
            
            conversational_reply, actions = self._parse_response(response_text)
            
            logger.info(f"Generated {len(actions)} actions")
            logger.debug(f"Actions: {json.dumps(actions, indent=2)}")
            
            return conversational_reply, actions
            
        except Exception as e:
            logger.error(f"Unexpected error in agent run: {e}", exc_info=True)
            return "Sorry, I ran into an unexpected error. Please try again.", []

# --- THE CRUCIAL WRAPPER FUNCTION (OUTSIDE THE CLASS) ---
# This is the function that your app.py actually calls.

def run_agent_one_shot(model: Any, history: List[Dict[str, str]], context: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
    """
    This is the main entrypoint called by app.py.
    It creates an instance of our agent class and runs it.
    """
    # Create an instance of the agent
    agent_instance = SmartTaskAgent() 
    # Call the method that lives ON THE INSTANCE
    return agent_instance.run_agent_one_shot(model, history, context)


