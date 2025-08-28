#!/usr/bin/env python3
"""
Task Management Agent (Goal-Oriented with Strict JSON)

ENHANCED FEATURES:
- GOAL-ORIENTED: Intelligent context inference and parameter auto-completion
- FUZZY MATCHING: Handles typos and partial task title matches  
- SMART VALIDATION: Auto-resolves missing titleMatch from conversation history
- CONTEXT AWARE: Uses conversation history, task context, and AI brain memories
- STRICT JSON: Maintains perfect JSON formatting and validation
- TIME INTELLIGENCE: Parses relative times and timezone conversions

CORE CAPABILITIES:
- Robust JSON extraction from AI output with fenced code block support
- Intelligent parameter inference (titleMatch, reminder titles, confirmation flags)
- Fuzzy task matching with similarity scoring
- Multi-strategy context inference (conversation, recency, preferences)
- JSON schema validation and normalization with goal-oriented assistance
- Time parsing and UTC conversion for reminders
- Safe fallback responses when ambiguous or invalid data detected

Usage:
    agent = TaskManagementAgent(ai_model=your_ai_client)
    result = agent.process_command(user_command, user_context)
    # result -> {'response': str, 'actions': [ ... normalized and validated actions ]}

INTELLIGENCE MODES:
1. **Context Inference**: Automatically determines which task user is referencing
2. **Fuzzy Matching**: Finds best task matches even with typos (60% similarity threshold)  
3. **Smart Completion**: Auto-fills missing parameters using available context
4. **Intent Recognition**: Understands colloquial commands and converts to structured actions
5. **Time Intelligence**: Converts relative times ("in 30 mins") to UTC timestamps

This agent combines the intelligence of context-aware reasoning with the reliability
of strict JSON validation, ensuring both user-friendly interaction and system safety.
"""

import json
import logging
import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

