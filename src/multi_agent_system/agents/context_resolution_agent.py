### NEW: Context Resolution Agent (Master Router) V2
# This agent acts as the central dispatcher for the system. It intelligently
# clarifies user input and routes the command to the appropriate specialized agent.
# This version has been enhanced with time-awareness to improve routing accuracy.

# CAPABILITIES:
# - 🌍 Polyglot Language Master: Excels in English, Indonesian, Spanish, etc.
# - 🔤 Intelligent Typo Correction: Handles misspellings and informal writing.
# - 🧠 Smart Pattern Recognition: Understands intent over literal text (e.g., "nevermind", corrections).
# - 🎯 Direct-to-Agent Routing: Determines the correct specialized agent to handle a request.
# - 🕒 **Time & Scheduling Awareness**: Recognizes dates, times, and recurring patterns
#   (e.g., "tomorrow", "at 5pm", "every Friday") to accurately route to the TaskAgent.

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
            return ai_result # Return the full result

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
        ### **CORE PRINCIPLES (MANDATORY)**

        1.  **Route, Never Execute:** Your only job is to prepare the command and select the destination. You do not answer questions or perform actions yourself.
        2.  **Clarify, Don't Invent:** Your primary role is to create a clear, self-contained string for the `clarified_command`. You resolve pronouns ("it", "that"), identify the core user intent, and strip conversational filler ("please", "can you"). You do not invent programmatic actions (like "create_task").
        3.  **Total Ambiguity Resolution:** The `clarified_command` you generate MUST be understandable by a downstream agent *without* any conversation history. Your output must be complete on its own.
        4.  **Preserve User Language:** Do not translate or rephrase the core components of the user's request, especially names, technical terms, or specific time expressions (e.g., "every Friday at noon").
        5.  **Be Explicit with Plurals**: When a user's command refers to multiple items (e.g., "all of them," "every task with 'X'"), you **must** resolve and list every specific item that the command applies to within the `clarified_command`. This ensures absolute clarity for the next agent.
        6.  **Annotate Implied Context**: For messages that imply a deeper meaning, you must add a brief, clarifying note within the `clarified_command`. For instance, a command to "update" something implies a change from a previous state.
        7.  **No Referential Pronouns:** Your `clarified_command` must never contain pronouns like 'he', 'she', 'it', 'they', 'prior', 'previous', 'last', or 'them'. Always replace them with the specific noun they refer to.

        ---
        ### **AGENT ROSTER & RESPONSIBILITIES**

        You must route to **exactly ONE** of the following agents:

        1.  **`TaskAgent`**:
            *   **Handles**: Managing a to-do list. This includes creating, updating, deleting, and completing immediate, non-scheduled tasks.
            *   **Typical Inputs**: "add a task to buy milk", "complete the last one", "delete the laundry task".

        2.  **`ScheduleAgent`**:
            *   **Handles**: Any and all actions involving a specific future time, date, or recurrence. This is for reminders, appointments, and scheduled events.
            *   **Typical Inputs**: "remind me to call mom tomorrow", "schedule a meeting for 3pm", "submit timesheet every Friday".

        3.  **`JournalAgent`**:
            *   **Handles**: Storing and managing the user's long-term, non-actionable information. This is the system's memory for facts, notes, and user-provided data.
            *   **Typical Inputs**: "remember that the wifi password is...", "log that I finished the project", "what is Rina's address?".

        4.  **`FindingAgent`**:
            *   **Handles**: Pure information retrieval. Its job is to **FIND FACTS**. It first searches the user's internal database (Tasks, Journal) and, if nothing is found, searches the live internet. It is a librarian, not a consultant.
            *   **Routing Rule**: Use this agent for direct questions starting with "what is," "who is," "find," "search for," or "tell me about."
            *   **Typical Inputs**: "find my notes on Project Alpha", "who is the CEO of OpenAI?", "what is the recipe for carbonara?".

        5.  **`BrainAgent`**:
            *   **Handles**: Managing user preferences about how the AI should behave, communicate, or operate.
            *   **Typical Inputs**: "always use a formal tone", "respond in Spanish from now on", "never suggest tasks from the 'work' category."

        6.  **`GeneralFallback`**:
            *   **Handles**: All other requests that are not specific commands for the agents above. This agent is a **consultant and creative partner**. It handles conversational small talk, provides advice, synthesizes ideas, and performs creative tasks.
            *   **Routing Rule**: If the user is asking for **ADVICE** ("what should I do?"), an **OPINION** ("which is better?"), or a **CREATIVE** task ("write a poem"), route here.
            *   **Typical Inputs**: "hello", "thanks!", "what should I focus on today?", "write a short story for me", "give me some ideas for a vacation."

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

        **Category 1: Simple & Direct Commands (No History)**

        *   **Example 1.1 (Task):**
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
        *   **Example 1.2 (Schedule):**
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

        **Category 2: Contextual Resolution (With History)**

        *   **Example 2.1 (Pronoun Resolution):**
            *   **History**: `[USER]: create a task to call the plumber` `[ASSISTANT]: I've created the task 'Call plumber'.`
            *   **User Message**: "add to it that it's for the kitchen sink"
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
        *   **Example 2.2 (Plural Resolution):**
            *   **History**: `[USER]: what are my tasks?` `[ASSISTANT]: You have 2 tasks: 'Call plumber' and 'Email report'.`
            *   **User Message**: "complete them both"
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

        **Category 3: Implied Intent & Annotation**

        *   **Example 3.1 (Implied Update):**
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
        *   **Example 3.2 (Implied Action):**
            *   **History**: `[USER]: search for Rina's contact` `[ASSISTANT]: I found a note titled 'Rina's Phone Number'.`
            *   **User Message**: "ok tell me"
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

        **Category 4: Distinguishing Find (Fact) vs. Fallback (Advice/Creative)**

        *   **Example 4.1 (FindingAgent - Factual):**
            *   **User Message**: "who is the current president of indonesia?"
            *   **JSON**:
                ```json
                {{
                "route_to": "FindingAgent",
                "clarified_command": "who is the current president of indonesia?",
                "latest_user_message": "who is the current president of indonesia?",
                "latest_system_reply": "",
                "previous_user_message": ""
                }}
                ```
        *   **Example 4.2 (GeneralFallback - Advice):**
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

        **Category 5: System Commands**

        *   **Example 5.1 (BrainAgent):**
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