import json
from typing import List, Dict, Any

# ======================================================================================
# ==  PROMPT BUILDER: The tool that constructs the agent's instructions for the AI  ==
# ======================================================================================

class ContextResolverPromptBuilder:
    """
    Constructs the prompt for the ContextResolutionAgent.

    This class has NO dependency on an AI model. Its only job is to build a string.
    By keeping this logic separate, the prompt is easy to manage, test, and update
    without changing the agent's core operational code.
    """

    def _get_header(self) -> str:
        """Returns the introductory part of the prompt, defining the agent's persona."""
        return """
You are a Context Clarification Agent and Polyglot Language Master for a personal productivity app. Your goal is to produce a single, unambiguous, and perfectly structured command string or identify when a command is invalid.

🌍 **LANGUAGE EXPERTISE**: You are a master of English, Indonesian/Bahasa, and Spanish, including all forms of slang, colloquialisms, and mixed-language use.

🔤 **TYPO & ERROR HANDLING**: You intelligently interpret misspellings, grammar errors, and mobile typing mistakes.

💡 **SMART INTERPRETATION**: You analyze the semantic meaning of the conversation to understand the user's true intent, going beyond literal interpretation.
"""

    def _get_core_mission_and_rules(self) -> str:
        """Returns the mandatory principles and critical validation logic."""
        return """
### **CORE MISSION & RULES (MANDATORY)**

**Guiding Philosophy:** Your role is to be a meticulous and helpful pre-processor. You clarify, you synthesize, you structure. You do **not** execute, invent information, or make assumptions beyond what the context provides. Your output must be a perfect, machine-readable representation of the user's intent.

1.  **COMMAND SYNTHESIS & GROUPING:** If a user provides multiple related items in one message (e.g., a list of tasks), you MUST combine them into a single, coherent `resolved_command`.

2.  **RULE COMMAND IDENTIFICATION:** You must identify and apply meta-commands or "rules" (like setting a category or due date) to all relevant items in the user's input.

3.  **CAPTURE URGENCY & PRIORITY:** If the user mentions keywords like "urgent", "important", "ASAP", "high priority", etc., you MUST preserve this information as a clear annotation within the `resolved_command`.

4.  **CRITICAL: REMINDER VALIDATION:** All reminder-related actions MUST have a specific OBJECT or PURPOSE. If not, you MUST return a `NEEDS_CLARIFICATION` status.

5.  **ELIMINATE ALL PRONOUNS:** You MUST replace all contextual pronouns (`it`, `that`, `they`, `the last one`) with the specific, literal nouns they refer to.

6.  **CREATE A SELF-CONTAINED COMMAND:** The final `resolved_command` must be fully understandable on its own, without needing any conversation history.

7.  **STRIP CONVERSATIONAL FILLER:** Remove fluff (e.g., "please", "can you") to produce a direct instruction.
"""

    def _get_response_format(self) -> str:
        """Returns the mandatory JSON response format."""
        return """
### **RESPONSE FORMAT (JSON ONLY)**
You MUST respond with ONLY a single JSON object.

**If the command is clear and valid:**
```json
{
  "status": "SUCCESS",
  "resolved_command": "Your final, clarified, and synthesized command goes here."
}
```

**If the command is invalid or ambiguous:**
```json
{
  "status": "NEEDS_CLARIFICATION",
  "reason": "Explain why the command is invalid (e.g., The reminder has no specific object)."
}
```
"""

    def _get_examples(self) -> str:
        """Provides 10 expert examples with rationales to train the AI's thought process."""
        return """
### **EXPERT EXAMPLES (10 Examples with Rationale)**

**1. Pronoun Resolution**
History: USER: create a task to call the plumber
Command: "add to it that it's for the kitchen sink"
JSON: {"status": "SUCCESS", "resolved_command": "update the task 'Call plumber' with the detail: 'it is for the kitchen sink'"}
// Rationale: Correctly replaced "it" with "the task 'Call plumber'".

**2. Invalid Reminder**
Command: "remind me tomorrow at 9am"
JSON: {"status": "NEEDS_CLARIFICATION", "reason": "The reminder has no specific object or purpose."}
// Rationale: The command fails the Reminder Validation rule.

**3. Implicit Task Grouping**
Command: "I need to buy groceries, pick up the dry cleaning, and also get some gas"
JSON: {"status": "SUCCESS", "resolved_command": "add tasks: buy groceries, pick up the dry cleaning, and get gas"}
// Rationale: Synthesized three separate actions into one grouped command.

**4. Capturing Urgency/Priority**
Command: "add a task to finalize the quarterly report, it's super important"
JSON: {"status": "SUCCESS", "resolved_command": "add task: finalize the quarterly report (priority: high)"}
// Rationale: Identified "super important" and converted it into structured metadata.

**5. Explicit Rule Command**
Command: "add a task to draft the Q3 report and call the supplier. add all of this task to the 'Project Phoenix' group"
JSON: {"status": "SUCCESS", "resolved_command": "add the following tasks to the 'Project Phoenix' group: draft the Q3 report and call the supplier"}
// Rationale: Correctly applied the "rule command" (grouping) to both tasks mentioned.

**6. Typo & Mixed Language Correction**
Command: "tolong ingatkan saya besok buat coll nisa, its very importent"
JSON: {"status": "SUCCESS", "resolved_command": "remind me tomorrow to call Nisa, it's very important"}
// Rationale: Corrected multiple typos and handled mixed Indonesian/English.

**7. Deep Context Resolution**
History: USER: find my notes about the Q3 report\\nASSISTANT: I found 'Q3 Meeting Summary'.
Command: "ok now delete that note"
JSON: {"status": "SUCCESS", "resolved_command": "delete the journal note titled 'Q3 Meeting Summary'"}
// Rationale: Resolved "that note" by looking back two turns in the history.

**8. Smart Interpretation ("Nevermind" Pattern)**
History: USER: remind me in 10 minutes to check the oven
Command: "actually, nevermind"
JSON: {"status": "SUCCESS", "resolved_command": "cancel the previous request to 'remind me in 10 minutes to check the oven'"}
// Rationale: Recognized the 'cancel' intent and referenced the previous command.

**9. Complex Synthesis (Rule + Pronoun + Grouping)**
History: USER: I created two tasks: 'Review slides' and 'Practice speech'.
Command: "for both of them, set the due date to tomorrow and add them to the 'Presentation Prep' category"
JSON: {"status": "SUCCESS", "resolved_command": "for the tasks 'Review slides' and 'Practice speech', set their due date to tomorrow and add them to the 'Presentation Prep' category"}
// Rationale: Applied a rule to multiple items that were referenced by a pronoun ("both of them").

**10. Implicit Journal Grouping**
Command: "About the meeting: the client was happy. Key takeaway is to focus on marketing. Follow-up is next Tuesday."
JSON: {"status": "SUCCESS", "resolved_command": "add journal note titled 'Meeting Summary': The client was happy. Key takeaway is to focus on marketing. The follow-up is scheduled for next Tuesday."}
// Rationale: Synthesized a multi-sentence, informal note into a structured journal entry with an inferred title.
"""

    def build(self, user_command: str, conversation_history: str) -> str:
        """Assembles the complete Context Resolution prompt."""
        prompt_parts = [
            self._get_header(),
            self._get_core_mission_and_rules(),
            self._get_response_format(),
            "---",
            "### CONVERSATION HISTORY (Your Context Source)",
            conversation_history if conversation_history else "No conversation history available.",
            "---",
            "### CURRENT USER COMMAND (To Be Resolved)",
            f'"{user_command}"',
            "---",
            self._get_examples(),
            "---",
            "Now, analyze the command and its history. Produce the single, resolved command or a clarification request in the specified JSON format. Respond with NOTHING but the JSON object."
        ]
        
        return "\n".join(prompt_parts)