ISO_UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class TaskManagementAgent:
    def __init__(self, ai_model=None):
        self.ai_model = ai_model
        # Define actual available functions from ai_tools.py with semantic mappings
        self.function_mappings = self._build_function_mappings()
    
    def _build_function_mappings(self) -> Dict[str, Dict[str, Any]]:
        """
        Build semantic mapping of user intents to actual available functions.
        This replaces hard-coded action validation with intelligent semantic matching.
        """
        return {
            # TASK MANAGEMENT - map to actual functions in ai_tools.py
            'create_task': {
                'function': 'create_task',
                'aliases': ['add_task', 'new_task', 'make_task', 'task_add', 'task_create'],
                'semantic_intents': ['add', 'create', 'make', 'new', 'insert', 'start'],
                'category': 'task_management'
            },
            'get_tasks': {
                'function': 'get_tasks', 
                'aliases': ['list_tasks', 'show_tasks', 'all_tasks', 'tasks_list', 'view_tasks', 'display_tasks'],
                'semantic_intents': ['list', 'show', 'get', 'all', 'view', 'display', 'find', 'search'],
                'category': 'task_management'
            },
            'update_task': {
                'function': 'update_task',
                'aliases': ['modify_task', 'edit_task', 'change_task', 'task_update', 'task_modify'],
                'semantic_intents': ['update', 'modify', 'edit', 'change', 'alter'],
                'category': 'task_management'
            },
            'delete_task': {
                'function': 'delete_task',
                'aliases': ['remove_task', 'task_delete', 'task_remove'],
                'semantic_intents': ['delete', 'remove', 'destroy', 'eliminate'],
                'category': 'task_management'
            },
            # REMINDER MANAGEMENT
            'create_reminder': {
                'function': 'create_reminder',
                'aliases': ['set_reminder', 'add_reminder', 'new_reminder', 'make_reminder'],
                'semantic_intents': ['set', 'create', 'add', 'make', 'schedule'],
                'category': 'reminder_management'
            },
            'get_reminders': {
                'function': 'get_reminders',
                'aliases': ['list_reminders', 'show_reminders', 'all_reminders', 'view_reminders'],
                'semantic_intents': ['list', 'show', 'get', 'all', 'view', 'display'],
                'category': 'reminder_management'
            },
            'update_reminder': {
                'function': 'update_reminder',
                'aliases': ['modify_reminder', 'edit_reminder', 'change_reminder'],
                'semantic_intents': ['update', 'modify', 'edit', 'change'],
                'category': 'reminder_management'
            },
            'delete_reminder': {
                'function': 'delete_reminder',
                'aliases': ['remove_reminder', 'cancel_reminder'],
                'semantic_intents': ['delete', 'remove', 'cancel', 'destroy'],
                'category': 'reminder_management'
            },
            
            # AI ACTIONS / SCHEDULING - for recurring and automated tasks
            'create_ai_action': {
                'function': 'create_ai_action',
                'aliases': ['schedule', 'recurring_task', 'automated_task', 'schedule_task', 'daily_task', 'recurring', 'automation', 'create_schedule', 'buat_schedule', 'jadwalkan'],
                'semantic_intents': ['schedule', 'recurring', 'daily', 'weekly', 'monthly', 'repeat', 'automate', 'automation', 'tiap', 'setiap', 'berkala', 'otomatis'],
                'category': 'ai_actions',
                'keywords': ['tiap hari', 'setiap hari', 'daily', 'every day', 'recurring', 'schedule', 'jadwal', 'automation', 'repeat']
            },
            'get_ai_actions': {
                'function': 'get_ai_actions',
                'aliases': ['list_ai_actions', 'show_schedules', 'list_schedules', 'show_ai_actions', 'view_schedules', 'automations'],
                'semantic_intents': ['list', 'show', 'get', 'view', 'display'],
                'category': 'ai_actions'
            },
            'update_ai_action': {
                'function': 'update_ai_action',
                'aliases': ['modify_ai_action', 'edit_schedule', 'change_schedule', 'update_schedule'],
                'semantic_intents': ['update', 'modify', 'edit', 'change'],
                'category': 'ai_actions'
            },
            'delete_ai_action': {
                'function': 'delete_ai_action',
                'aliases': ['remove_ai_action', 'cancel_schedule', 'delete_schedule', 'stop_automation'],
                'semantic_intents': ['delete', 'remove', 'cancel', 'stop'],
                'category': 'ai_actions'
            },
            
            # JOURNAL MANAGEMENT - Updated to match actual ai_tools.py functions
            'create_journal_entry': {
                'function': 'create_journal_entry',
                'aliases': ['add_journal', 'create_journal', 'new_journal', 'write_journal', 'journal_entry', 'diary_entry', 'note', 'write_note', 'save_note', 'record', 'log_entry', 'create_note', 'make_note', 'tulis_jurnal', 'catat'],
                'semantic_intents': ['write', 'create', 'add', 'new', 'journal', 'diary', 'note', 'record', 'log', 'save'],
                'category': 'journal_management'
            },
            'search_journal_entries': {
                'function': 'search_journal_entries', 
                'aliases': ['list_journal', 'get_journals', 'show_journals', 'my_journals', 'view_journals', 'list_notes', 'get_notes', 'show_notes', 'my_notes', 'view_notes', 'all_journals', 'all_notes', 'search_journals', 'find_journals'],
                'semantic_intents': ['list', 'show', 'get', 'all', 'view', 'display', 'my', 'search', 'find'],
                'category': 'journal_management'
            },
            'update_journal_entry': {
                'function': 'update_journal_entry',
                'aliases': ['update_journal', 'edit_journal', 'modify_journal', 'change_journal', 'edit_note', 'update_note', 'modify_note', 'change_note'],
                'semantic_intents': ['update', 'modify', 'edit', 'change', 'alter'],
                'category': 'journal_management'
            },
            'delete_journal_entry': {
                'function': 'delete_journal_entry',
                'aliases': ['delete_journal', 'remove_journal', 'delete_note', 'remove_note', 'hapus_jurnal'],
                'semantic_intents': ['delete', 'remove', 'destroy', 'eliminate'],
                'category': 'journal_management'
            },
            'get_journal_categories': {
                'function': 'get_journal_categories',
                'aliases': ['list_categories', 'show_categories', 'journal_categories', 'note_categories'],
                'semantic_intents': ['categories', 'list', 'show', 'get'],
                'category': 'journal_management'
            },
            
            # AI BRAIN MEMORY MANAGEMENT
            'add_ai_brain': {
                'function': 'add_ai_brain',
                'aliases': ['add_memory', 'save_memory', 'remember', 'learn', 'store_info', 'save_info', 'add_knowledge', 'save_knowledge', 'create_memory', 'store_knowledge', 'memorize', 'keep_in_mind', 'ingat', 'simpan_info', 'pelajari'],
                'semantic_intents': ['remember', 'learn', 'save', 'store', 'add', 'memorize', 'keep', 'knowledge'],
                'category': 'ai_brain_management'
            },
            'search_ai_brain': {
                'function': 'search_ai_brain',
                'aliases': ['search_memory', 'find_memory', 'recall', 'lookup', 'search_knowledge', 'find_knowledge', 'what_do_you_know', 'what_do_you_remember', 'cari_ingatan', 'temukan_info'],
                'semantic_intents': ['search', 'find', 'recall', 'lookup', 'what', 'remember', 'know'],
                'category': 'ai_brain_management'
            },
            'update_ai_brain': {
                'function': 'update_ai_brain',
                'aliases': ['update_memory', 'edit_memory', 'modify_memory', 'change_memory', 'update_knowledge', 'edit_knowledge', 'modify_knowledge'],
                'semantic_intents': ['update', 'modify', 'edit', 'change', 'alter'],
                'category': 'ai_brain_management'
            },
            'delete_ai_brain': {
                'function': 'delete_ai_brain',
                'aliases': ['delete_memory', 'remove_memory', 'forget', 'delete_knowledge', 'remove_knowledge', 'erase_memory', 'clear_memory', 'lupa', 'hapus_ingatan'],
                'semantic_intents': ['delete', 'remove', 'forget', 'erase', 'clear', 'destroy'],
                'category': 'ai_brain_management'
            }
            # Add more mappings for other functions as needed
        }
    
    def _semantic_function_match(self, user_action_type: str, scheduling_context: Optional[str] = None) -> Optional[str]:
        """
        Intelligently match user's action type to available functions using semantic analysis.
        Now includes scheduling context awareness to override incorrect AI decisions.
        Returns the correct function name or None if no match found.
        """
        user_action = user_action_type.lower().strip()
        
        # ENHANCED: Context-aware override for scheduling
        # If we detected scheduling intent but AI generated create_task, override it
        if (user_action in ['create_task', 'add_task', 'new_task', 'make_task'] and 
            scheduling_context in ['recurring_task', 'timed_task']):
            logger.info(f"SCHEDULING OVERRIDE: '{user_action}' → 'create_ai_action' (context: {scheduling_context})")
            return 'create_ai_action'
        
        # Special case: Check for scheduling/recurring keywords that should map to AI Actions
        if self._contains_scheduling_keywords(user_action):
            logger.info(f"Scheduling keywords detected: '{user_action}' → 'create_ai_action'")
            return 'create_ai_action'
        
        # First try exact match
        if user_action in self.function_mappings:
            return user_action
        
        # Try alias matching
        for func_name, func_info in self.function_mappings.items():
            if user_action in [alias.lower() for alias in func_info.get('aliases', [])]:
                return func_name
        
        # Semantic intent matching - check if user's intent matches function's semantic intents
        for func_name, func_info in self.function_mappings.items():
            semantic_intents = func_info.get('semantic_intents', [])
            
            # Check if user action contains any semantic intent keywords
            for intent in semantic_intents:
                if intent in user_action or user_action in intent:
                    # Additional context-based validation
                    if self._validate_semantic_context(user_action, func_info['category']):
                        logger.info(f"Semantic match: '{user_action}' → '{func_name}' (intent: {intent})")
                        return func_name
        
        logger.warning(f"No semantic match found for action type: '{user_action}'")
        return None
    
    def _contains_scheduling_keywords(self, text: str) -> bool:
        """
        Check if text contains keywords that indicate scheduling/recurring tasks.
        """
        scheduling_patterns = [
            # English scheduling keywords
            r'\b(schedule|recurring|daily|weekly|monthly|repeat|automation|every day|every week)\b',
            # Indonesian scheduling keywords  
            r'\b(jadwal|schedule|tiap hari|setiap hari|tiap|setiap|berkala|otomatis|buat schedule|jadwalkan)\b',
            # Time frequency patterns
            r'\b(every \d+|tiap \d+|setiap \d+)\b',
            # Action + frequency patterns
            r'\b(buat.*tiap|create.*daily|make.*weekly)\b'
        ]
        
        text_lower = text.lower()
        for pattern in scheduling_patterns:
            if re.search(pattern, text_lower):
                logger.info(f"Scheduling pattern found: '{pattern}' in '{text}'")
                return True
        return False
    
    def _validate_semantic_context(self, user_action: str, category: str) -> bool:
        """
        Validate that the semantic match makes sense in context.
        Prevents false positives like matching 'list_reminder' to 'create_task'.
        """
        user_lower = user_action.lower()
        
        # Category-specific validation
        if category == 'task_management':
            return any(keyword in user_lower for keyword in ['task', 'todo', 'do', 'work', 'job'])
        elif category == 'reminder_management':
            return any(keyword in user_lower for keyword in ['remind', 'alert', 'notify', 'notification'])
        elif category == 'ai_actions':
            # AI actions should match scheduling, automation, or recurring keywords
            return any(keyword in user_lower for keyword in ['schedule', 'recurring', 'daily', 'automation', 'repeat', 'tiap', 'setiap', 'berkala', 'jadwal', 'otomatis'])
        
        return True  # Default to accepting the match

    def process_command(self, clear_command: str, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a clear, explicit command into JSON actions with validation.
        Returns a dict: {'actions': <list of normalized actions>, 'processing_context': <dict>, 'status': <str>}
        
        Note: This method DOES NOT return user-facing responses. All user-facing responses 
        should be handled by AnsweringAgent. This method only returns structured data
        for processing and execution.
        """
        if not self.ai_model:
            logger.error("No AI model available for task management")
            return {
                'actions': [], 
                'processing_context': {'error': 'No AI model available'}, 
                'status': 'error'
            }

        # Pre-process command for scheduling detection
        scheduling_hint = self._detect_scheduling_intent(clear_command)
        if scheduling_hint:
            logger.info(f"Scheduling intent detected: {scheduling_hint}")

        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(clear_command, user_context, scheduling_hint)

        try:
            full_prompt = f"{system_prompt}\n\nHuman: {user_prompt}\n\nAssistant:"
            response = self.ai_model.generate_content(full_prompt)
            response_text = response.text.strip()

            conversational_text, raw_actions = self._parse_ai_response(response_text)

            # Validate and normalize actions
            valid, normalized_actions, issues = self._validate_and_normalize_actions(raw_actions, user_context, scheduling_hint)

            if not valid:
                # Return structured data about validation issues, not user-facing text
                return {
                    'actions': [],
                    'processing_context': {
                        'validation_issues': issues,
                        'raw_response': conversational_text,
                        'command': clear_command,
                        'scheduling_hint': scheduling_hint
                    },
                    'status': 'validation_failed'
                }

            # Return structured data with successful actions and processing context
            return {
                'actions': normalized_actions,
                'processing_context': {
                    'raw_response': conversational_text,
                    'command': clear_command,
                    'scheduling_hint': scheduling_hint,
                    'user_context': user_context
                },
                'status': 'success'
            }

        except Exception as e:
            logger.exception("Task management processing failed")
            return {
                'actions': [],
                'processing_context': {'error': str(e), 'command': clear_command},
                'status': 'error'
            }
    
    def _detect_scheduling_intent(self, command: str) -> Optional[str]:
        """
        Analyze the full command to detect if it's a scheduling/recurring task request.
        Returns scheduling hint or None.
        """
        command_lower = command.lower()
        
        # Strong scheduling indicators
        strong_patterns = [
            r'buat schedule',
            r'create schedule',
            r'jadwalkan',
            r'tiap hari',
            r'setiap hari',
            r'every day',
            r'daily',
            r'recurring',
            r'otomatis',
            r'automation'
        ]
        
        for pattern in strong_patterns:
            if re.search(pattern, command_lower):
                logger.info(f"Strong scheduling pattern found: '{pattern}' in command")
                return "recurring_task"
        
        # Medium scheduling indicators (with task creation context)
        if any(create_word in command_lower for create_word in ['buat', 'create', 'make', 'add']):
            medium_patterns = [
                r'\d+\s*(jam|hour|pukul)',  # time indicators
                r'tiap',
                r'setiap',
                r'berkala'
            ]
            
            for pattern in medium_patterns:
                if re.search(pattern, command_lower):
                    logger.info(f"Medium scheduling pattern found: '{pattern}' in command")
                    return "timed_task"
        
        return None

    # ---------------------- Prompt building ----------------------
    def _build_system_prompt(self) -> str:
        """Enhanced system prompt with goal-oriented workflow and smart context handling"""
        current_time = datetime.now(timezone.utc).isoformat()

        tools_and_constraints = """
AVAILABLE TOOLS & CAPABILITIES:
The system intelligently maps your action intents to available functions. Use natural language action types:

- TASK MANAGEMENT: 
  * Create: add_task, create_task, new_task, make_task
  * View: list_tasks, get_tasks, show_tasks, all_tasks, view_tasks  
  * Update: update_task, modify_task, edit_task, change_task
  * Delete: delete_task, remove_task
  
- REMINDER MANAGEMENT:
  * Create: set_reminder, create_reminder, add_reminder, make_reminder  
  * View: list_reminders, get_reminders, show_reminders, all_reminders
  * Update: update_reminder, modify_reminder, edit_reminder
  * Delete: delete_reminder, remove_reminder, cancel_reminder

- AI ACTIONS / SCHEDULING (for recurring and automated tasks):
  * Create: create_ai_action, schedule, recurring_task, automated_task, buat_schedule, jadwalkan
  * View: get_ai_actions, list_ai_actions, show_schedules, list_schedules, automations
  * Update: update_ai_action, modify_ai_action, edit_schedule, change_schedule
  * Delete: delete_ai_action, remove_ai_action, cancel_schedule, stop_automation

- JOURNAL MANAGEMENT (for notes, diary entries, personal records):
  * Create: add_journal, create_journal, new_journal, write_journal, journal_entry, diary_entry, note, write_note, save_note, record, log_entry, tulis_jurnal, catat
  * View: list_journal, get_journals, show_journals, my_journals, view_journals, list_notes, get_notes, show_notes, my_notes, view_notes, all_journals, all_notes
  * Update: update_journal, edit_journal, modify_journal, change_journal, edit_note, update_note, modify_note, change_note
  * Delete: delete_journal, remove_journal, delete_note, remove_note, hapus_jurnal

- AI BRAIN MANAGEMENT (for storing preferences, knowledge, memories):
  * Create: add_ai_brain, add_memory, save_memory, remember, learn, store_info, save_info, add_knowledge, save_knowledge, create_memory, store_knowledge, memorize, keep_in_mind, ingat, simpan_info, pelajari
  * Search: search_ai_brain, search_memory, find_memory, recall, lookup, search_knowledge, find_knowledge, what_do_you_know, what_do_you_remember, cari_ingatan, temukan_info
  * Update: update_ai_brain, update_memory, edit_memory, modify_memory, change_memory, update_knowledge, edit_knowledge, modify_knowledge
  * Delete: delete_ai_brain, delete_memory, remove_memory, forget, delete_knowledge, remove_knowledge, erase_memory, clear_memory, lupa, hapus_ingatan

SMART SEMANTIC MATCHING:
- The system will automatically map similar intents (e.g. "all_task" → get_tasks)
- Use natural language - don't worry about exact function names
- Context-aware matching prevents cross-category errors
- SCHEDULING KEYWORDS: "schedule", "tiap hari", "setiap hari", "daily", "recurring", "automation" → use AI Actions

IMPORTANT: For recurring/scheduled tasks, use create_ai_action instead of create_task!
Examples:
- "buat schedule buang sampah tiap hari jam 9" → create_ai_action
- "daily reminder to exercise" → create_ai_action  
- "automate weekly report" → create_ai_action

DATABASE ENUM CONSTRAINTS:

FROM TABLE tasks - status field:
ALLOWED VALUES: ['todo', 'doing', 'done', 'Todo', 'Doing', 'Done', 'pending', 'Pending', 'completed', 'Completed']

FROM TABLE tasks - priority field:
ALLOWED VALUES: ['low', 'medium', 'high']

FROM TABLE ai_brain_memories - brain_data_type field (AI_BRAIN ENUM):
ALLOWED VALUES: ['communication_style']
- 'communication_style': ALL communication preferences combined into one intelligent entry using JSONB storage
  * Language: Indonesian, English, Japanese, etc.
  * Tone: Professional, casual, friendly, formal
  * Style: Use emojis, bullet points, detailed responses
  * Format: Conversational, structured, technical
  * SMART MERGING: New preferences intelligently merge with existing ones
  Examples: "Speak Indonesian and use emojis", "Professional English with detailed responses", "Casual tone with bullet points"

FROM TABLE ai_actions - action_type field:
ALLOWED VALUES: ['summarize_tasks', 'create_recurring_task', 'send_reminder', 'cleanup_completed_tasks', 'generate_daily_summary', 'backup_data']

FROM TABLE ai_actions - status field:
ALLOWED VALUES: ['active', 'inactive', 'completed', 'failed']

FROM TABLE journal_entries - entry_type field:
ALLOWED VALUES: ['free_form', 'structured', 'reflection', 'planning']
"""

        system = f"""
You are a GOAL-ORIENTED Smart Task JSON generator with SEMANTIC FUNCTION MATCHING. You combine intelligent context inference with strict JSON formatting and smart action mapping.

== CORE MISSION ==
Convert user commands into valid JSON actions by:
1. INTELLIGENTLY interpreting ambiguous or incomplete commands using available context
2. AUTOMATICALLY mapping user action intents to correct functions (e.g. "all_task" → "get_tasks", "add task" → "create_task")  
3. RESOLVING missing parameters (like titleMatch) from conversation history and task context
4. INFERRING user intent even when commands contain typos or use alternative terminology
5. ENSURING all output follows strict JSON formatting rules

== INTELLIGENCE & CONTEXT FEATURES ==
- **Pure AI Semantic Inference**: Use natural language understanding to interpret context across all languages
- **Smart Function Mapping**: Automatically map user action types to available functions using semantic similarity
- **Smart Context Analysis**: Leverage USER_CONTEXT, TASK_CONTEXT, CONVERSATION_HISTORY, and AI_BRAIN_CONTEXT semantically
- **Fuzzy Matching**: Handle typos in task titles by finding closest matches in existing tasks
- **Auto-Parameter Resolution**: When user says "mark it done" or "update that task", infer which task through semantic analysis
- **Intent Recognition**: Understand natural language commands across languages → convert to structured actions
- **Time Intelligence**: Parse relative times ("in 30 mins", "tonight", "tomorrow morning") into UTC timestamps
- **Missing Data Completion**: Use semantic context to complete partial commands instead of requesting clarification

== SEMANTIC FUNCTION MAPPING EXAMPLES ==
- "add task" / "create task" / "new task" → create_task
- "all tasks" / "list task" / "show tasks" → get_tasks
- "update task" / "modify task" / "edit task" → update_task
- "delete task" / "remove task" → delete_task
- "set reminder" / "create reminder" → create_reminder
- "write note" / "diary entry" / "journal entry" / "save note" / "tulis jurnal" → add_journal
- "my notes" / "show journals" / "list notes" → list_journal
- "remember this" / "save info" / "learn this" / "ingat" → add_ai_brain
- "what do you know" / "recall" / "search memory" → search_ai_brain
- "forget this" / "delete memory" / "lupa" → delete_ai_brain
- "schedule daily" / "recurring task" / "jadwalkan" → create_ai_action

== ACTION TYPE USAGE GUIDELINES ==
- For storing personal information, memories, preferences: use add_ai_brain
- For notes, diary entries, journaling: use add_journal  
- For recurring/scheduled tasks: use create_ai_action
- For simple one-time tasks: use create_task
- For reminders with specific times: use create_reminder

== STRICT JSON OUTPUT RULES ==
- ALWAYS output a conversational reply followed by a fenced ```json``` block containing only the JSON object
- The JSON must be valid and parsable by standard JSON parsers
- Use single top-level key "actions" containing an array of action objects
- STRICTLY follow the enum constraints listed below. Do not use values outside the allowed enums
- Times for reminders must be ISO 8601 UTC strings (YYYY-MM-DDTHH:MM:SSZ)
- Action types will be automatically mapped to correct functions - use natural language

== REQUIRED FIELDS BY ACTION TYPE ==
- add_journal: MUST include both 'title' AND 'content' (content cannot be empty)
- add_ai_brain: MUST include both 'title' AND 'content' (content cannot be empty)
- create_task: MUST include 'title' (content can be optional)
- create_reminder: MUST include 'title' AND 'reminderTime' or 'remind_at'

== JSON FORMAT TEMPLATE ==
```json
{{
  "actions": [
    {{
      "type": "<natural_language_action_intent>",
      "required_field": "value",
      "optional_field": "value"
    }}
  ]
}}
```

== EXAMPLE JSON OUTPUTS ==
For "write a note about today's meeting":
```json
{{
  "actions": [
    {{
      "type": "add_journal",
      "title": "Today's meeting", 
      "content": "Notes about today's meeting discussion",
      "entry_type": "free_form"
    }}
  ]
}}
```

For "always answer in japanese" or "respond in english":
```json
{{
  "actions": [
    {{
      "type": "add_ai_brain",
      "title": "Language preference", 
      "content": "User prefers responses in Japanese language",
      "brain_data_type": "communication_style"
    }}
  ]
}}
```

For "remember I prefer email and use emojis":
```json
{{
  "actions": [
    {{
      "type": "add_ai_brain",
      "title": "Communication preferences",
      "content": "User prefers email communication and wants responses with emojis",
      "brain_data_type": "communication_style"
    }}
  ]
}}
```

For "rumah dina di bekasi" (Dina's house in Bekasi):
```json
{{
  "actions": [
    {{
      "type": "add_journal",
      "title": "Dina's house in Bekasi",
      "content": "Information or notes about Dina's house located in Bekasi",
      "entry_type": "free_form"
    }}
  ]
}}
```

== DECISION HIERARCHY ==
1. **First**: Use semantic matching to map user action types to available functions
2. **Second**: Use intelligence to resolve ambiguity and complete missing information
3. **Third**: If critical data is still missing after inference attempts, leave actions empty and ask for clarification
4. **Always**: Maintain strict JSON formatting regardless of complexity

== CONTEXT USAGE EXAMPLES ==
- Command: "mark it done" → Use TASK_CONTEXT to find most recently mentioned/created task
- Command: "remind me about the meeting" → Search CONVERSATION_HISTORY and TASK_CONTEXT for meeting-related tasks
- Command: "update lunch task" → Use fuzzy matching to find task with "lunch" in title, even if actual title is "Lunch with Sarah"
- Command: "set reminder for 6pm" → Calculate UTC time from user timezone in USER_CONTEXT

{tools_and_constraints}

CONTEXT: Current UTC time: {current_time}
**ALWAYS prioritize semantic function mapping and intelligent inference over requesting clarification while maintaining JSON format perfection.**
"""
        return system

    def _build_user_prompt(self, clear_command: str, user_context: Optional[Dict[str, Any]] = None, scheduling_hint: Optional[str] = None) -> str:
        parts = [f'CLEAR COMMAND: "{clear_command}"']
        
        # Add scheduling hint if detected
        if scheduling_hint:
            parts.append(f"SCHEDULING_HINT: {scheduling_hint} (Consider using create_ai_action for recurring/scheduled tasks)")
        
        if user_context:
            if user_context.get('user_info'):
                parts.append("USER_CONTEXT: " + json.dumps(user_context['user_info']))
            if user_context.get('tasks'):
                parts.append("TASK_CONTEXT: " + json.dumps(user_context['tasks']))
            if user_context.get('ai_brain'):
                parts.append("AI_BRAIN_CONTEXT: " + json.dumps(user_context['ai_brain']))
            if user_context.get('conversation_history'):
                parts.append("CONVERSATION_HISTORY: " + json.dumps(user_context['conversation_history']))
        else:
            parts.append("No additional context available.")

        return "\n\n".join(parts)

    # ---------------------- AI response parsing ----------------------
    def _parse_ai_response(self, response_text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Extract conversational text (before JSON block) and the actions array.
        If JSON cannot be extracted, return conversational_text and empty actions list.
        """
        conversational = response_text
        json_obj = None

        # First try fenced ```json blocks
        if '```json' in response_text:
            parts = response_text.split('```json', 1)
            conversational = parts[0].strip()
            remainder = parts[1]
            if '```' in remainder:
                json_text = remainder.split('```', 1)[0].strip()
                try:
                    json_obj = json.loads(json_text)
                except json.JSONDecodeError:
                    logger.warning('Failed to parse JSON inside ```json block')
                    json_obj = None
        # Fallback: try to extract first JSON object-like substring
        if json_obj is None:
            # attempt to find first `{` and match braces
            extracted = self._extract_first_json_object(response_text)
            if extracted:
                try:
                    json_obj = json.loads(extracted)
                    # conversational should be text before the extracted json
                    idx = response_text.find(extracted)
                    conversational = response_text[:idx].strip()
                except Exception:
                    logger.warning('Failed to parse extracted JSON substring')
                    json_obj = None

        actions = []
        if isinstance(json_obj, dict) and 'actions' in json_obj and isinstance(json_obj['actions'], list):
            actions = json_obj['actions']
        else:
            # No valid actions found — keep actions empty
            actions = []

        return conversational if conversational else "I've processed your request.", actions

    def _extract_first_json_object(self, text: str) -> Optional[str]:
        """Find the first balanced JSON object in text by brace-matching."""
        start = text.find('{')
        if start == -1:
            return None
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if ch == '"' and not escape:
                in_string = not in_string
            if ch == '\\' and not escape:
                escape = True
                continue
            else:
                escape = False
            if not in_string:
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        return text[start:i+1]
        return None

    # ---------------------- Validation & normalization ----------------------
    def _validate_and_normalize_actions(self, actions: List[Dict[str, Any]], user_context: Optional[Dict[str, Any]], scheduling_hint: Optional[str] = None) -> Tuple[bool, List[Dict[str, Any]], Dict[str, Any]]:
        """
        GOAL-ORIENTED validation with intelligent parameter completion and fuzzy matching.
        Returns (valid, normalized_actions, issues)
        issues: {'errors': [...], 'ambiguous': [{'action_index': int, 'candidates': [...]}, ...]}
        """
        issues = {'errors': [], 'ambiguous': []}
        normalized = []
        task_titles = []
        tasks_dict = {}
        if user_context and user_context.get('tasks'):
            tasks_dict = {t.get('title', ''): t for t in user_context['tasks'] if t.get('title')}
            task_titles = list(tasks_dict.keys())

        for idx, action in enumerate(actions):
            if not isinstance(action, dict):
                issues['errors'].append(f"action[{idx}] is not an object")
                continue
            
            original_action_type = action.get('type')
            if not original_action_type:
                issues['errors'].append(f"action[{idx}] missing required 'type' field")
                continue
            
            # Use semantic matching to find the correct function
            matched_function = self._semantic_function_match(original_action_type, scheduling_hint)
            if not matched_function:
                issues['errors'].append(f"action[{idx}].type='{original_action_type}' - no matching function found")
                continue

            # Clone action to normalized version we can edit
            na = dict(action)
            # Update the action type to use the correctly matched function name
            na['type'] = matched_function
            
            # Log the mapping for transparency
            if original_action_type != matched_function:
                logger.info(f"Mapped action type: '{original_action_type}' → '{matched_function}'")

            # == GOAL-ORIENTED INTELLIGENCE: Auto-complete missing parameters ==
            
            # For task operations that need titleMatch, try to intelligently infer it
            if matched_function in ('update_task', 'delete_task'):
                if not na.get('titleMatch') and not na.get('task_id'):
                    # Try to infer titleMatch from context
                    inferred_title = self._infer_task_from_context(user_context)
                    if inferred_title:
                        # Try fuzzy matching against existing tasks
                        best_match = self._find_best_task_match(inferred_title, task_titles)
                        if best_match:
                            na['titleMatch'] = best_match
                            logger.info(f"Auto-inferred titleMatch='{best_match}' from context for {matched_function}")
                        else:
                            na['titleMatch'] = inferred_title
                            logger.info(f"Using inferred title='{inferred_title}' for {matched_function}")
                    else:
                        issues['errors'].append(f"action[{idx}] {matched_function} requires 'titleMatch' or 'task_id' - could not infer from context")
                        continue
                else:
                    # User provided titleMatch - apply fuzzy matching to improve accuracy
                    provided_title = na.get('titleMatch')
                    if provided_title:
                        best_match = self._find_best_task_match(provided_title, task_titles)
                        if best_match and best_match != provided_title:
                            na['titleMatch'] = best_match
                            logger.info(f"Fuzzy-matched titleMatch '{provided_title}' → '{best_match}' for {matched_function}")
            
            # For reminders that reference tasks, try to link them intelligently
            if matched_function in ('create_reminder', 'update_reminder'):
                # Try multiple possible field names for the reminder time
                rt = (na.get('reminderTime') or na.get('remind_at') or 
                     na.get('time') or na.get('when') or 
                     na.get('reminder_time') or na.get('at') or
                     na.get('schedule_at'))
                     
                if not rt:
                    issues['errors'].append(f"action[{idx}] {matched_function} requires 'reminderTime' or 'remind_at' → Please specify when to be reminded (e.g., 'at 8am', 'tomorrow at 6pm', '2025-01-20T18:00:00Z')")
                    continue
                    
                parsed = self._normalize_time_field(rt, user_context)
                if not parsed:
                    issues['errors'].append(f"action[{idx}] {matched_function} has invalid or unparsable reminderTime: '{rt}'")
                else:
                    na['remind_at'] = parsed  # Use the actual parameter name from ai_tools.py
                    # Remove the old field if it was using different name
                    if 'reminderTime' in na:
                        del na['reminderTime']
                    
                # If no title provided, try to infer based on context
                if not na.get('title') and user_context:
                    inferred_title = self._infer_task_from_context(user_context)
                    if inferred_title:
                        na['title'] = f"Reminder about {inferred_title}"
                        logger.info(f"Auto-generated reminder title: '{na['title']}'")
            
            # Basic validations with goal-oriented assistance
            if matched_function == 'create_task':
                if not na.get('title'):
                    issues['errors'].append(f"action[{idx}] create_task missing 'title'")
                    
            if matched_function == 'delete_task':
                # Be more flexible about confirmation - infer intent
                if not na.get('confirm', False):
                    # Check if user's original command had strong delete intent
                    if user_context and user_context.get('conversation_history'):
                        recent_messages = user_context['conversation_history'][-2:] if user_context['conversation_history'] else []
                        has_strong_intent = any(
                            word in str(msg).lower() 
                            for msg in recent_messages 
                            for word in ['delete', 'remove', 'cancel', 'drop', 'eliminate']
                        )
                        if has_strong_intent:
                            na['confirm'] = True
                            logger.info(f"Auto-confirmed delete based on strong intent keywords")
                        else:
                            issues['errors'].append(f"action[{idx}] delete_task requires explicit confirmation")

            # Additional goal-oriented enhancements can be added here
            normalized.append(na)

        # If any ambiguous or errors exist, we consider it invalid
        if issues['errors'] or issues['ambiguous']:
            return False, [], issues

        return True, normalized, issues

    def _find_best_task_match(self, input_title: str, available_titles: List[str]) -> Optional[str]:
        """
        GOAL-ORIENTED fuzzy matching to find the best task title match.
        Handles typos, partial matches, and case-insensitive matching.
        Returns the best matching title or None if no good match found.
        """
        if not input_title or not available_titles:
            return None
            
        input_lower = input_title.lower().strip()
        
        # Exact match (case-insensitive)
        for title in available_titles:
            if title.lower() == input_lower:
                return title
                
        # Partial match - input is contained in title
        partial_matches = []
        for title in available_titles:
            if input_lower in title.lower():
                partial_matches.append(title)
        
        # If only one partial match, use it
        if len(partial_matches) == 1:
            return partial_matches[0]
        elif len(partial_matches) > 1:
            # Return the shortest match (most specific)
            return min(partial_matches, key=len)
        
        # Reverse partial match - title is contained in input
        reverse_matches = []
        for title in available_titles:
            if title.lower() in input_lower:
                reverse_matches.append(title)
                
        if len(reverse_matches) == 1:
            return reverse_matches[0]
        elif len(reverse_matches) > 1:
            # Return the longest match (most complete)
            return max(reverse_matches, key=len)
        
        # Simple character-based similarity for typos
        best_match = None
        best_score = 0
        
        for title in available_titles:
            # Calculate simple similarity based on common characters
            similarity = self._calculate_similarity(input_lower, title.lower())
            if similarity > best_score and similarity >= 0.6:  # 60% similarity threshold
                best_score = similarity
                best_match = title
        
        return best_match
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate simple character-based similarity between two strings.
        Returns a value between 0.0 and 1.0.
        """
        if not str1 or not str2:
            return 0.0
            
        # Remove spaces and special characters for comparison
        clean1 = ''.join(c for c in str1 if c.isalnum()).lower()
        clean2 = ''.join(c for c in str2 if c.isalnum()).lower()
        
        if not clean1 or not clean2:
            return 0.0
            
        if clean1 == clean2:
            return 1.0
            
        # Count common characters
        common_chars = 0
        str1_chars = list(clean1)
        str2_chars = list(clean2)
        
        for char in str1_chars:
            if char in str2_chars:
                str2_chars.remove(char)  # Remove to avoid double counting
                common_chars += 1
        
        # Calculate similarity based on common characters vs total characters
        max_len = max(len(clean1), len(clean2))
        return common_chars / max_len if max_len > 0 else 0.0

    def _infer_task_from_context(self, user_context: Optional[Dict[str, Any]]) -> Optional[str]:
        """
        PURE AI-SEMANTIC context inference: Let the AI language model naturally infer 
        what task the user is referring to from conversation history and context.
        Returns the most likely task title or None if cannot infer.
        """
        if not user_context:
            return None
            
        # Strategy 1: Use conversation history for semantic understanding
        conversation_history = user_context.get('conversation_history', [])
        if conversation_history:
            # Get recent conversation context for AI to analyze semantically
            recent_messages = conversation_history[-3:] if len(conversation_history) >= 3 else conversation_history
            
            # Let the AI infer from conversation - we'll pass this context up to the AI model
            # The AI model will handle semantic understanding across all languages
            if recent_messages:
                logger.info("Found conversation context for AI semantic inference")
                # We don't do keyword matching here - let the AI handle it semantically
        
        # Strategy 2: Find most recently modified incomplete task (simple heuristic)
        tasks = user_context.get('tasks', [])
        if tasks:
            try:
                # Simple sorting without complex scoring - let AI handle semantic matching
                def get_task_timestamp(task):
                    updated = task.get('updated_at', '')
                    created = task.get('created_at', '')
                    timestamps = [t for t in [updated, created] if t]
                    return max(timestamps) if timestamps else ''
                
                sorted_tasks = sorted(tasks, key=get_task_timestamp, reverse=True)
                
                # Prioritize incomplete tasks
                incomplete_tasks = [t for t in sorted_tasks if t.get('status', '').lower() not in ['done', 'completed']]
                
                if incomplete_tasks:
                    most_recent_task = incomplete_tasks[0]
                    title = most_recent_task.get('title', '')
                    if title:
                        logger.info(f"Found most recent incomplete task '{title}' for AI to consider")
                        return title
                elif sorted_tasks:
                    most_recent_task = sorted_tasks[0]
                    title = most_recent_task.get('title', '')
                    if title:
                        logger.info(f"Found most recent task '{title}' for AI to consider")
                        return title
                        
            except Exception as e:
                logger.warning(f"Error in task sorting: {e}")
                if tasks and tasks[0].get('title'):
                    return tasks[0]['title']
        
        # Strategy 3: Let AI handle any brain context semantically
        ai_brain = user_context.get('ai_brain', [])
        if ai_brain:
            # Don't process brain context here - let the AI model handle it semantically
            logger.info("Found AI brain context for semantic inference")
        
        return None

    def _normalize_time_field(self, time_value: str, user_context: Optional[Dict[str, Any]]) -> Optional[str]:
        """
        Simple time normalization - just use AI to convert time expressions to UTC.
        
        SIMPLIFIED ARCHITECTURE: 
        - AI handles all time parsing with user timezone context
        - No complex parsing modules or validation layers
        - Direct AI call with current time and timezone context
        """
        if not self.ai_model:
            return None
            
        # Get current UTC time as reference
        current_utc = datetime.now(timezone.utc).strftime(ISO_UTC_FORMAT)
        
        # Extract user timezone context (default GMT+7)
        user_timezone = "GMT+7"
        if user_context:
            # Check user_info structure first (as per chat.py _build_user_context)
            if 'user_info' in user_context and isinstance(user_context['user_info'], dict):
                user_timezone = user_context['user_info'].get('timezone', 'GMT+7')
            # Fallback to direct timezone field
            elif 'timezone' in user_context:
                user_timezone = user_context['timezone']
            # Legacy user_timezone field
            elif 'user_timezone' in user_context and isinstance(user_context['user_timezone'], dict):
                user_timezone = user_context['user_timezone'].get('timezone', 'GMT+7')
        
        # Simple AI prompt with timezone context
        prompt = f"""Convert this time expression to UTC format (YYYY-MM-DDTHH:MM:SSZ).

CURRENT UTC TIME: {current_utc}
USER TIMEZONE: {user_timezone}
TIME EXPRESSION: "{time_value}"

CRITICAL TIMEZONE RULES:
- User's times are ALWAYS in their local timezone ({user_timezone})
- When user says "jam 8" or "8am" or "8 tomorrow", they mean 8:00 AM in {user_timezone}
- You MUST subtract timezone offset to get UTC time
- {user_timezone} is 7 hours ahead of UTC, so subtract 7 hours from their local time
- Examples for {user_timezone}:
  * User says "8am" → 8:00 AM {user_timezone} → 1:00 AM UTC → 2025-XX-XXTX1:00:00Z
  * User says "jam 11 malam" → 11:00 PM {user_timezone} → 4:00 PM UTC → 2025-XX-XXTX16:00:00Z  
  * User says "7pm tomorrow" → 7:00 PM {user_timezone} → 12:00 PM UTC → 2025-XX-XXTX12:00:00Z
- For relative times like "in 2 hours", calculate from current UTC time

Return ONLY the UTC timestamp or "ERROR" if cannot parse."""

        try:
            response = self.ai_model.generate_content(prompt)
            result = response.text.strip()
            
            # Clean up the result (extract only the timestamp)
            import re
            timestamp_match = re.search(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', result)
            if timestamp_match:
                result = timestamp_match.group(0)
            
            # Validate the result
            if result == "ERROR" or not result or not result.endswith('Z'):
                logger.warning(f"AI could not parse time: '{time_value}' -> '{result}'")
                return None
                
            # Verify it's a valid UTC timestamp
            try:
                datetime.strptime(result, ISO_UTC_FORMAT)
                logger.info(f"Successfully parsed '{time_value}' -> '{result}'")
                return result
            except ValueError as e:
                logger.warning(f"Invalid timestamp format from AI: '{result}' - {e}")
                return None
                
        except Exception as e:
            logger.error(f"AI time parsing failed for '{time_value}': {e}")
            return None

    # ---------------------- Clarification building ----------------------
    def _build_clarification_response(self, conversational_text: str, issues: Dict[str, Any]) -> str:
        """Build detailed clarification response with specific validation guidance"""
        lines = []
        if conversational_text:
            lines.append(conversational_text)
            
        # Handle ambiguous matches first
        if issues.get('ambiguous'):
            lines.append("\n🔍 **Ambiguous References Found:**")
            for amb in issues['ambiguous']:
                orig = amb.get('original')
                cands = amb.get('candidates', [])
                if cands:
                    lines.append(f"• Multiple matches for '{orig}': {', '.join(cands[:3])}")
                    lines.append(f"  Which specific task did you mean?")
                else:
                    lines.append(f"• No task found matching '{orig}'")
                    lines.append(f"  Please provide the exact task title or check your task list.")
                    
        # Handle validation errors with specific guidance
        if issues.get('errors'):
            lines.append("\n❌ **Validation Issues:**")
            for error in issues['errors']:
                lines.append(f"• {error}")
                
                # Provide specific guidance based on error type
                if "missing 'title'" in error:
                    lines.append("  → Please provide a task title (e.g., 'Buy groceries')")
                elif "requires 'reminderTime'" in error:
                    lines.append("  → Please specify when to remind you (e.g., '6pm', 'tomorrow at 9am', '2025-01-20T18:00:00Z')")
                elif "invalid or unparsable reminderTime" in error:
                    lines.append("  → Use formats like: '6pm', 'in 30 minutes', 'tomorrow at 9am', or ISO format")
                elif "not allowed" in error:
                    lines.append("  → This action type is not supported. Try: add_task, update_task, list_tasks, set_reminder")
                elif "requires explicit 'confirm'" in error:
                    lines.append("  → Deleting tasks requires confirmation. Please confirm you want to delete this task.")
                    
        # Add helpful examples if there are validation errors
        if issues.get('errors'):
            lines.append("\n💡 **Examples of valid requests:**")
            lines.append("• 'Add task: Buy milk' → Creates a new task")
            lines.append("• 'Update my lunch task to dinner' → Updates existing task")
            lines.append("• 'Remind me about the meeting at 3pm' → Sets reminder")
            lines.append("• 'List my tasks' → Shows all tasks")
            
        # Ensure response ends with a question
        result = "\n".join(lines).strip()
        if not result.endswith('?'):
            if issues.get('ambiguous'):
                result += "\n\nWhich specific item would you like me to work with?"
            else:
                result += "\n\nCould you please clarify or provide the missing information?"
                
        return result


# ---------------------- End of agent ----------------------