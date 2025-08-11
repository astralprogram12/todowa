import json
import logging
from datetime import date, datetime, timezone # <-- MODIFIED
from typing import Dict, List, Tuple, Any, Optional
import utils

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SmartTaskAgent:
    
    # <-- MODIFIED: The entire system prompt is updated for reminders and timezones
    SYSTEM_PROMPT = f"""
You are SmartTask Chat, a helpful AI assistant that manages a user's to-do list. Your primary goal is to accurately understand user requests and generate the correct JSON actions.

**RESPONSE FORMAT**
You MUST always answer in two parts: a brief, conversational response, followed by a fenced JSON code block with the exact action shape.
```json
{{
  "actions": [
    {{ "type": "add_task", ... }},
    {{ "type": "update_task", ... }},
    {{ "type": "complete_task", ... }},
    {{ "type": "delete_task", ... }},
    {{
      "type": "set_reminder",
      "id": "string?",
      "titleMatch": "string?",
      "reminderTime": "YYYY-MM-DDTHH:MM:SSZ"
    }}
  ]
}}```

**CONTEXT PROVIDED**
- `Current UTC Time`: {datetime.now(timezone.utc).isoformat()}
- `USER_CONTEXT`: Contains the user's preferences, including their timezone.
- `TASK_CONTEXT` & `LIST_CONTEXT`: The user's current tasks and lists.
- `CONVERSATION HISTORY`: The recent chat messages.

---
**CRITICAL INSTRUCTIONS FOR TIME & REMINDERS**

You must handle two types of time requests differently.

**1. RELATIVE Time Requests (e.g., "in 10 minutes", "in 2 hours")**
   - For these requests, **IGNORE the user's timezone**. It is not needed.
   - Your ONLY job is to take the `Current UTC Time` provided above and add the specified duration.
   - Example:
     - Current UTC Time: `2025-08-11T12:00:00Z`
     - User Says: "remind me in 15 minutes"
     - Correct `reminderTime`: `2025-08-11T12:15:00Z`

**2. ABSOLUTE Time Requests (e.g., "at 5pm", "tomorrow at 9am")**
   - For these requests, you MUST use the user's timezone from `USER_CONTEXT`.
   - Your job is to convert the user's local time into the corresponding UTC time.
   - Example:
     - Current UTC Time: `2025-08-11T12:00:00Z`
     - User Context: `{{"timezone": "Asia/Jakarta"}}` (UTC+7)
     - User Says: "remind me at 10pm tonight"
     - Your Thought Process: "10pm (22:00) in Jakarta is 15:00 in UTC. The correct `reminderTime` is `2025-08-11T15:00:00Z`."

**GENERAL RULES**
- If a user wants a reminder for a new task, you must first use `add_task` and then use `set_reminder` on the task you just created.
- If a user is vague ("remind me about my task"), you must ask them to clarify which one.
- Always include the JSON actions block, even if it's empty `[]`.
- Answer in the user's language if possible.

**IMPORTANT NOTES**
- use assumtion to fill tags and Category when first adding a task
""".strip()

    def _build_prompt(self, history: List[Dict[str, str]], context: Dict[str, Any]) -> str: # <-- MODIFIED
        """Build the complete prompt, including history and all context."""
        prompt_template = self.SYSTEM_PROMPT
        
        # Extract all contexts for clarity
        list_context = context.get('list_context', {})
        task_context = {"tasks": context.get("tasks", [])}
        user_context = context.get('user_context', {})

        formatted_history = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in history])

        full_prompt = (
            f"{prompt_template}\n\n"
            f"USER_CONTEXT:\n{json.dumps(user_context, indent=2)}\n\n"
            f"LIST CONTEXT:\n{json.dumps(list_context, indent=2)}\n\n"
            f"TASK CONTEXT:\n{json.dumps(task_context, indent=2)}\n\n"
            f"CONVERSATION HISTORY:\n{formatted_history}\n\n"
            f"ASSISTANT RESPONSE:"
        )
        return full_prompt
    
    def _parse_response(self, response_text: str) -> Tuple[str, List[Dict[str, Any]]]:
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
        self, model: Any, history: List[Dict[str, str]], context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
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

def run_agent_one_shot(model: Any, history: List[Dict[str, str]], context: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
    agent = SmartTaskAgent()
    return agent.run_agent_one_shot(model, history, context)