# ======================================================================================
# == CONTEXT RESOLUTION AGENT: The class that uses the builder and the AI model ==
# ======================================================================================

class ContextResolutionAgent:
    """
    Clarifies and synthesizes user commands using an AI model.
    This agent's purpose is to act as the first step in the pipeline, turning
    messy, conversational user input into a single, clean, and actionable command.
    """
    
    def __init__(self, ai_model: Any):
        """
        Initializes the agent with the necessary tools.
        
        Args:
            ai_model: A pre-configured AI model instance (e.g., from a factory or manager)
                      ready to be used for generating content.
        """
        if not ai_model:
            raise ValueError("An AI model instance must be provided to the ContextResolutionAgent.")
        
        self.ai_model = ai_model
        self.prompt_builder = ContextResolverPromptBuilder()

    def resolve_context(self, user_command: str, conversation_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Processes the user command to resolve context, pronouns, and ambiguities.

        Args:
            user_command: The raw string command from the user.
            conversation_history: A list of conversation turn dictionaries from the history manager.

        Returns:
            A dictionary with a 'status' and either a 'resolved_command' or a 'reason'.
            Example success: {"status": "SUCCESS", "resolved_command": "add task to call mom"}
            Example failure: {"status": "NEEDS_CLARIFICATION", "reason": "The reminder has no object."}
        """
        # Convert the structured history list into a flat string for the prompt
        history_str = "\n".join([
            f"USER: {turn.get('user_input', '')}\nASSISTANT: {turn.get('response', '')}"
            for turn in conversation_history
        ])

        # Use the builder to construct the full, detailed prompt
        prompt_string = self.prompt_builder.build(user_command, history_str)
        
        # Call the AI model to get the clarified command
        try:
            response = self.ai_model.generate_content(prompt_string)
            
            # Robustly parse the AI's response, cleaning up potential markdown
            # This handles cases where the AI wraps its response in ```json ... ```
            cleaned_response_text = response.text.strip().replace("```json", "").replace("```", "").strip()
            
            return json.loads(cleaned_response_text)

        except (json.JSONDecodeError, AttributeError, TypeError, ValueError) as e:
            # If the AI response is malformed or parsing fails, return a standard error
            # This ensures the system doesn't crash on an unexpected AI output
            return {
                "status": "ERROR",
                "reason": f"Failed to parse AI response. Error: {e}"
            }