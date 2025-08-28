"""
### NEW: Context Resolution Agent (Master Router) V2
This agent acts as the central dispatcher for the system. It intelligently
clarifies user input and routes the command to the appropriate specialized agent.
This version has been enhanced with time-awareness to improve routing accuracy.

CAPABILITIES:
- 🌍 Polyglot Language Master: Excels in English, Indonesian, Spanish, etc.
- 🔤 Intelligent Typo Correction: Handles misspellings and informal writing.
- 🧠 Smart Pattern Recognition: Understands intent over literal text (e.g., "nevermind", corrections).
- 🎯 Direct-to-Agent Routing: Determines the correct specialized agent to handle a request.
- 🕒 **Time & Scheduling Awareness**: Recognizes dates, times, and recurring patterns
  (e.g., "tomorrow", "at 5pm", "every Friday") to accurately route to the TaskAgent.
"""

import logging
import json
from typing import List, Dict, Any
from datetime import datetime, timezone

# --- Configure logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ConversationHistory:
    """
    Stores conversation history locally in memory for a single session.
    """
    def __init__(self):
        self.history: List[Dict[str, Any]] = []
        self.max_history = 5
        self.turn_counter = 0
    
    def add_interaction(self, user_input: str, clarified_input: str, response: Any):
        self.turn_counter += 1
        interaction = {
            'timestamp': datetime.now().isoformat(),
            'user_input': user_input,
            'clarified_input': clarified_input,
            'response': str(response) if response is not None else '',
            'conversation_turn': self.turn_counter
        }
        self.history.append(interaction)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_recent_context(self) -> List[Dict[str, Any]]:
        return self.history.copy()

