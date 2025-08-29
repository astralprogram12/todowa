import json
from typing import Dict, Any

# ======================================================================================
# ==  PROMPT BUILDER: The tool that constructs the agent's instructions for the AI  ==
# ======================================================================================

class AuditPlannerPromptBuilder:
    """
    Constructs the prompt for the AuditAgent. Its role is to be a Master Router,
    intelligently splitting or grouping commands based on which specialist
    agent is required, and explaining its reasoning via a suggestion.
    """

    def _get_header(self) -> str:
        """Returns the introductory part of the prompt, defining the agent's persona."""
        return """
You are a world-class AI Master Router and Intelligent Planner. Your function is to analyze a single, clarified user command and create an execution plan by routing parts of the command to the correct specialist agents.
"""

    def _get_core_mission_and_rules(self) -> str:
        """Returns the mandatory principles for routing and segmentation."""
        return """
### **CORE MISSION & RULES (MANDATORY)**

1.  **THE PRINCIPLE OF SPECIALIST DELEGATION (The Golden Rule):** Your decision to split or group the command is based ENTIRELY on the destination agent.
    *   **WHEN TO SPLIT:** If a command contains parts that must be handled by **DIFFERENT** agents.
    *   **WHEN TO GROUP:** If a command contains multiple parts that are all handled by the **SAME** agent.

2.  **GOAL-ORIENTED ROUTING:** You must understand the user's underlying *goal* to choose the correct agent, not just their literal words.

3.  **CRITICAL: THE TASK vs. JOURNAL DISTINCTION:** This is the most important application of Goal-Oriented Routing.
    *   **A TASK is anything ACTIONABLE** that the user needs to *do*, especially if it involves a deadline. (e.g., "remember the report is due Friday" -> Goal is to track a deadline -> `TaskAgent`).
    *   **A JOURNAL ENTRY is NON-ACTIONABLE information** that the user wants to *store*. (e.g., "remember the wifi password is '123'" -> Goal is to store a fact -> `JournalAgent`).

4.  **VERBATIM COMMAND INTEGRITY:** You MUST pass the user's exact wording to the specialist agent in the `clarified_command` field. Do not rephrase, summarize, or extract parameters. The specialist agent is the expert.

5.  **PRODUCE A SUGGESTION (Justify Your Routing):** For every sub-task, you MUST provide a high-level `suggestion` that explains *why* you chose that specific agent based on your goal analysis.
"""

    def _get_agent_roster(self) -> str:
        """Defines the complete agent roster for routing decisions."""
        return """
### **AGENT ROUTING ROSTER**

1.  **`TaskAgent`**: Handles managing actionable to-do lists, including items with deadlines.
2.  **`ScheduleAgent`**: Handles reminders, appointments, and recurring events with specific times.
3.  **`JournalAgent`**: Handles storing non-actionable facts, notes, and memories.
4.  **`FindingAgent`**: Handles searching for information.
5.  **`BrainAgent`**: Handles changing the AI's behavior or preferences.
6.  **`GeneralFallback`**: Handles conversation, advice, and creative requests.
"""

    def _get_response_format(self) -> str:
        """Returns the correct JSON response format with the suggestion field."""
        return """
### **RESPONSE FORMAT (JSON ONLY)**
```json
{
  "sub_tasks": [
    {
      "route_to": "SelectedAgentName",
      "suggestion": "(Suggestion: I am routing this because...)",
      "clarified_command": "The original, verbatim segment of the user's command for this agent."
    }
  ]
}
```
"""

    def _get_examples(self) -> str:
        """Provides expert examples demonstrating the 5 core rules."""
        return """
### **EXPERT EXAMPLES**

**Example 1: The CRITICAL Task vs. Journal Distinction (Goal: Track Deadline)**
Resolved Command: "remember the project report is due this Friday"
JSON Output:
```json
{ "sub_tasks": [{"route_to": "TaskAgent", "suggestion": "(Suggestion: I'm routing this to the TaskAgent because the user's goal is to track an actionable deadline.)", "clarified_command": "the project report is due this Friday"}]}
```

**Example 2: The CRITICAL Task vs. Journal Distinction (Goal: Store Fact)**
Resolved Command: "remember that the client's main color preference is blue"
JSON Output:
```json
{ "sub_tasks": [{"route_to": "JournalAgent", "suggestion": "(Suggestion: I'm routing this to the JournalAgent because the user's goal is to store a non-actionable fact.)", "clarified_command": "remember that the client's main color preference is blue"}]}
```

**Example 3: SPLITTING a Command for Different Agents**
Resolved Command: "add a task to draft the proposal and find my notes on last year's proposal"
JSON Output:
```json
{ "sub_tasks": [{"route_to": "TaskAgent", "suggestion": "(Suggestion: I'm routing the first part to the TaskAgent to create a to-do item.)", "clarified_command": "add a task to draft the proposal"}, {"route_to": "FindingAgent", "suggestion": "(Suggestion: I'm routing the second part to the FindingAgent to search your notes.)", "clarified_command": "find my notes on last year's proposal"}]}
```

**Example 4: GROUPING a Command for the Same Agent**
Resolved Command: "add a task to buy groceries and add another task to get gas"
JSON Output:
```json
{ "sub_tasks": [{"route_to": "TaskAgent", "suggestion": "(Suggestion: I'm routing this to the TaskAgent and grouping these instructions, as they both involve creating tasks.)", "clarified_command": "add a task to buy groceries and add another task to get gas"}]}
```

**Example 5: Complex Plan with both SPLITTING and GROUPING**
Resolved Command: "remind me to call the vendor tomorrow at 10am, schedule a team sync for 3pm, and also log that the project kickoff was successful"
JSON Output:
```json
{ "sub_tasks": [{"route_to": "ScheduleAgent", "suggestion": "(Suggestion: I'm grouping these for the ScheduleAgent as they both involve scheduling specific times.)", "clarified_command": "remind me to call the vendor tomorrow at 10am, schedule a team sync for 3pm"}, {"route_to": "JournalAgent", "suggestion": "(Suggestion: I'm routing this to the JournalAgent because it's a non-actionable piece of information to be logged.)", "clarified_command": "log that the project kickoff was successful"}]}
```
"""

    def build(self, resolved_command: str) -> str:
        """Assembles the complete Audit & Planning prompt."""
        prompt_parts = [
            self._get_header(),
            self._get_core_mission_and_rules(),
            self._get_agent_roster(),
            self._get_response_format(),
            "---",
            "### **CLARIFIED COMMAND TO BE PLANNED**",
            f'"{resolved_command}"',
            "---",
            self._get_examples(),
            "---",
            "Now, create the execution plan based on the 5 core rules. Provide a suggestion for each routing decision. Respond with NOTHING but the JSON object."
        ]
        
        return "\n".join(prompt_parts)


