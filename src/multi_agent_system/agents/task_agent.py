# File: task_agent.py
# This is the correct home for your TaskAgent class.

import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)

# This is the standard ISO 8601 UTC format we will use for all timestamps.
ISO_UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

class TaskAgent:
    def __init__(self, ai_model=None, supabase=None, api_key_manager=None):
        self.ai_model = ai_model
        self.supabase = supabase
        self.api_key_manager = api_key_manager
        self.last_api_call = 0
        self.rate_limit_seconds = 2
        self.category_cache = {}
        self.base_categories = ['work', 'personal', 'health', 'finance', 'home', 'learning', 'shopping']

    def process_command(self, user_command: str, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main entry point. Processes a command, determines intent, and returns executable JSON action(s).
        """
        if not self.ai_model:
            return self._error_response("Task Agent is not properly initialized.")

        try:
            user_id = user_context.get('user_info', {}).get('user_id')
            if not user_id: return self._error_response("User ID is required for task operations.")

            intent_details = self._determine_intent(user_command)
            intent = intent_details.get('intent', 'create_task')
            
            if intent == 'create_task':
                return self._handle_create_task(user_command, user_id, intent_details, user_context)
            elif intent == 'list_tasks':
                return self._handle_list_tasks(user_command, user_id, intent_details, user_context)
            elif intent == 'update_task':
                return self._handle_task_modification(user_command, user_id, intent_details, 'update', user_context)
            elif intent == 'complete_task':
                return self._handle_task_modification(user_command, user_id, intent_details, 'complete', user_context)
            elif intent == 'delete_task':
                return self._handle_task_modification(user_command, user_id, intent_details, 'delete', user_context)
            elif intent == 'batch_operation':
                return self._handle_batch_operation(user_id, intent_details, user_context)
            else:
                return self._handle_create_task(user_command, user_id, intent_details, user_context)
                
        except Exception as e:
            logger.exception(f"Task Agent processing failed: {e}")
            return self._error_response("An error occurred while processing your task request.")

    def _handle_create_task(self, user_command: str, user_id: str, intent_details: Dict, user_context: Dict) -> Dict[str, Any]:
        title = intent_details.get('title', user_command)
        description = intent_details.get('description', '')
        notes = intent_details.get('notes', '')
        due_date_str = intent_details.get('due_date')

        analysis = self._analyze_task_details(
            title, f"{description}\n{notes}", user_id, intent_details, due_date_str, user_context
        )
        
        action = {'type': 'create_task', 'title': title, 'description': description, 'notes': notes, 'due_date': analysis.get('normalized_due_date'), 'category': analysis['category'], 'priority': analysis['priority']}
        
        return {'success': True, 'actions': [action], 'response': f"Okay, I've added the task '{title}' to your '{analysis['category']}' category."}
        
    def _handle_list_tasks(self, user_command: str, user_id: str, intent_details: Dict, user_context: Dict) -> Dict[str, Any]:
        filters = intent_details.get('filters', {})
        filter_description = filters.get('description')
        status_filter = filters.get('status', 'todo') # Default to 'todo' if not specified

        if filter_description:
            # AI-powered smart search branch
            task_ids_to_list = self._find_matching_tasks_for_batch_op(filter_description, user_id, user_context, status=status_filter)

            if not task_ids_to_list:
                return {'success': True, 'actions': [], 'response': f"I couldn't find any {status_filter} tasks matching your description."}

            list_action = {'type': 'get_tasks', 'task_ids': task_ids_to_list, 'order_by': 'due_date', 'ascending': True}
            response = f"Here are the {status_filter} tasks I found related to your request..."
        else:
            # Default behavior: list recent tasks with the specified or default status
            list_action = {'type': 'get_tasks', 'status': status_filter, 'limit': 15, 'order_by': 'due_date', 'ascending': True}
            response = f"Let me get your current {status_filter} tasks..."

        stats_action = {'type': 'get_task_stats'}
        return {'success': True, 'actions': [list_action, stats_action], 'response': response}

    def _handle_task_modification(self, user_command: str, user_id: str, intent_details: Dict, mode: str, user_context: Dict) -> Dict[str, Any]:
        title_match = intent_details.get('title_match')
        if not title_match: return self._error_response(f"Which task would you like to {mode}?")

        search_result = self._find_best_task_match(title_match, user_id)
        if not search_result['found']: return self._error_response(f"I couldn't find an active task that matches '{title_match}'.")
        if search_result.get('ambiguous'):
            options = "', '".join(search_result['options'])
            return {'success': True, 'actions': [], 'response': f"I found a few similar tasks. Which one did you mean?\n- '{options}'", 'requires_clarification': True}
        
        matched_task = search_result['task']
        
        if not matched_task:
            return self._error_response(f"I found a match for '{title_match}', but there was an internal error retrieving its details.")

        action, response = None, ""
        
        if mode == 'complete':
            action = {'type': 'update_task', 'task_id': matched_task['id'], 'patch': {'status': 'done'}}
            response = f"Great job! Marking '{matched_task['title']}' as complete."
        elif mode == 'delete':
            action = {'type': 'delete_task', 'task_id': matched_task['id']}
            response = f"Okay, deleting '{matched_task['title']}'."
        elif mode == 'update':
            patch = intent_details.get('patch', {})
            if not patch: return self._error_response("What change would you like to make to the task?")
            
            if 'due_date' in patch and isinstance(patch['due_date'], str):
                patch['due_date'] = self._normalize_time_string(patch['due_date'], user_context) or patch['due_date']
            
            action = {'type': 'update_task', 'task_id': matched_task['id'], 'patch': patch}
            response = f"I'll update the task '{matched_task['title']}'."
        else:
            return self._error_response("Invalid modification action.")

        return {'success': True, 'actions': [action], 'response': response}
    
    def _handle_batch_operation(self, user_id: str, intent_details: Dict, user_context: Dict) -> Dict[str, Any]:
        operation = intent_details.get('operation')
        if not operation:
            return self._error_response("I'm not sure which action to perform on the tasks.")

        if operation == 'create':
            tasks_to_create = intent_details.get('tasks_to_create', [])
            if not tasks_to_create: return self._error_response("You asked to add multiple tasks, but didn't specify which ones.")
            
            analyzed_details = self._analyze_batch_task_details(tasks_to_create, user_id, user_context)
            if len(analyzed_details) != len(tasks_to_create): return self._error_response("I had trouble analyzing the batch of tasks.")

            actions = [
                {'type': 'create_task', 'title': task.get('title'), 'description': task.get('description', ''), 'notes': task.get('notes', ''), 'due_date': analysis.get('normalized_due_date'), 'category': analysis.get('category', 'general'), 'priority': analysis.get('priority', 'medium')}
                for task, analysis in zip(tasks_to_create, analyzed_details) if task.get('title')
            ]
            if not actions: return self._error_response("I couldn't parse any valid tasks from your request.")

            return {'success': True, 'actions': actions, 'response': f"Okay, I've added {len(actions)} new tasks to your list."}

        filters = intent_details.get('filters', {})
        filter_description = filters.get('description')
        status_filter = filters.get('status', 'todo') # Default to 'todo'

        if not filter_description:
            return self._error_response("I'm not sure which tasks you want to modify. Please be more specific.")

        # For safety, lock 'complete' operations to 'todo' tasks.
        if operation == 'complete' and status_filter != 'todo':
            return self._error_response("You can only mark active (todo) tasks as complete.")
        
        task_ids_to_modify = self._find_matching_tasks_for_batch_op(filter_description, user_id, user_context, status=status_filter)

        if not task_ids_to_modify:
            return self._error_response(f"I couldn't find any {status_filter} tasks that match your criteria.")

        task_count = len(task_ids_to_modify)
        if operation == 'delete':
            actions = [{'type': 'delete_task', 'task_id': task_id} for task_id in task_ids_to_modify]
            response = f"Okay, I've deleted {task_count} {status_filter} task(s) that matched your criteria."
        elif operation == 'complete':
            patch = {'status': 'done'}
            actions = [{'type': 'update_task', 'task_id': task_id, 'patch': patch} for task_id in task_ids_to_modify]
            response = f"Done! I've marked {task_count} task(s) as complete."

        elif operation == 'update':
            patch = intent_details.get('patch', {})
            if not patch:
                return self._error_response("You asked to update multiple tasks, but didn't specify the change.")
            
            actions = [{'type': 'update_task', 'task_id': task_id, 'patch': patch} for task_id in task_ids_to_modify]
            response = f"Okay, I've updated {task_count} task(s) that matched your criteria."
            
        else:
            return self._error_response(f"The batch operation '{operation}' is not supported for existing tasks.")
            
        return {'success': True, 'actions': actions, 'response': response}

    def _determine_intent(self, user_command: str) -> Dict[str, Any]:
        prompt = self._build_intent_determination_prompt(user_command)
        response_text = self._make_ai_request_sync(prompt)
        try:
            return json.loads(response_text.strip().replace('```json', '').replace('```', ''))
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Could not parse task intent. Defaulting to 'create_task'. Response: {response_text}")
            return {'intent': 'create_task', 'title': user_command}

    def _analyze_task_details(self, title: str, content: str, user_id: str, intent_details: Dict, due_date_str: Optional[str], user_context: Dict) -> Dict[str, Any]:
        if intent_details.get('category'):
            category = intent_details['category'].lower().strip()
            priority = self._analyze_priority_heuristically(title, content, due_date_str)
            normalized_due_date = self._normalize_time_string(due_date_str, user_context) if due_date_str else None
            return {'category': category, 'priority': priority, 'normalized_due_date': normalized_due_date}

        custom_categories = self._get_user_custom_categories(user_id)
        prompt = self._build_combined_analysis_prompt(content, custom_categories, user_context, due_date_str)
        response_text = self._make_ai_request_sync(prompt)
        try:
            return json.loads(response_text.strip().replace('```json', '').replace('```', ''))
        except (json.JSONDecodeError, TypeError):
            return {'category': 'general', 'priority': 'medium', 'normalized_due_date': None}
    
    def _analyze_batch_task_details(self, tasks_to_create: List[Dict], user_id: str, user_context: Dict) -> List[Dict]:
        custom_categories = self._get_user_custom_categories(user_id)
        prompt = self._build_batch_analysis_prompt(tasks_to_create, custom_categories, user_context)
        response_text = self._make_ai_request_sync(prompt)
        try:
            analyzed_tasks = json.loads(response_text.strip().replace('```json', '').replace('```', ''))
            return analyzed_tasks if isinstance(analyzed_tasks, list) else []
        except (json.JSONDecodeError, TypeError):
            return [{'category': 'general', 'priority': 'medium', 'normalized_due_date': None}] * len(tasks_to_create)

    def _normalize_time_string(self, time_str: str, user_context: Dict) -> Optional[str]:
        if not time_str: return None
        prompt = self._build_time_parsing_prompt(time_str, user_context)
        response_text = self._make_ai_request_sync(prompt)
        try:
            parsed_time = response_text.strip()
            datetime.strptime(parsed_time, ISO_UTC_FORMAT)
            return parsed_time
        except (ValueError, TypeError):
            return None

    def _normalize_date_range(self, time_str: str, user_context: Dict) -> Tuple[Optional[str], Optional[str]]:
        if not time_str: return None, None
        prompt = self._build_date_range_parsing_prompt(time_str, user_context)
        response_text = self._make_ai_request_sync(prompt)
        try:
            date_range = json.loads(response_text.strip().replace('```json', '').replace('```', ''))
            start_utc, end_utc = date_range.get('start_utc'), date_range.get('end_utc')
            if start_utc and end_utc: return start_utc, end_utc
            return None, None
        except (json.JSONDecodeError, TypeError, ValueError):
            return None, None

    def _get_user_custom_categories(self, user_id: str) -> List[str]:
        cache_key = f"task_categories_{user_id}"
        if cache_key in self.category_cache and time.time() - self.category_cache[cache_key][0] < 300:
            return self.category_cache[cache_key][1]
        try:
            if not self.supabase: return []
            result = self.supabase.table('tasks').select('category').eq('user_id', user_id).eq('status', 'todo').execute()
            if result.data:
                custom_cats = list(set(d['category'] for d in result.data if d.get('category')))
                self.category_cache[cache_key] = (time.time(), custom_cats)
                return custom_cats
        except Exception as e:
            logger.error(f"Error fetching custom task categories: {e}")
        return []

    def _find_best_task_match(self, query: str, user_id: str) -> Dict:
        # This function is for modification, so it should ONLY ever search 'todo' tasks.
        try:
            if not self.supabase: return {'found': False}
            res = self.supabase.table('tasks').select('id, title, category').eq('user_id', user_id).eq('status', 'todo').execute()
            candidate_tasks = res.data or []
            if not candidate_tasks: return {'found': False}

            prompt = self._build_find_task_prompt(query, candidate_tasks)
            response_text = self._make_ai_request_sync(prompt)
            matches = json.loads(response_text.strip().replace('```json', '').replace('```', '')).get('matches', [])

            if not matches: return {'found': False}
            
            best_match_title = matches[0]
            matched_task = next((task for task in candidate_tasks if task['title'].lower() == best_match_title.lower()), None)
            
            if len(matches) > 1: return {'found': True, 'ambiguous': True, 'options': matches}
            
            return {'found': True, 'ambiguous': False, 'task': matched_task}
        except Exception as e:
            logger.error(f"Error during intelligent task search: {e}")
            return {'found': False}

    def _find_matching_tasks_for_batch_op(self, filter_description: str, user_id: str, user_context: dict, status: str = 'todo') -> List[int]:
        """Uses AI to find all tasks matching a natural language description and a given status."""
        try:
            if not self.supabase: return []
            # UPDATED: The query now uses the 'status' parameter.
            res = self.supabase.table('tasks').select('id, title, category, description').eq('user_id', user_id).eq('status', status).execute()
            candidate_tasks = res.data or []
            if not candidate_tasks: return []

            prompt = self._build_batch_filter_prompt(filter_description, candidate_tasks, user_context)
            response_text = self._make_ai_request_sync(prompt)
            
            if not response_text: return []

            result = json.loads(response_text.strip().replace('```json', '').replace('```', ''))
            return result.get('task_ids', [])
        except (json.JSONDecodeError, TypeError, Exception) as e:
            logger.error(f"Error during AI-powered batch filtering: {e}")
            return []

    def _analyze_priority_heuristically(self, title: str, description: str, due_date: Optional[str]) -> str:
        content = f"{title} {description}".lower()
        if any(k in content for k in ['urgent', 'asap', 'critical', 'important', 'emergency']): return 'high'
        if due_date: return 'medium'
        return 'low'

    def _make_ai_request_sync(self, prompt: str) -> Optional[str]:
        if not self.ai_model: return None
        try:
            self._enforce_rate_limit()
            response = self.ai_model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.exception(f"AI request failed in TaskAgent: {e}")
            return None

    def _enforce_rate_limit(self):
        time_since_call = time.time() - self.last_api_call
        if time_since_call < self.rate_limit_seconds:
            time.sleep(self.rate_limit_seconds - time_since_call)
        self.last_api_call = time.time()
        
    def _error_response(self, message: str) -> Dict[str, Any]:
        return {'success': False, 'actions': [], 'response': f"❌ {message}", 'error': message}

    def _build_intent_determination_prompt(self, user_command: str) -> str:
        return f"""Analyze the user's command for task management and extract a structured JSON object.

User Command: "{user_command}"

**CRITICAL GOAL:** Your most important job is to distinguish between a command for a SINGLE task versus a command for MULTIPLE tasks (a "batch_operation"). Commands that list several items separated by commas or "and", or use words like "all" or "every", are almost always a 'batch_operation'.

**Definitions:**
- `intent`: One of 'create_task', 'list_tasks', 'update_task', 'complete_task', 'delete_task', 'batch_operation'.
- `title`: (For create_task) The main subject.
- `title_match`: (For single task ops) The title of the task to modify.
- `patch`: (For update_task) A dictionary of changes.
- `operation`: (For batch) The action: 'create', 'delete', 'complete', or 'update'.
- `tasks_to_create`: (For batch create) A list of new task objects, each with a 'title' and optional 'due_date'.
- `filters`: A dictionary with a `description` of the tasks to find.

---
**EXAMPLES**
---

### --- BATCH CREATION (Multiple Tasks) ---
# Note: These commands create several tasks at once.

# Implicit batch creation with deadlines (the original problem case)
- "test 1 deadline hari ini, test 2 deadline besok, test 3 deadline lusa" -> {{"intent": "batch_operation", "operation": "create", "tasks_to_create": [{{"title": "test 1", "due_date": "hari ini"}}, {{"title": "test 2", "due_date": "besok"}}, {{"title": "test 3", "due_date": "lusa"}}]}}

# Explicit batch creation with natural language
- "add two tasks: schedule the annual review and book a flight to Jakarta" -> {{"intent": "batch_operation", "operation": "create", "tasks_to_create": [{{"title": "schedule the annual review"}}, {{"title": "book a flight to Jakarta"}}]}}

# Simple implicit list
- "buy milk, walk the dog, pay the electricity bill" -> {{"intent": "batch_operation", "operation": "create", "tasks_to_create": [{{"title": "buy milk"}}, {{"title": "walk the dog"}}, {{"title": "pay the electricity bill"}}]}}

### --- BATCH MODIFICATION (Multiple Tasks) ---
# Note: These commands modify existing tasks that match a description.

# Batch deletion using a filter
- "delete all the tasks that contain the word 'Project'" -> {{"intent": "batch_operation", "operation": "delete", "filters": {{"description": "all tasks that contain the word 'Project'", "status": "todo"}}}}

# Batch completion using a filter
- "finish all my tasks for the 'Website Launch' initiative" -> {{"intent": "batch_operation", "operation": "complete", "filters": {{"description": "tasks for the 'Website Launch' initiative", "status": "todo"}}}}

# Intricate batch update using a filter
- "change all my 'work' tasks to the 'project-alpha' category" -> {{"intent": "batch_operation", "operation": "update", "filters": {{"description": "all 'work' tasks"}}, "patch": {{"category": "project-alpha"}}}}

### --- SINGLE TASK OPERATIONS ---
# Note: These commands target only one specific task.

# Simple single task creation
- "remind me to call the doctor's office tomorrow at 10am" -> {{"intent": "create_task", "title": "call the doctor's office", "due_date": "tomorrow at 10am"}}

# Complex single task update with a clear title match
- "update the deadline for 'Submit Q3 Financial Report' to next Friday EOD" -> {{"intent": "update_task", "title_match": "Submit Q3 Financial Report", "patch": {{"due_date": "next Friday EOD"}}}}

# Single task completion
- "mark 'Finalize presentation slides' as done" -> {{"intent": "complete_task", "title_match": "Finalize presentation slides"}}

# Listing tasks (always a single operation, but can return multiple results)
- "show me my high priority tasks for this week" -> {{"intent": "list_tasks", "filters": {{"description": "high priority tasks for this week", "status": "todo"}}}}
---

Now, analyze the user's command carefully based on these detailed examples. Respond with ONLY a valid JSON object.
"""

    def _build_batch_filter_prompt(self, filter_description: str, tasks: List[Dict], user_context: Dict) -> str:
        current_utc = datetime.now(timezone.utc).strftime(ISO_UTC_FORMAT)
        user_timezone = user_context.get('user_info', {}).get('timezone', 'UTC')
        task_list_str = json.dumps(tasks, indent=2)
        return f"""You are a smart task filter. Your job is to analyze a user's request and identify all the tasks that match it from a provided list.
**User's Filter Request:** "{filter_description}"
**Context:**
- Current UTC Time: {current_utc}
- User's Timezone: {user_timezone}
**Candidate Tasks:**
{task_list_str}
**Instructions:**
1.  Read the "User's Filter Request" carefully. Consider keywords, dates, categories, and intent.
2.  Examine each task in the "Candidate Tasks" list.
3.  Select *all* tasks that logically match the user's request.
4.  Your response MUST be a single JSON object with one key: `task_ids`.
5.  The value of `task_ids` must be a list of the integer IDs of all the matching tasks.
6.  If no tasks match, return an empty list: {{"task_ids": []}}.
Respond with ONLY the valid JSON object.
"""

    def _build_batch_analysis_prompt(self, tasks: List[Dict], active_categories: List[str], user_context: Dict) -> str:
        current_utc = datetime.now(timezone.utc).strftime(ISO_UTC_FORMAT)
        user_timezone = user_context.get('user_info', {}).get('timezone', 'UTC')
        task_list_str = json.dumps(tasks, indent=2)
        return f"""Analyze a list of new tasks and return a JSON array where each object contains the analysis for the corresponding task.
User's Task List:
{task_list_str}
**Categorization Rules:**
1.  **PRIORITY 1: Use Existing Active Categories.** First, try to see if the user spesified a **category** for each task, if not try to match with the user's active categories: {json.dumps(active_categories)} if its no match for example task : cooking dinner for wife available category: work then create a new one .
2.  **PRIORITY 2: Create a New, Specific Category.** If a task does not fit an existing category, create a NEW, descriptive, project-focused category (e.g., "Plan Paris Holiday"). AVOID generic categories like "Work" or "Personal".
**Other Instructions:**
-   **Priority**: Assign 'high' for urgent tasks, 'low' for optional ones, 'medium' otherwise.
-   **Due Date**: If a 'due_date' string exists, convert it to an ISO 8601 UTC timestamp ({ISO_UTC_FORMAT}). Current time: {current_utc}. User's timezone: {user_timezone}. Use 5 PM local time for dates without times. If invalid, it must be null.
-   **Response Format**: Your response MUST be a single JSON array, with the same number of objects as the input.
Respond with ONLY the valid JSON array.
"""

    def _build_combined_analysis_prompt(self, content: str, active_categories: List[str], user_context: Dict, due_date_str: Optional[str]) -> str:
        current_utc = datetime.now(timezone.utc).strftime(ISO_UTC_FORMAT)
        user_timezone = user_context.get('user_info', {}).get('timezone', 'UTC')
        time_section = 'The user did not provide a due date, so "normalized_due_date" should be null.'
        if due_date_str:
            time_section = f"""- **Due Date Parsing**: User's raw date input is "{due_date_str}". Convert this into a precise ISO 8601 UTC timestamp ({ISO_UTC_FORMAT}), assuming the current time is {current_utc} and the user's timezone is {user_timezone}. For dates without times, use 5 PM user's local time."""
        return f"""Analyze the task and respond with a single JSON object with "category", "priority", and "normalized_due_date" keys.
Task Content: "{content}"
**Categorization Rules:**
1.  **PRIORITY 1: Use Existing Active Category.** You MUST try to fit the task into one of the user's existing categories: {json.dumps(active_categories)}.
2.  **PRIORITY 2: Create New Specific Category.** If it does not fit, create a NEW, descriptive, project-focused category (e.g., "Plan Paris Holiday"). AVOID generic categories like "Work" or "Personal".
**Other Instructions:**
- **Priority**: Assign 'high' for urgent tasks; 'low' for optional ones; default 'medium'.
{time_section}
Respond with ONLY a valid JSON object.
"""

    def _build_time_parsing_prompt(self, time_str: str, user_context: Dict) -> str:
        current_utc = datetime.now(timezone.utc).strftime(ISO_UTC_FORMAT)
        user_timezone = user_context.get('user_info', {}).get('timezone', 'UTC')
        return f"""Convert the user's time expression into a single, precise ISO 8601 UTC timestamp ({ISO_UTC_FORMAT}).
- User's Time Expression: "{time_str}"
- Current UTC Time: {current_utc}
- User's Timezone: {user_timezone}
RULES:
- For dates without times (e.g., "tomorrow"), use end of business day (5 PM local time).
- If the expression is not a date, return "Error".
Respond with ONLY the timestamp string or "Error".
"""

    def _build_date_range_parsing_prompt(self, time_str: str, user_context: Dict) -> str:
        current_utc = datetime.now(timezone.utc).strftime(ISO_UTC_FORMAT)
        user_timezone = user_context.get('user_info', {}).get('timezone', 'UTC')
        return f"""Analyze the user's time expression and convert it into a start and end ISO 8601 UTC timestamp.
- User's Time Expression: "{time_str}"
- Current UTC Time: {current_utc}
- User's Timezone: {user_timezone}
RULES:
- "today": Start of user's day (00:00) to end (23:59:59).
- "this week": Start of Monday to end of Sunday.
- Convert final times to UTC.
Respond with ONLY a valid JSON object with "start_utc" and "end_utc".
"""

    def _build_find_task_prompt(self, query: str, tasks: List[Dict]) -> str:
        task_list = "\n".join([f"- Title: \"{task['title']}\", Category: \"{task['category']}\"" for task in tasks])
        return f"""From the following list of active tasks, find the best match(es) for the user's query.
User Query: "{query}"
Available Tasks:
{task_list}
Instructions:
- Analyze the query for the most relevant task.
- If it's a clear match, return that single task title.
- If two or three tasks are very similar, return all their titles for clarification.
Respond with ONLY a valid JSON object with a single key "matches", a list of the exact titles of the matching task(s).
"""