# --- THIS IS THE CLASS NAME THE MAIN APPLICATION IS LOOKING FOR ---
class ContextResolutionAgent:
    """
    Agent that provides intelligent contextual understanding and acts as the master router.
    """
    def __init__(self, ai_model=None):
        self.ai_model = ai_model
        self.history_manager = ConversationHistory()

    def resolve_context(self, user_input: str) -> Dict[str, Any]:
        """
        Use AI to analyze user input, using conversation history for context, and route it.
        """
        recent_context = self.history_manager.get_recent_context()
        
        if not self.ai_model:
            logger.warning("AI model not available, routing cannot be determined.")
            return {'clarified_command': "NEEDS_CLARIFICATION", 'route_to': None}

        try:
            ai_result = self._ai_clarify_and_route(user_input, recent_context)
            
            clarified_command = ai_result.get('clarified_command')
            route_to = ai_result.get('route_to')

            if not clarified_command or (not isinstance(route_to, str) and route_to is not None):
                logger.error(f"AI failed to produce valid routing output. Response: {ai_result}")
                return {'clarified_command': "NEEDS_CLARIFICATION", 'route_to': None}

            if clarified_command.strip().upper() == "NEEDS_CLARIFICATION":
                logger.info(f"❓ Input unclear: '{user_input}' - needs user clarification")
                return {'clarified_command': "NEEDS_CLARIFICATION", 'route_to': None}
            
            logger.info(f"🤖 Routed: '{user_input}' -> '{clarified_command}' | Route: {route_to}")
            return {'clarified_command': clarified_command, 'route_to': route_to}

        except Exception as e:
            logger.exception(f"❌ Context clarification and routing failed: {e}")
            return {'clarified_command': "NEEDS_CLARIFICATION", 'route_to': None}

    def _ai_clarify_and_route(self, user_input: str, context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """AI-powered clarification with direct-to-agent routing decisions."""
        context_info = self._build_context_info(context)
        # NEW: Provide the current time to the AI for context
        current_time_utc = datetime.now(timezone.utc).isoformat()
            
        system_prompt = f"""
        You are a world-class AI router and command clarifier. Your sole function is to act as an intelligent, high-speed switchboard for a multi-agent system. You must analyze a user's message, fully resolve all ambiguities using the provided conversation context, and then generate a single, precise JSON object to route a self-contained command to the correct specialized agent.

        You are aware that the current UTC time is {current_time_utc}. Use this to understand relative dates and the timeliness of a query.

        ---
        ### **AGENT ROSTER & RESPONSIBILITIES**

        You must route to **exactly ONE** of the following agents:

        1.  **`TaskAgent`**: Manages immediate, non-scheduled to-do list items. Keywords: "task", "to-do", "add", "complete", "delete".
        2.  **`ScheduleAgent`**: Manages the user's calendar and time-based alerts. Keywords: "remind", "schedule", "appointment", "event", "alarm", specific times/dates.
        3.  **`JournalAgent`**: Manages the user's long-term memory (facts, notes). Keywords: "remember", "note", "log", "fact", "recall".
        4.  **`FindingAgent`**: The system's librarian; finds and retrieves factual information. Keywords: "find", "search", "what is", "who is", "look up".
        5.  **`BrainAgent`**: Manages user preferences about the AI's behavior. Keywords: "always", "never", "from now on", "your name is".
        6.  **`GeneralFallback`**: The system's creative partner and conversationalist. Handles advice, opinions, creative tasks, and conversation.

        ---
        ### **RESPONSE FORMAT (JSON ONLY)**
        ```json
        {{
        "route_to": "SelectedAgentName",
        "clarified_command": "The fully resolved and annotated user command as a string.",
        "latest_user_message": "The user's most recent, verbatim message.",
        "latest_system_reply": "The system's last reply from the previous turn. Empty string if no history.",
        "previous_user_message": "The user's message from the previous turn. Empty string if no history."
        }}
        ```
        ---
        ### **EXPERT EXAMPLES (Study these carefully)**

        **Example 1: Simple Task**
        *   **User Message**: "add task buy milk and eggs"
        *   **JSON**:
            ```json
            {{
            "route_to": "TaskAgent",
            "clarified_command": "add task: buy milk and eggs",
            "latest_user_message": "add task buy milk and eggs",
            "latest_system_reply": "",
            "previous_user_message": ""
            }}
            ```

        **Example 2: Simple Schedule**
        *   **User Message**: "remind me to check the oven in 20 minutes"
        *   **JSON**:
            ```json
            {{
            "route_to": "ScheduleAgent",
            "clarified_command": "remind to check the oven in 20 minutes",
            "latest_user_message": "remind me to check the oven in 20 minutes",
            "latest_system_reply": "",
            "previous_user_message": ""
            }}
            ```

        **Example 3: Pronoun Resolution with Full History**
        *   **User Message**: "add to it that it's for the kitchen sink"
        *   **Context**: The system just said "I've created the task 'Call plumber'." after the user said "create a task to call the plumber".
        *   **JSON**:
            ```json
            {{
            "route_to": "TaskAgent",
            "clarified_command": "update the task 'Call plumber' to add the note 'it is for the kitchen sink'",
            "latest_user_message": "add to it that it's for the kitchen sink",
            "latest_system_reply": "I've created the task 'Call plumber'.",
            "previous_user_message": "create a task to call the plumber"
            }}
            ```

        **Example 4: Plural Resolution with Full History**
        *   **User Message**: "complete them both"
        *   **Context**: The system just said "You have 2 tasks: 'Call plumber' and 'Email report'." after the user said "what are my tasks?".
        *   **JSON**:
            ```json
            {{
            "route_to": "TaskAgent",
            "clarified_command": "complete the following 2 tasks: 'Call plumber' and 'Email report'",
            "latest_user_message": "complete them both",
            "latest_system_reply": "You have 2 tasks: 'Call plumber' and 'Email report'.",
            "previous_user_message": "what are my tasks?"
            }}
            ```

        **Example 5: Implied Intent & Annotation**
        *   **User Message**: "rumah rina pindah ke bandung"
        *   **JSON**:
            ```json
            {{
            "route_to": "JournalAgent",
            "clarified_command": "Update Rina's house location to Bandung. The word 'pindah' (moved) implies this is a change from a previously stored address.",
            "latest_user_message": "rumah rina pindah ke bandung",
            "latest_system_reply": "",
            "previous_user_message": ""
            }}
            ```

        **Example 6: Vague Follow-up with Full History**
        *   **User Message**: "ok tell me"
        *   **Context**: The system just said "I found a note titled 'Rina's Phone Number'." after the user said "search for Rina's contact".
        *   **JSON**:
            ```json
            {{
            "route_to": "JournalAgent",
            "clarified_command": "The user wants to see the content of the note 'Rina's Phone Number' that was just mentioned.",
            "latest_user_message": "ok tell me",
            "latest_system_reply": "I found a note titled 'Rina's Phone Number'.",
            "previous_user_message": "search for Rina's contact"
            }}
            ```

        **Example 7: Distinguishing `FindingAgent` (Fact) vs. `GeneralFallback` (Advice)**
        *   **User Message**: "i feel unproductive, what should i do?"
        *   **JSON**:
            ```json
            {{
            "route_to": "GeneralFallback",
            "clarified_command": "i feel unproductive, what should i do?",
            "latest_user_message": "i feel unproductive, what should i do?",
            "latest_system_reply": "",
            "previous_user_message": ""
            }}
            ```

        **Example 8: Distinguishing `ScheduleAgent` (Time) vs. `TaskAgent` (No Time)**
        *   **User Message**: "I need to call the caterer about the event next week"
        *   **JSON**:
            ```json
            {{
            "route_to": "TaskAgent",
            "clarified_command": "add a task to call the caterer about the event next week",
            "latest_user_message": "I need to call the caterer about the event next week",
            "latest_system_reply": "",
            "previous_user_message": ""
            }}
            ```
            *   **Reasoning**: Although a time is mentioned ("next week"), the command is not to schedule something *for* next week, but to create a general to-do item. "Remind me next week to call" would go to ScheduleAgent.

        **Example 9: System Command to `BrainAgent`**
        *   **User Message**: "from now on, always reply in Bahasa Indonesia"
        *   **JSON**:
            ```json
            {{
            "route_to": "BrainAgent",
            "clarified_command": "set user preference for communication language to Bahasa Indonesia",
            "latest_user_message": "from now on, always reply in Bahasa Indonesia",
            "latest_system_reply": "",
            "previous_user_message": ""
            }}
            ```

        **Example 10: Complex Vague Command Resolved with Full History**
        *   **User Message**: "delete the last one"
        *   **Context**: The system just said "OK, I've created the journal entry 'Project Alpha Budget'." after the user said "remember the budget for project alpha is $5000".
        *   **JSON**:
            ```json
            {{
            "route_to": "JournalAgent",
            "clarified_command": "delete the journal entry titled 'Project Alpha Budget'",
            "latest_user_message": "delete the last one",
            "latest_system_reply": "OK, I've created the journal entry 'Project Alpha Budget'.",
            "previous_user_message": "remember the budget for project alpha is $5000"
            }}
            ```

        **Example 11: Distinguishing `FindingAgent` (Internal Fact) vs. `JournalAgent` (Memory)**
        *   **User Message**: "remind me what is Farah's address?"
        *   **JSON**:
            ```json
            {{
            "route_to": "FindingAgent",
            "clarified_command": "find Farah's address",
            "latest_user_message": "remind me what is Farah's address?",
            "latest_system_reply": "",
            "previous_user_message": ""
            }}
            ```
            *   **Reasoning**: Despite the word "remind," the core intent is a question ("what is..."), which is a retrieval job for the FindingAgent, not a new reminder for the ScheduleAgent.

        **Example 12: Creative Request to `GeneralFallback`**
        *   **User Message**: "give me some cool ideas for a new project"
        *   **JSON**:
            ```json
            {{
            "route_to": "GeneralFallback",
            "clarified_command": "give me some cool ideas for a new project",
            "latest_user_message": "give me some cool ideas for a new project",
            "latest_system_reply": "",
            "previous_user_message": ""
            }}
            ```
        """


        user_prompt = f"""
RECENT CONVERSATION HISTORY:
{context_info}
CURRENT USER INPUT: "{user_input}"
Based on all the rules and context provided, analyze the user's input and generate the required JSON response.
"""
        full_prompt = f"{system_prompt}\n\nHuman: {user_prompt}\n\nAssistant:"

        response = self.ai_model.generate_content(full_prompt)
        
        try:
            response_text = response.text.strip().replace('```json', '').replace('```', '')
            result = json.loads(response_text)

            if 'clarified_command' not in result or 'route_to' not in result:
                raise ValueError("AI output is missing required keys ('clarified_command', 'route_to').")
                
            return result
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse or validate JSON from Master Router AI: {e}\nResponse was: {response.text}")
            return {'clarified_command': "NEEDS_CLARIFICATION", 'route_to': None}

    def _build_context_info(self, context: List[Dict[str, Any]]) -> str:
        if not context: 
            return "No previous conversation context available."
        
        context_parts = []
        for interaction in reversed(context):
            turn = interaction.get('conversation_turn', 'N/A')
            user_input = interaction.get('user_input', '')
            clarified_input = interaction.get('clarified_input', '')
            
            turn_info = f"\nPrevious Turn #{turn}:\n  - User Said: \"{user_input}\""
            
            if clarified_input and clarified_input != user_input and "NEEDS_CLARIFICATION" not in clarified_input:
                turn_info += f"\n  - System Understood As: \"{clarified_input}\""
            
            context_parts.append(turn_info)
        return "\n".join(context_parts)

    def needs_clarification(self, resolved_context: Dict[str, Any]) -> bool:
        if isinstance(resolved_context, dict):
            return resolved_context.get('clarified_command', '').strip().upper() == "NEEDS_CLARIFICATION"
        return True

    def add_interaction(self, user_input: str, clarified_input: str, response: Any):
        self.history_manager.add_interaction(user_input, clarified_input, response)

    def clear_history(self):
        self.history_manager = ConversationHistory()
        logger.info("Cleared the local conversation history.")