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

    def resolve_context(self, user_command: str, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Takes a raw user command and the full conversation history, and returns a 
        structured, multi-step execution plan. This is the entry point to the Master Planner.
        """
        if not self.ai_model:
            logger.error("ContextResolutionAgent AI model is not initialized.")
            return {"sub_tasks": []}

        context_for_prompt = self._build_context_for_prompt(conversation_history)
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
        """A simple check: if the plan is empty, it might indicate a need for clarification."""
        return not routing_result.get("sub_tasks")

    def add_interaction(self, *args, **kwargs):
        """Placeholder for compatibility. The main app manages history."""
        pass

    def _build_context_for_prompt(self, history: List[Dict[str, str]]) -> Dict[str, str]:
        """
        Formats the last two turns of conversation history into the structured
        format required by the prompt.
        """
        context = {
            "previous_user": "", "previous_system": "",
            "latest_user": "", "latest_system": ""
        }
        if not history:
            return context

        # Get the last 4 messages, if they exist
        last_four = history[-4:]
        
        # This logic correctly maps the linear history to the structured format
        if len(last_four) == 1:
            context["latest_user"] = last_four[0].get('content', '')
        elif len(last_four) == 2:
            context["latest_user"] = last_four[0].get('content', '')
            context["latest_system"] = last_four[1].get('content', '')
        elif len(last_four) == 3:
            context["previous_user"] = last_four[0].get('content', '')
            context["previous_system"] = last_four[1].get('content', '')
            context["latest_user"] = last_four[2].get('content', '')
        elif len(last_four) == 4:
            context["previous_user"] = last_four[0].get('content', '')
            context["previous_system"] = last_four[1].get('content', '')
            context["latest_user"] = last_four[2].get('content', '')
            context["latest_system"] = last_four[3].get('content', '')
            
        return context

    def _build_master_planner_prompt(self, user_command: str, context: Dict[str, str]) -> str:
        """
        Builds the definitive Master Planner prompt, now with a fully structured
        and populated conversation history section.
        """
        current_time_utc = datetime.now(timezone.utc).isoformat()
        
        return f"""
        You are a world-class AI Master Planner. Your sole function is to deconstruct a user's command into a precise, multi-step execution plan. You MUST use the provided conversation context to resolve all ambiguities.

        You are aware that the current UTC time is {current_time_utc}.

        ---
        ### **CONVERSATION CONTEXT**
        PREVIOUS TURN USER: "{context['previous_user']}"
        PREVIOUS TURN SYSTEM: "{context['previous_system']}"
        LATEST TURN USER: "{context['latest_user']}"
        LATEST TURN SYSTEM: "{context['latest_system']}"
        ---
        ### **CURRENT USER COMMAND TO ANALYZE**
        "{user_command}"
        ---

        ### **CORE PRINCIPLES**
        1.  **Deconstruct and Group:** Break the command into steps. If multiple actions are for the SAME specialist, group them into a single sub-task.
        2.  **Total Ambiguity Resolution:** Use the conversation context to resolve all pronouns ("it", "them"). The final `clarified_command` must be fully self-contained.
        3.  **Route, Never Execute:** Your only job is to create the plan.

        ---
        ### **AGENT ROSTER**
        `TaskAgent`, `ScheduleAgent`, `JournalAgent`, `FindingAgent`, `BrainAgent`, `GeneralFallback`
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

        **Example 1: Pronoun Resolution with Full History**
        *   **Conversation Context**:
            PREVIOUS TURN USER: ""
            PREVIOUS TURN SYSTEM: ""
            LATEST TURN USER: "create a task to call the plumber"
            LATEST TURN SYSTEM: "I've created the task 'Call plumber'."
        *   **Current User Command**: "add to it that it's for the kitchen sink"
        *   **JSON**:
            ```json
            {{"sub_tasks": [
                {{"route_to": "TaskAgent", "clarified_command": "update the task 'Call plumber' to add the note 'it is for the kitchen sink'"}}
            ]}}
            ```

        **Example 2: Plural Resolution with Full History**
        *   **Conversation Context**:
            PREVIOUS TURN USER: ""
            PREVIOUS TURN SYSTEM: ""
            LATEST TURN USER: "what are my tasks?"
            LATEST TURN SYSTEM: "You have 2 tasks: 'Call plumber' and 'Email report'."
        *   **Current User Command**: "delete them both"
        *   **JSON**:
            ```json
            {{"sub_tasks": [
                {{"route_to": "TaskAgent", "clarified_command": "delete the following 2 tasks: 'Call plumber' and 'Email report'"}}
            ]}}
            ```

        **Example 3: Vague Follow-up with Full History**
        *   **Conversation Context**:
            PREVIOUS TURN USER: ""
            PREVIOUS TURN SYSTEM: ""
            LATEST TURN USER: "find my notes on Project Alpha"
            LATEST TURN SYSTEM: "I found two notes: 'Project Alpha - Initial Ideas' and 'Project Alpha - Budget'."
        *   **Current User Command**: "ok open the budget one"
        *   **JSON**:
            ```json
            {{"sub_tasks": [
                {{"route_to": "JournalAgent", "clarified_command": "display the content of the journal note titled 'Project Alpha - Budget'"}}
            ]}}
            ```

        **Example 4: Complex Multi-Specialist Command (No History)**
        *   **Conversation Context**:
            PREVIOUS TURN USER: ""
            PREVIOUS TURN SYSTEM: ""
            LATEST TURN USER: ""
            LATEST TURN SYSTEM: ""
        *   **Current User Command**: "add task eating dinner, and add to journal that rumah farah di bandung"
        *   **JSON**:
            ```json
            {{"sub_tasks": [
                {{"route_to": "TaskAgent", "clarified_command": "add task eating dinner"}},
                {{"route_to": "JournalAgent", "clarified_command": "add to journal that rumah farah di bandung"}}
            ]}}
            ```

        **Example 5: The CRITICAL Grouping Logic (ScheduleAgent)**
        *   **Conversation Context**:
            PREVIOUS TURN USER: ""
            PREVIOUS TURN SYSTEM: ""
            LATEST TURN USER: ""
            LATEST TURN SYSTEM: ""
        *   **Current User Command**: "schedule a party for Rina on August 30th at 7pm, and also remind me to buy a cake two days before."
        *   **JSON**:
            ```json
            {{"sub_tasks": [
                {{"route_to": "ScheduleAgent", "clarified_command": "schedule an event 'Rina's party' for August 30th at 7pm, and also remind me on August 28th to buy a cake for it"}}
            ]}}
            ```

        **Example 6: Very Complex Command with Mixed Grouping (No History)**
        *   **Conversation Context**:
            PREVIOUS TURN USER: ""
            PREVIOUS TURN SYSTEM: ""
            LATEST TURN USER: ""
            LATEST TURN SYSTEM: ""
        *   **Current User Command**: "Rina's birthday is August 30th, schedule a party for her that day at 7pm, remind me to buy a cake two days before, and also create a task to call the caterer."
        *   **JSON**:
            ```json
            {{"sub_tasks": [
                {{"route_to": "JournalAgent", "clarified_command": "remember that Rina's birthday is August 30th"}},
                {{"route_to": "ScheduleAgent", "clarified_command": "schedule an event 'Rina's party' for August 30th at 7pm, and also remind me on August 28th to buy a cake for it"}},
                {{"route_to": "TaskAgent", "clarified_command": "create a task to call the caterer"}}
            ]}}

Example 6: Deep Context Resolution (Two-Turn History)
Conversation Context:
PREVIOUS TURN USER: "find my notes about the Q3 report"
PREVIOUS TURN SYSTEM: "I found two notes: 'Q3 Report Draft' and 'Q3 Meeting Summary'. Which one are you referring to?"
LATEST TURN USER: "the meeting summary"
LATEST TURN SYSTEM: "Here is the 'Q3 Meeting Summary': [The summary content is displayed to the user...]"
Current User Command: "ok delete that note"
JSON:
code
JSON
{{"sub_tasks": [
    {{"route_to": "JournalAgent", "clarified_command": "delete the journal note titled 'Q3 Meeting Summary'"}}
]}}
Example 7: Very Complex Command with Mixed Grouping (No History)
Conversation Context:
PREVIOUS TURN USER: ""
PREVIOUS TURN SYSTEM: ""
LATEST TURN USER: ""
LATEST TURN SYSTEM: ""
Current User Command: "Rina's birthday is August 30th, schedule a party for her that day at 7pm, remind me to buy a cake two days before, and also create a task to call the caterer."
JSON:
code
JSON
{{"sub_tasks": [
    {{"route_to": "JournalAgent", "clarified_command": "remember that Rina's birthday is August 30th"}},
    {{"route_to": "ScheduleAgent", "clarified_command": "schedule an event 'Rina's party' for August 30th at 7pm, and also remind me on August 28th to buy a cake for it"}},
    {{"route_to": "TaskAgent", "clarified_command": "create a task to call the caterer"}}
]}}
Example 8: Implied Intent from Context (Completing a Task)
Conversation Context:
PREVIOUS TURN USER: ""
PREVIOUS TURN SYSTEM: ""
LATEST TURN USER: "what do I need to do for the project launch?"
LATEST TURN SYSTEM: "You have one remaining task: 'Confirm final design with client'."
Current User Command: "I just got off the phone with them, it's approved"
JSON:
code
JSON
{{"sub_tasks": [
    {{"route_to": "TaskAgent", "clarified_command": "Complete the task 'Confirm final design with client' and add a note: 'Got approval from them over the phone'"}}
]}}
Example 9: Distinguishing Agents with Subtle Language ("remind me what...")
Conversation Context:
PREVIOUS TURN USER: ""
PREVIOUS TURN SYSTEM: ""
LATEST TURN USER: ""
LATEST TURN SYSTEM: ""
Current User Command: "remind me what is the wifi password?"
JSON:
code
JSON
{{"sub_tasks": [
    {{"route_to": "FindingAgent", "clarified_command": "find the wifi password"}}
]}}
Example 10: BrainAgent Preference Setting with Context
Conversation Context:
PREVIOUS TURN USER: "tell me about black holes"
PREVIOUS TURN SYSTEM: "[A very long, multi-paragraph explanation of black holes...]"
LATEST TURN USER: "that was too long"
LATEST TURN SYSTEM: "My apologies. I will try to be more concise in the future."
Current User Command: "yes, from now on always keep your answers to one paragraph"
JSON:
code
JSON
{{"sub_tasks": [
    {{"route_to": "BrainAgent", "clarified_command": "set user preference: from now on, always keep answers to a single paragraph"}}
]}}
Example 11: Distinguishing FindingAgent (Fact) vs. GeneralFallback (Advice)
Conversation Context:
PREVIOUS TURN USER: ""
PREVIOUS TURN SYSTEM: ""
LATEST TURN USER: ""
LATEST TURN SYSTEM: ""
Current User Command: "what should I focus on today?"
JSON:
code
JSON
{{"sub_tasks": [
    {{"route_to": "GeneralFallback", "clarified_command": "what should I focus on today?"}}
]}}
        ---
        Now, analyze the command and produce the execution plan based on the user command and the full conversation context. Respond with ONLY the valid JSON object.
        """