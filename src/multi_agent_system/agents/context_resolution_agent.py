# File: src/multi_agent_system/agents/context_resolution_agent.py

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ContextResolutionAgent:
    """
    Acts as the Master Planner for the multi-agent system.
    It deconstructs user commands into a multi-step execution plan, using full
    conversation history to resolve all ambiguities. It maintains the original
    public method signatures for compatibility.
    """
    def __init__(self, ai_model=None):
        self.ai_model = ai_model
        # This agent is now stateless. The main app is responsible for managing and passing the history.

    def resolve_context(self, user_command: str, conversation_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Takes a raw user command and structured conversation history, and returns a 
        multi-step execution plan. This is the entry point to the Master Planner.
        """
        if not self.ai_model:
            logger.error("ContextResolutionAgent AI model is not initialized.")
            return {"sub_tasks": []}

        context_for_prompt = self._build_context_string_from_structured(conversation_history)
        prompt = self._build_master_planner_prompt(user_command, context_for_prompt)
        
        try:
            response = self.ai_model.generate_content(prompt)
            cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
            parsed_json = json.loads(cleaned_response)
            
            if "sub_tasks" not in parsed_json or not isinstance(parsed_json.get("sub_tasks"), list):
                logger.warning(f"Planner returned malformed JSON. Defaulting to fallback. Response: {cleaned_response}")
                return {"sub_tasks": [{"route_to": "GeneralFallback", "clarified_command": user_command}]}

            return parsed_json
        except (json.JSONDecodeError, TypeError, Exception) as e:
            logger.error(f"Failed to parse Master Planner response: {e}\nResponse was: {getattr(response, 'text', 'N/A')}")
            return {"sub_tasks": [{"route_to": "GeneralFallback", "clarified_command": user_command}]}

    def needs_clarification(self, routing_result: Dict[str, Any]) -> bool:
        """
        A simple check: if the plan is empty, it might indicate a need for clarification.
        """
        return not routing_result.get("sub_tasks")

    def add_interaction(self, *args, **kwargs):
        """
        Placeholder for compatibility. The main application is responsible
        for managing the conversation history state.
        """
        pass

    def _build_context_string_from_structured(self, history: List[Dict[str, Any]]) -> str:
        """
        Formats the structured conversation history into a simple string for the AI prompt.
        """
        if not history:
            return "No conversation history available."
        
        # We use the last 2 turns (4 entries max) to keep the prompt focused
        recent_turns = history[-2:]
        
        formatted_history = []
        for turn in recent_turns:
            # Use the raw user input and the final AI response for the context
            formatted_history.append(f"USER: {turn.get('user_input', '')}")
            formatted_history.append(f"ASSISTANT: {turn.get('response', '')}")
        
        return "\n".join(formatted_history)

    def _build_master_planner_prompt(self, user_command: str, conversation_history: str) -> str:
        """
        Builds the definitive Master Planner prompt, now with a fully structured
        and populated conversation history section and examples.
        """
        current_time_utc = datetime.now(timezone.utc).isoformat()
        
        return f"""
        You are a world-class AI Master Planner. Your sole function is to deconstruct a user's command into a precise, multi-step execution plan. You MUST use the provided conversation context to resolve all ambiguities.

        You are aware that the current UTC time is {current_time_utc}.

        ---
        ### **RECENT CONVERSATION HISTORY**
        {conversation_history}
        ---
        ### **CURRENT USER COMMAND TO ANALYZE**
        "{user_command}"
        ---


        ---
        ### **CORE PRINCIPLES (MANDATORY)**

        1.  **Route, Never Execute:** Your only job is to prepare the command and select the destination. You do not answer questions or perform actions yourself.
        2.  **Clarify, Don't Invent:** Your primary role is to create a clear, self-contained string for the `clarified_command`. You resolve pronouns ("it", "that"), identify the core user intent, and strip conversational filler ("please", "can you"). You do not invent programmatic actions (like "create_task").
        3.  **Total Ambiguity Resolution:** The `clarified_command` you generate MUST be understandable by a downstream agent *without* any conversation history. Your output must be complete on its own.
        4.  **Preserve User Language:** Do not translate or rephrase the core components of the user's request, especially names, technical terms, or specific time expressions (e.g., "every Friday at noon").
        5.  **Be Explicit with Plurals**: When a user's command refers to multiple items (e.g., "all of them," "every task with 'X'"), you **must** resolve and list every specific item that the command applies to within the `clarified_command`. This ensures absolute clarity for the next agent.
        6.  **Annotate Implied Context**: For messages that imply a deeper meaning, you must add a brief, clarifying note within the `clarified_command`. For instance, a command to "update" something implies a change from a previous state.
        7.  **No Referential Pronouns:** Your `clarified_command` must never contain pronouns like 'he', 'she', 'it', 'they', 'prior', 'previous', 'last', or 'them'. Always replace them with the specific noun they refer to.
        8.  **Combine similar intent to the same agent NEVER MENTION THE SAME AGENT TWICE
        ---
        ### **AGENT ROSTER & RESPONSIBILITIES**

        You must route to as few agent as possile and each agent is maximum ONCE:

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
        "sub_tasks": [
            {{
            "route_to": "SelectedAgentName",
            "clarified_command": "The fully resolved and self-contained command for this specific step."
            }}
        ]
        }}
        ```
        ---
        ### **EXPERT EXAMPLES (Study these carefully)**

        **Example 1: Simple Multi-Specialist Command (No History)**
        *   **Conversation History**: `No conversation history available.`
        *   **Current User Command**: "add task eating dinner, and add to journal that rumah farah di bandung"
        *   **JSON**:
            ```json
            {{"sub_tasks": [
                {{"route_to": "TaskAgent", "clarified_command": "add task eating dinner"}},
                {{"route_to": "JournalAgent", "clarified_command": "add to journal that rumah farah di bandung"}}
            ]}}
            ```

        **Example 2: Pronoun Resolution with Full History**
        *   **Conversation History**: `USER: create a task to call the plumber\nASSISTANT: I've created the task 'Call plumber'.`
        *   **Current User Command**: "add to it that it's for the kitchen sink"
        *   **JSON**:
            ```json
            {{"sub_tasks": [
                {{"route_to": "TaskAgent", "clarified_command": "update the task 'Call plumber' to add the note 'it is for the kitchen sink'"}}
            ]}}
            ```

        **Example 3: Plural Resolution with Full History**
        *   **Conversation History**: `USER: what are my tasks?\nASSISTANT: You have 2 tasks: 'Call plumber' and 'Email report'.`
        *   **Current User Command**: "delete them both"
        *   **JSON**:
            ```json
            {{"sub_tasks": [
                {{"route_to": "TaskAgent", "clarified_command": "delete the following 2 tasks: 'Call plumber' and 'Email report'"}}
            ]}}
            ```

        **Example 4: The CRITICAL Grouping Logic (ScheduleAgent)**
        *   **Conversation History**: `No conversation history available.`
        *   **Current User Command**: "schedule a party for Rina on August 30th at 7pm, and also remind me to buy a cake two days before."
        *   **JSON**:
            ```json
            {{"sub_tasks": [
                {{"route_to": "ScheduleAgent", "clarified_command": "schedule an event 'Rina's party' for August 30th at 7pm, and also remind me on August 28th to buy a cake for it"}}
            ]}}
            ```

        **Example 5: The CRITICAL Grouping Logic (TaskAgent)**
        *   **Conversation History**: `No conversation history available.`
        *   **Current User Command**: "delete my 'review budget' task and add a new one to 'finalize report'"
        *   **JSON**:
            ```json
            {{"sub_tasks": [
                {{"route_to": "TaskAgent", "clarified_command": "delete the 'review budget' task and add a new task to 'finalize report'"}}
            ]}}
            ```

        **Example 6: Deep Context Resolution (Two-Turn History)**
        *   **Conversation History**: `USER: find my notes about the Q3 report\nASSISTANT: I found two notes: 'Q3 Report Draft' and 'Q3 Meeting Summary'. Which one are you referring to?\nUSER: the meeting summary\nASSISTANT: Here is the 'Q3 Meeting Summary': [The summary content is displayed to the user...]`
        *   **Current User Command**: "ok delete that note"
        *   **JSON**:
            ```json
            {{"sub_tasks": [
                {{"route_to": "JournalAgent", "clarified_command": "delete the journal note titled 'Q3 Meeting Summary'"}}
            ]}}
            ```

        **Example 7: Very Complex Command with Mixed Grouping (No History)**
        *   **Conversation History**: `No conversation history available.`
        *   **Current User Command**: "Rina's birthday is August 30th, schedule a party for her that day at 7pm, remind me to buy a cake two days before, and also create a task to call the caterer."
        *   **JSON**:
            ```json
            {{"sub_tasks": [
                {{"route_to": "JournalAgent", "clarified_command": "remember that Rina's birthday is August 30th"}},
                {{"route_to": "ScheduleAgent", "clarified_command": "schedule an event 'Rina's party' for August 30th at 7pm, and also remind me on August 28th to buy a cake for it"}},
                {{"route_to": "TaskAgent", "clarified_command": "create a task to call the caterer"}}
            ]}}
            ```

        **Example 8: Implied Intent from Context (Completing a Task)**
        *   **Conversation History**: `USER: what do I need to do for the project launch?\nASSISTANT: You have one remaining task: 'Confirm final design with client'.`
        *   **Current User Command**: "I just got off the phone with them, it's approved"
        *   **JSON**:
            ```json
            {{"sub_tasks": [
                {{"route_to": "TaskAgent", "clarified_command": "Complete the task 'Confirm final design with client' and add a note: 'Got approval from them over the phone'"}}
            ]}}
            ```

        **Example 9: Distinguishing Agents with Subtle Language ("remind me what...")**
        *   **Conversation History**: `No conversation history available.`
        *   **Current User Command**: "remind me what is the wifi password?"
        *   **JSON**:
            ```json
            {{"sub_tasks": [
                {{"route_to": "FindingAgent", "clarified_command": "find the wifi password"}}
            ]}}
            ```

        **Example 10: BrainAgent Preference Setting with Full History**
        *   **Conversation History**: `USER: tell me about black holes\nASSISTANT: [A very long, multi-paragraph explanation of black holes...]\nUSER: that was too long\nASSISTANT: My apologies. I will try to be more concise in the future.`
        *   **Current User Command**: "yes, from now on always keep your answers to one paragraph"
        *   **JSON**:
            ```json
            {{"sub_tasks": [
                {{"route_to": "BrainAgent", "clarified_command": "set user preference: from now on, always keep answers to a single paragraph"}}
            ]}}
            ```

        **Example 11: Distinguishing `FindingAgent` (Fact) vs. `GeneralFallback` (Advice)**
        *   **Conversation History**: `No conversation history available.`
        *   **Current User Command**: "what should I focus on today?"
        *   **JSON**:
            ```json
            {{"sub_tasks": [
                {{"route_to": "GeneralFallback", "clarified_command": "what should I focus on today?"}}
            ]}}
            ```
        ---
        Now, analyze the command and produce the execution plan based on the user command and the full conversation history. Respond with ONLY the valid JSON object.
        """