# ======================================================================================
# == AUDIT AGENT: The class that uses the builder and the AI model to create plans ==
# ======================================================================================

class AuditAgent:
    """
    Analyzes a clarified command and routes segments of it to the appropriate
    specialist agents, creating a multi-step execution plan for the orchestrator.
    """
    
    def __init__(self, ai_model: Any):
        if not ai_model:
            raise ValueError("An AI model instance must be provided to the AuditAgent.")
        
        self.ai_model = ai_model
        self.prompt_builder = AuditPlannerPromptBuilder()

    def create_execution_plan(self, resolved_command: str) -> Dict[str, Any]:
        """
        Processes the clarified command to create a structured execution plan.

        Args:
            resolved_command: A clean, unambiguous command from the ContextResolutionAgent.

        Returns:
            A dictionary containing a 'sub_tasks' list, ready for the TodowaApp loop.
        """
        prompt_string = self.prompt_builder.build(resolved_command)
        
        try:
            response = self.ai_model.generate_content(prompt_string)
            cleaned_response_text = response.text.strip().replace("```json", "").replace("```", "").strip()
            
            plan = json.loads(cleaned_response_text)
            
            if 'sub_tasks' not in plan or not isinstance(plan['sub_tasks'], list):
                # Using print for debugging in case logging isn't set up
                print(f"ERROR: AuditAgent produced malformed plan. Output: {plan}")
                return {"sub_tasks": []}
            return plan

        except (json.JSONDecodeError, AttributeError, TypeError, ValueError) as e:
            print(f"ERROR: AuditAgent failed to parse AI response. Error: {e}")
            return {"sub_tasks": []}