# agent.py

import json
import logging
from datetime import date
from typing import Dict, List, Tuple, Any, Optional
import utils  # Assuming you have a utils.py for extract_json_block

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SmartTaskAgent:
    """A conversational AI assistant for managing to-do lists via chat."""
    
    SYSTEM_PROMPT = """
You are SmartTask Chat, a helpful AI assistant that manages a user's to-do list via chat.
Your goal is to understand the user's request, referencing the conversation history for context, and provide a helpful response followed by a JSON object of actions.

**RESPONSE FORMAT**
You MUST always answer in two parts:
1) A brief, conversational response.
2) A fenced JSON code block with the exact shape:
```json
{{
  "actions": [
    {{
      "type": "add_task",
      "title": "string",
      "notes": "string?",
      "dueDate": "YYYY-MM-DD?",
      "priority": "low|medium|high?",
      "difficulty": "easy|medium|hard?",
      "category": "string?",
      "tags": ["string"]?,
      "list": "string?"
    }},
    {{
      "type": "update_task",
      "id": "string?",
      "titleMatch": "string?",
      "patch": {{
        "title?": "string",
        "notes?": "string",
        "dueDate?": "YYYY-MM-DD",
        "status?": "todo|doing|done",
        "priority?": "low|medium|high",
        "difficulty?": "easy|medium|hard",
        "category?": "string",
        "tags?": ["string"],
        "list?": "string"
      }}
    }},
    {{ "type": "complete_task", "id": "string?", "titleMatch": "string?", "done": true }},
    {{ "type": "delete_task", "id": "string?", "titleMatch": "string?" }}
  ]
}}```

**INSTRUCTIONS & GUIDELINES**
- Today's Date: {current_date}
- Use the `CONVERSATION HISTORY` for context.
- Use `TASK CONTEXT` and `LIST CONTEXT` to answer questions or find tasks.
- To assign a task to a list, use the list's name from the `LIST CONTEXT` in the `list` property.
- For `tags`, always provide a JSON array of strings, e.g., `["work", "urgent"]`.
- When updating, only include fields in the `patch` object that need to be changed.
- Always include the JSON actions block, even if it's empty `[]`.
- answer in the user language if possible

**IMPORTANT NOTES**
- use assumtion to fill tags and Category when first adding a task

""".strip()

    def __init__(self):
        """Initialize the SmartTask agent."""
        pass
    
    def _build_prompt(self, history: List[Dict[str, str]], context: Dict[str, Any]) -> str:
        """Build the complete prompt, including history and all context."""
        prompt_template = self.SYSTEM_PROMPT.format(current_date=date.today().isoformat())
        
        # Extract list context and task context for clear separation in the prompt
        list_context = context.get('list_context', {})
        task_context = {"tasks": context.get("tasks", [])}

        formatted_history = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in history])

        full_prompt = (
            f"{prompt_template}\n\n"
            f"LIST CONTEXT:\n{json.dumps(list_context, indent=2)}\n\n"
            f"TASK CONTEXT:\n{json.dumps(task_context, indent=2)}\n\n"
            f"CONVERSATION HISTORY:\n{formatted_history}\n\n"
            f"ASSISTANT RESPONSE:"
        )
        return full_prompt
    
    def _parse_response(self, response_text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Parse the AI response into conversational reply and actions."""
        if not response_text:
            return "I didn't receive a proper response. Could you try again?", []
        
        logger.debug(f"Raw AI Output:\n{response_text}")
        
        conversational_reply = response_text.strip()
        actions = []
        
        try:
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
    
    def run_agent_one_shot(
        self, 
        model: Any, 
        history: List[Dict[str, str]], 
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Run the agent in a single pass, using conversation history and context."""
        logger.info("AGENT: Running in One-Shot Mode...")
        
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
            logger.error(f"Unexpected error in run_agent_one_shot: {e}", exc_info=True)
            return "Sorry, I ran into an unexpected error. Please try again.", []

# --- Main Entrypoint for your app.py ---
def run_agent_one_shot(model: Any, history: List[Dict[str, str]], context: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
    """Functional wrapper for the SmartTaskAgent class."""
    agent = SmartTaskAgent()
    return agent.run_agent_one_shot(model, history, context)