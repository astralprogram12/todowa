"""
Prompt Assembler / Builder
--------------------------

Purpose
=======
Assemble the production prompt for SmartTaskAgent from modular files, then
append runtime context and conversation history to produce the final string
fed into the LLM.

Design Principles
=================
- Separation of concerns: static rules live in markdown/json parts on disk.
- Deterministic assembly order with versioning and locale support hooks.
- No dynamic values (like current time) inside rules; inject them only in the
  context block.
- Safe fallbacks: if a part is missing on disk, use a minimal embedded default
  text so the system can still run.

Usage
=====
from prompt_assembler import PromptAssembler

assembler = PromptAssembler(root_dir="prompts", version="v1")
system_prompt = assembler.assemble_rules()
full_prompt = assembler.build_full_prompt(
    user_context={"timezone": "Asia/Jakarta"},
    memory_context={},
    category_context={},
    task_context={"tasks": []},
    reminders_context={},
    ai_actions_context={},
    conversation_history=[{"role":"user","content":"hi"}],
    current_utc_iso="2025-08-17T09:00:00Z",
)

Feed `full_prompt` to your model.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# -----------------------------
# Embedded minimal fallbacks
# -----------------------------
_DEFAULT_PARTS: Dict[str, str] = {
    "00_header_persona.md": (
        "You are a helpful SmartTask Chat Assistant. Think twice before answering.\n"
        "Your goal is to generate flawless JSON actions.\n"
    ),
    "01_response_format.md": (
        "RESPONSE FORMAT: Answer in two parts: a conversational reply that ends with a question,\n"
        "then a fenced JSON code block with an `actions` array (can be empty).\n"
    ),
    "02_actions_schema.json": json.dumps({
        "actions": [
            {"type": "add_task", "title": "string"},
            {"type": "update_task", "titleMatch": "string", "patch": {"title?": "string", "notes?": "string"}},
            {"type": "complete_task", "titleMatch": "string"},
            {"type": "delete_task", "titleMatch": "string"},
            {"type": "set_reminder", "titleMatch": "string", "reminderTime": "YYYY-MM-DDTHH:MM:SSZ"},
            {"type": "update_reminder", "titleMatch": "string", "newReminderTime": "YYYY-MM-DDTHH:MM:SSZ"},
            {"type": "delete_reminder", "titleMatch": "string"},
            {"type": "add_memory", "title": "string", "content": "string?"},
            {"type": "search_memories", "query": "string"},
            {"type": "update_memory", "titleMatch": "string", "patch": {"title?": "string", "content?": "string"}},
            {"type": "delete_memory", "titleMatch": "string"},
            {
                "type": "schedule_ai_action",
                "action_type": ["summarize_tasks", "create_recurring_task"],
                "description": "string",
                "schedule": {"frequency": ["DAILY", "WEEKLY"], "by_day?": ["MO"], "at_time": "HH:MM"},
                "payload?": {"title?": "string"}
            },
            {"type": "update_ai_action", "descriptionMatch": "string", "patch": {"description?": "string", "schedule?": {}}},
            {"type": "delete_ai_action", "descriptionMatch": "string"},
        ]
    }, indent=2),
    "03_time_and_timezone.md": (
        "Handle RELATIVE vs ABSOLUTE time. Use Current UTC Time for relative;\n"
        "convert from USER_CONTEXT.timezone to UTC for absolute times.\n"
    ),
    "04_task_reply_rules.md": (
        "Show only undone tasks by default. Group by category (or tag), sort by due date then priority.\n"
    ),
    "05_memory_and_reminders.md": (
        "Use update/delete operations to manage existing memories and reminders.\n"
    ),
    "06_ai_scheduled_actions.md": (
        "Provide unique description for schedule_ai_action. Update/delete using descriptionMatch.\n"
    ),
    "07_safety_and_deletion.md": (
        "Seek confirmation before destructive actions. Do not invent state not present in context.\n"
    ),
    "08_language_and_style.md": (
        "Answer in the user's language when possible. Always end with a helpful question.\n"
    ),
    "09_context_contract.md": (
        "Expect explicit context blocks: USER_CONTEXT, MEMORY_CONTEXT, category_context, TASK_CONTEXT,\n"
        "REMINDERS_CONTEXT, AI_ACTIONS_CONTEXT, and CONVERSATION HISTORY.\n"
    ),
    "10_examples.md": (
        "(Examples omitted in fallback; rely on external files for golden examples.)\n"
    ),
    "99_footer_requirements.md": (
        "Always include an actions JSON block (can be []); reply times in user timezone but store UTC.\n"
    ),
}

# Default deterministic order of parts
_DEFAULT_ORDER: List[str] = [
    "00_header_persona.md",
    "01_response_format.md",
    "02_actions_schema.json",
    "03_time_and_timezone.md",
    "04_task_reply_rules.md",
    "05_memory_and_reminders.md",
    "06_ai_scheduled_actions.md",
    "07_safety_and_deletion.md",
    "08_language_and_style.md",
    "09_context_contract.md",
    "10_examples.md",
    "99_footer_requirements.md",
]


@dataclass
class PromptAssembler:
    """Load modular prompt parts and assemble a single system prompt.

    Parameters
    ----------
    root_dir : str | Path
        Root directory that contains prompt versions. Expected structure:
        root_dir / version / <parts>.
    version : str
        Version folder name, e.g., "v1".
    order : List[str]
        Ordered list of filenames to assemble. If None, use _DEFAULT_ORDER.
    locale : Optional[str]
        Reserved for future per-locale overrides. If provided, assembler will
        first try `root_dir/version/locales/{locale}/<part>` before the default.
    """

    root_dir: Path | str = "prompts"
    version: str = "v1"
    order: Optional[List[str]] = None
    locale: Optional[str] = None
    encoding: str = "utf-8"

    parts_cache: Dict[str, str] = field(default_factory=dict)

    def _resolve_paths(self, part: str) -> List[Path]:
        base = Path(self.root_dir) / self.version
        paths: List[Path] = []
        if self.locale:
            paths.append(base / "locales" / self.locale / part)
        paths.append(base / part)
        return paths

    def _load_part(self, part: str) -> str:
        # Cache hit
        if part in self.parts_cache:
            return self.parts_cache[part]

        # Try disk (locale first)
        for path in self._resolve_paths(part):
            if path.exists():
                try:
                    text = path.read_text(encoding=self.encoding)
                    self.parts_cache[part] = text
                    logger.debug("Loaded part %s from %s", part, path)
                    return text
                except Exception as e:
                    logger.warning("Failed reading %s: %s", path, e)

        # Fallback
        fallback = _DEFAULT_PARTS.get(part, f"[Missing part: {part}]\n")
        self.parts_cache[part] = fallback
        logger.info("Using fallback for part %s", part)
        return fallback

    def assemble_rules(self) -> str:
        """Concatenate all rule parts into a single system prompt string.

        Returns
        -------
        str
            The static rules (no runtime context appended).
        """
        order = self.order or _DEFAULT_ORDER
        chunks: List[str] = []
        for filename in order:
            content = self._load_part(filename).strip()
            # Annotate section boundaries for readability when debugging
            chunks.append(f"\n# >>> {filename} >>>\n{content}\n# <<< {filename} <<<\n")
        rules = "\n".join(chunks).strip() + "\n"
        return rules

    @staticmethod
    def _format_history(history: List[Dict[str, str]]) -> str:
        lines: List[str] = []
        for msg in history:
            role = (msg.get("role") or "").upper()
            content = msg.get("content") or ""
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    @staticmethod
    def _json(obj: Dict) -> str:
        return json.dumps(obj, ensure_ascii=False, indent=2)

    def build_full_prompt(
        self,
        *,
        user_context: Dict,
        memory_context: Dict,
        category_context: Dict,
        task_context: Dict,
        reminders_context: Dict,
        ai_actions_context: Dict,
        conversation_history: List[Dict[str, str]],
        current_utc_iso: Optional[str] = None,
    ) -> str:
        """Produce the final prompt string that will be sent to the model.

        Notes
        -----
        - This function does not insert dynamic data into the rules; the rules
          are assembled via `assemble_rules`. All dynamic values live in the
          context block below.
        - `current_utc_iso` is optional; if omitted, the model will rely on
          whatever the runtime or prior parts specify. Recommended to pass it.
        """
        rules = self.assemble_rules()

        context_lines = ["--- START OF CONTEXT DATA ---"]
        if current_utc_iso:
            context_lines.append(f"Current UTC Time: {current_utc_iso}")
        context_lines.append("USER_CONTEXT:\n" + self._json(user_context))
        context_lines.append("MEMORY_CONTEXT:\n" + self._json(memory_context))
        context_lines.append("category_context:\n" + self._json(category_context))
        context_lines.append("TASK_CONTEXT:\n" + self._json(task_context))
        context_lines.append("REMINDERS_CONTEXT:\n" + self._json(reminders_context))
        context_lines.append("AI_ACTIONS_CONTEXT:\n" + self._json(ai_actions_context))
        context_lines.append("--- END OF CONTEXT DATA ---")

        history_block = "CONVERSATION HISTORY:\n" + self._format_history(conversation_history) + "\n\nASSISTANT RESPONSE:"

        final = "\n\n".join([rules, "\n".join(context_lines), history_block]).strip()
        return final


# Optional: quick manual test (won't run in prod imports)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    assembler = PromptAssembler(root_dir="prompts", version="v1")
    demo = assembler.build_full_prompt(
        user_context={"timezone": "Asia/Jakarta"},
        memory_context={},
        category_context={},
        task_context={"tasks": []},
        reminders_context={},
        ai_actions_context={},
        conversation_history=[{"role": "user", "content": "Show my tasks"}],
        current_utc_iso="2025-08-17T11:00:00Z",
    )
    print(demo[:1000] + "\n...\n")
