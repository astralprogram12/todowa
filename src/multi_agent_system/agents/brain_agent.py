#!/usr/bin/env python3
"""
Brain Agent - Manages AI Behavior and User Preferences (Stateful Version)

CORE PURPOSE:
- Intelligently manages user preferences by always considering the current state.
- Uses a single, powerful AI call to merge new requests with existing settings.
- Generates executable JSON actions to synchronize the database with the desired state.
"""

import json
import logging
import time
from typing import Dict, Any, Optional

# We assume ai_tools is available for fetching memories.
# This would typically be handled by the ActionExecutor, but for the agent's
# internal logic, we might need a direct way to fetch context.
# For this example, we'll simulate the fetch from the user_context.

logger = logging.getLogger(__name__)

class BrainAgent:
    def __init__(self, ai_model=None, api_key_manager=None):
        self.ai_model = ai_model
        self.api_key_manager = api_key_manager
        self.last_api_call = 0
        self.rate_limit_seconds = 2

    def process_command(self, user_command: str, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Processes a command by fetching current state, analyzing the request in context,
        and returning the executable JSON action(s).
        """
        if not self.ai_model:
            return self._error_response("Brain Agent is not properly initialized.")

        try:
            # STEP 1: FETCH - Get the current brain state from the user_context.
            # The main chat loop provides this context.
            current_memories = user_context.get('ai_brain', [])
            
            # STEP 2: ANALYZE & MERGE - Make a single AI call with the full context.
            prompt = self._build_stateful_analysis_prompt(user_command, current_memories)
            response_text = self._make_ai_request_sync(prompt)
            
            # STEP 3: EXECUTE - The AI's response contains the final actions.
            clean_text = response_text.strip().replace('```json', '').replace('```', '')
            analysis_result = json.loads(clean_text)

            if "error" in analysis_result:
                return self._error_response(analysis_result["error"])

            logger.info(f"Stateful brain analysis result: {analysis_result}")
            return analysis_result

        except Exception as e:
            logger.exception(f"Stateful brain processing failed: {e}")
            return self._error_response("An error occurred while processing your preference request.")

    def _make_ai_request_sync(self, prompt: str) -> Optional[str]:
        """Makes a synchronous AI request."""
        # (This function remains the same as your previous version)
        if not self.ai_model:
            logger.error("AI model is not available for the BrainAgent.")
            return None
        try:
            # Enforce rate limit
            time_since_call = time.time() - self.last_api_call
            if time_since_call < self.rate_limit_seconds:
                time.sleep(self.rate_limit_seconds - time_since_call)
            self.last_api_call = time.time()
            
            response = self.ai_model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.exception(f"AI request failed in BrainAgent: {e}")
            return None

    def _error_response(self, message: str) -> Dict[str, Any]:
        """Creates a standardized error response dictionary."""
        return {'success': False, 'actions': [], 'response': f"❌ {message}"}

    def _build_stateful_analysis_prompt(self, user_command: str, current_memories: list) -> str:           
        # Find the single communication_style memory from the list
        comm_style_memory = next((mem for mem in current_memories if mem.get("brain_data_type") == "communication_style"), None)

        return f"""You are an intelligent assistant that manages a user's communication style preferences  personalities. Your task is to analyze a user's new command and produce the final, updated version of a single JSON object that holds all their preferences, based on their current settings.

    **Golden Rule: DO NOT rewrite the entire object from scratch. Your goal is to ADD to or MODIFY the "Current Communication Style Object", preserving all non-conflicting keys.**

    **Current Communication Style Object:**
    {json.dumps(comm_style_memory.get('content_json') if comm_style_memory else {}, indent=2)}

    **User's New Command:**
    "{user_command}"

    **Core Rules:**
    - **PRESERVE AND MERGE:** If the new command is compatible with existing preferences (e.g., adding "use emojis" when a language is already set), you MUST add the new key-value pair to the existing object. DO NOT remove the other keys.
    - **LATEST WINS (CONFLICTS ONLY):** Only update the value of an existing key if the new command directly conflicts with it (e.g., changing language from English to Indonesian).
    - **DELETION:** If the user asks to forget or remove a single preference (e.g., "don't use emojis"), remove only that key-value pair from the JSON and change it to "Formal and nice". never generate a `delete_memory`
    - **LISTING:** If the user asks to see their settings, summarize the "Current Communication Style Object" and generate an empty `actions` list.

    
    **EXTRA information:**
    - Persoanlities =  communication style preferences
    **Output Instructions:**
    - Generate a `response` message for the user.
    - Generate an `actions` list containing the necessary `create_or_update_memory` or `delete_memory` action.

    **Respond with ONLY a valid JSON object containing 'response' and 'actions' keys.**

    ---
    **Example 1: Adding a Key (MERGING)**
    User Command: "always use emojis in your answers"
    Current Style Object: `{{"language_preference": "English"}}`
    **Correct Output:**
    {{
    "response": "Got it, I'll add emojis to my responses from now on! :) ",
    "actions": [
        {{
        "type": "create_or_update_memory",
        "memory_type": "communication_style",
        "data": {{
            "language_preference": "English",
            "use_emojis": true
        }},
        "content": "User prefers English and wants emojis."
        }}
    ]
    }}
    ---
    **Example 2: Replacing a Key's Value (CONFLICT)**
    User Command: "actually, always speak to me in Indonesian"
    Current Style Object: `{{"language_preference": "English", "use_emojis": true}}`
    **Correct Output:**
    {{
    "response": "Tentu saja! sekarang saya akan menjawab di indonesia",
    "actions": [
        {{
        "type": "create_or_update_memory",
        "memory_type": "communication_style",
        "data": {{
            "language_preference": "Indonesian",
            "use_emojis": true
        }},
        "content": "User prefers Indonesian and wants emojis."
        }}
    ]
    }}
    ---
    **Example 3: Deleting a Key**
    User Command: "forget what I said about emojis"
    Current Style Object: `{{"language_preference": "Indonesian", "use_emojis": true}}`
    **Correct Output:**
    {{
    "response": "Okay, I've removed the preference about using emojis.",
    "actions": [
        {{
        "type": "create_or_update_memory",
        "memory_type": "communication_style",
        "data": {{
            "language_preference": "Indonesian"
        }},
        "content": "User prefers Indonesian."
        }}
    ]
    }}
    ---
    **Example 4: Listing Preferences**
    User Command: "what are my preferences?"
    Current Style Object: `{{"language_preference": "Indonesian", "tone": "formal"}}`
    **Correct Output:**
    {{
    "response": "Currently, I'm set to respond in Indonesian with a formal tone. Let me know if you'd like to change that!",
    "actions": []
    }}
    """