# ai_tools.py (Corrected and Merged Version)

import re
from datetime import datetime
import pytz
from croniter import croniter
import time

# Local imports (ensure these files exist and are correct)
import database_personal

# --- Helper Functions ---

def _to_snake_case(s):
    """Converts camelCase string to snake_case."""
    return re.sub(r'(?<!^)(?=[A-Z])', '_', s).lower()

def _convert_keys_to_snake_case(d):
    """Recursively converts all keys in a dictionary to snake_case."""
    if not isinstance(d, dict):
        return d
    return {_to_snake_case(k): _convert_keys_to_snake_case(v) for k, v in d.items()}

def _find_task(supabase, user_id, id=None, titleMatch=None):
    """
    Finds a single task by querying the database_personal.
    Prioritizes ID if provided, otherwise uses title match.
    """
    if id:
        tasks = database_personal.query_tasks(supabase, user_id, id=id)
        if tasks:
            return tasks[0]
    if titleMatch:
        # Use a title_like query for partial matching
        tasks = database_personal.query_tasks(supabase, user_id, title_like=titleMatch)
        if tasks:
            return tasks[0]
    return None



def _find_list_id_by_name(supabase, user_id, list_name):
    """Finds the ID of a list by its name."""
    if not list_name:
        return None
    lists = database_personal.query_lists(supabase, user_id, name=list_name)
    if lists:
        return lists[0]['id']
    print(f"TOOL: Could not find list with name '{list_name}'")
    return None

# --- FIX: Re-added from original working code to process list names in arguments ---
def _process_list_name(supabase, user_id, args):
    """Checks for a 'list' key in args, finds its ID, and replaces it with 'list_id'."""
    if 'list' in args:
        list_name = args.pop('list')
        if list_name:
            list_id = _find_list_id_by_name(supabase, user_id, list_name)
            if list_id:
                args['list_id'] = list_id
        else:
            # Handle cases where the list is explicitly set to null/none
            args['list_id'] = None
    return args

def _log_action_with_timing(supabase, user_id, action_type, entity_type, entity_id=None, 
                           action_details=None, user_input=None, success_status=True, 
                           error_details=None, session_id=None):
    """Helper function to log actions with execution timing."""
    try:
        database_personal.log_action(
            supabase=supabase,
            user_id=user_id,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            action_details=action_details or {},
            success_status=success_status,
            error_details=error_details,
            execution_time_ms=action_details.get('execution_time_ms') if action_details else None
        )
    except Exception as e:
        # Don't let logging errors break the main functionality
        print(f"!!! ACTION LOGGING ERROR: {e}")

# --- Task & Reminder Tools (Corrected Signatures) ---
# ai_tools.py

def add_task(supabase, user_id, **kwargs):
    """Adds a new task."""
    start_time = time.time()
    
    try:
        # FIX: Process list name and convert all keys to snake_case
        processed_kwargs = _process_list_name(supabase, user_id, kwargs)
        snake_case_args = _convert_keys_to_snake_case(processed_kwargs)

        # --- START CORRECTION ---
        # Standardize the 'difficulty' field to lowercase to match the database constraint.
        if 'difficulty' in snake_case_args and isinstance(snake_case_args.get('difficulty'), str):
            snake_case_args['difficulty'] = snake_case_args['difficulty'].lower()
        # --- END CORRECTION ---
        
        result = database_personal.add_task_entry(supabase, user_id, **snake_case_args)
        task_id = result.get('id') if result else None
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Log successful action
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="add_task",
            entity_type="task",
            entity_id=task_id,
            action_details={
                "title": kwargs.get('title'),
                "parameters": snake_case_args,
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )
        
        return {"status": "ok", "message": f"I've added the task: '{kwargs.get('title')}'."}
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        # Log failed action
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="add_task",
            entity_type="task",
            action_details={
                "title": kwargs.get('title'),
                "parameters": kwargs,
                "execution_time_ms": execution_time_ms
            },
            success_status=False,
            error_details=error_msg
        )
        
        return {"status": "error", "message": f"Failed to add task: {error_msg}"}


def delete_task(supabase, user_id=None, task_id=None, title=None, titleMatch=None, **kwargs):
    start_time = time.time()
    title = title or titleMatch
    
    try:
        if not task_id and not title:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="delete_task",
                entity_type="task",
                action_details={"execution_time_ms": execution_time_ms},
                success_status=False,
                error_details="No valid task_id or title provided"
            )
            return {"message": "No valid task_id(s) or title provided."}

        query = supabase.table("tasks").delete().eq("user_id", user_id)
        if task_id:
            query = query.eq("id", task_id)
        else:
            query = query.eq("title", title)
        result = query.execute()
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Log successful action
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="delete_task",
            entity_type="task",
            entity_id=task_id,
            action_details={
                "task_id": task_id,
                "title": title,
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )

        return {"message": f"Deleted task(s) matching {task_id or title}"}
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        # Log failed action
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="delete_task",
            entity_type="task",
            entity_id=task_id,
            action_details={
                "task_id": task_id,
                "title": title,
                "execution_time_ms": execution_time_ms
            },
            success_status=False,
            error_details=error_msg
        )
        
        return {"status": "error", "message": f"Failed to delete task: {error_msg}"}


def update_task(supabase, user_id, task_id=None, titleMatch=None, patch=None):
    start_time = time.time()
    
    try:
        if not task_id and not titleMatch:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="update_task",
                entity_type="task",
                action_details={"execution_time_ms": execution_time_ms},
                success_status=False,
                error_details="No task identifier provided"
            )
            return {"error": "No task identifier provided"}

        # Find task by task_id or titleMatch
        query = supabase.table("tasks").select("*").eq("user_id", user_id)
        if task_id:
            query = query.eq("id", task_id)
        elif titleMatch:
            query = query.ilike("title", f"%{titleMatch}%")

        task = query.execute()
        if not task.data:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="update_task",
                entity_type="task",
                entity_id=task_id,
                action_details={
                    "task_id": task_id,
                    "titleMatch": titleMatch,
                    "execution_time_ms": execution_time_ms
                },
                success_status=False,
                error_details="Task not found"
            )
            return {"error": "Task not found"}

        # Apply patch (can be title, due_date, priority, etc.)
        update_fields = {}
        if patch:
            update_fields.update(patch)

        if not update_fields:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="update_task",
                entity_type="task",
                entity_id=task.data[0]["id"],
                action_details={"execution_time_ms": execution_time_ms},
                success_status=False,
                error_details="No fields to update"
            )
            return {"error": "No fields to update"}

        result = supabase.table("tasks").update(update_fields).eq("id", task.data[0]["id"]).execute()
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Log successful action
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="update_task",
            entity_type="task",
            entity_id=task.data[0]["id"],
            action_details={
                "task_id": task_id,
                "titleMatch": titleMatch,
                "patch": patch,
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )

        return {"success": True, "updated": result.data}
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        # Log failed action
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="update_task",
            entity_type="task",
            entity_id=task_id,
            action_details={
                "task_id": task_id,
                "titleMatch": titleMatch,
                "patch": patch,
                "execution_time_ms": execution_time_ms
            },
            success_status=False,
            error_details=error_msg
        )
        
        return {"status": "error", "message": f"Failed to update task: {error_msg}"}


def complete_task(supabase, user_id=None, task_id=None, title=None, titleMatch=None, **kwargs):
    start_time = time.time()
    title = title or titleMatch
    
    try:
        if not task_id and not title:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="complete_task",
                entity_type="task",
                action_details={"execution_time_ms": execution_time_ms},
                success_status=False,
                error_details="No valid task_id or title provided"
            )
            return {"message": "No valid task_id(s) or title provided."}

        query = supabase.table("tasks").update({"status": "completed"}).eq("user_id", user_id)
        if task_id:
            query = query.eq("id", task_id)
        else:
            query = query.eq("title", title)
        result = query.execute()
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Log successful action
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="complete_task",
            entity_type="task",
            entity_id=task_id,
            action_details={
                "task_id": task_id,
                "title": title,
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )

        return {"message": f"Marked task {task_id or title} as completed"}
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        # Log failed action
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="complete_task",
            entity_type="task",
            entity_id=task_id,
            action_details={
                "task_id": task_id,
                "title": title,
                "execution_time_ms": execution_time_ms
            },
            success_status=False,
            error_details=error_msg
        )
        
        return {"status": "error", "message": f"Failed to complete task: {error_msg}"}


def set_reminder(supabase, user_id, id=None, titleMatch=None, reminderTime=None):
    """Sets a reminder for a specific task."""
    start_time = time.time()
    
    try:
        if not reminderTime:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="set_reminder",
                entity_type="reminder",
                action_details={"execution_time_ms": execution_time_ms},
                success_status=False,
                error_details="A specific reminder time is required"
            )
            return {"status": "error", "message": "A specific reminder time is required."}
            
        task = _find_task(supabase, user_id, id=id, titleMatch=titleMatch)
        if not task:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="set_reminder",
                entity_type="reminder",
                action_details={
                    "titleMatch": titleMatch,
                    "reminderTime": reminderTime,
                    "execution_time_ms": execution_time_ms
                },
                success_status=False,
                error_details=f"Task '{titleMatch}' not found"
            )
            return {"status": "not_found", "message": f"I couldn't find the task '{titleMatch}' to set a reminder for."}
            
        patch = {"reminder_at": reminderTime, "reminder_sent": False}
        database_personal.update_task_entry(supabase, user_id, task['id'], patch)
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="set_reminder",
            entity_type="reminder",
            entity_id=task['id'],
            action_details={
                "task_title": task['title'],
                "reminderTime": reminderTime,
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )
        
        return {"status": "ok", "message": f"Reminder set for '{task['title']}'."}
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="set_reminder",
            entity_type="reminder",
            action_details={
                "titleMatch": titleMatch,
                "reminderTime": reminderTime,
                "execution_time_ms": execution_time_ms
            },
            success_status=False,
            error_details=error_msg
        )
        
        return {"status": "error", "message": f"Failed to set reminder: {error_msg}"}

def update_reminder(supabase, user_id, id=None, titleMatch=None, newReminderTime=None):
    """Updates the reminder time for a specific task."""
    start_time = time.time()
    
    try:
        task = _find_task(supabase, user_id, id=id, titleMatch=titleMatch)
        if not task:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="update_reminder",
                entity_type="reminder",
                action_details={
                    "titleMatch": titleMatch,
                    "newReminderTime": newReminderTime,
                    "execution_time_ms": execution_time_ms
                },
                success_status=False,
                error_details=f"Task '{titleMatch}' not found"
            )
            return {"status": "not_found", "message": f"I couldn't find a task matching '{titleMatch}'."}
        
        patch = {"reminder_at": newReminderTime, "reminder_sent": False}
        database_personal.update_task_entry(supabase, user_id, task['id'], patch)
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="update_reminder",
            entity_type="reminder",
            entity_id=task['id'],
            action_details={
                "task_title": task['title'],
                "newReminderTime": newReminderTime,
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )
        
        return {"status": "ok", "message": f"I've updated the reminder for '{task['title']}'."}
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="update_reminder",
            entity_type="reminder",
            action_details={
                "titleMatch": titleMatch,
                "newReminderTime": newReminderTime,
                "execution_time_ms": execution_time_ms
            },
            success_status=False,
            error_details=error_msg
        )
        
        return {"status": "error", "message": f"Failed to update reminder: {error_msg}"}

def delete_reminder(supabase, user_id, id=None, titleMatch=None):
    """Deletes a reminder from a specific task."""
    start_time = time.time()
    
    try:
        task = _find_task(supabase, user_id, id=id, titleMatch=titleMatch)
        if not task:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="delete_reminder",
                entity_type="reminder",
                action_details={
                    "titleMatch": titleMatch,
                    "execution_time_ms": execution_time_ms
                },
                success_status=False,
                error_details=f"Task '{titleMatch}' not found"
            )
            return {"status": "not_found", "message": f"I couldn't find a task matching '{titleMatch}'."}
        
        patch = {"reminder_at": None, "reminder_sent": None}
        database_personal.update_task_entry(supabase, user_id, task['id'], patch)
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="delete_reminder",
            entity_type="reminder",
            entity_id=task['id'],
            action_details={
                "task_title": task['title'],
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )
        
        return {"status": "ok", "message": f"I've removed the reminder from '{task['title']}'."}
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="delete_reminder",
            entity_type="reminder",
            action_details={
                "titleMatch": titleMatch,
                "execution_time_ms": execution_time_ms
            },
            success_status=False,
            error_details=error_msg
        )
        
        return {"status": "error", "message": f"Failed to delete reminder: {error_msg}"}

def list_all_reminders(supabase, user_id):
    """Fetches and formats a list of all tasks that have an active reminder."""
    try:
        reminders = database_personal.get_all_reminders(supabase, user_id)
    except Exception as e:
        print(f"!!! TOOL ERROR in list_all_reminders: {e}")
        return "I had trouble retrieving your list of reminders right now."

    if not reminders:
        return "You don't have any reminders set at the moment."

    response_lines = ["Here are your active reminders:"]
    for reminder in reminders:
        reminder_time_utc = datetime.fromisoformat(reminder['reminder_at'].replace('Z', '+00:00'))
        response_lines.append(f"  - For task *'{reminder['title']}'* at `{reminder_time_utc.strftime('%Y-%m-%d %H:%M')} UTC`")
    
    return "\n".join(response_lines)


# --- Journal Tools ---

def _auto_categorize_journal(title, content):
    """Automatically categorizes a journal entry based on its title and content."""
    # Default category for empty or None values
    if not title and not content:
        return "uncategorized"
    
    # Simple keyword-based categorization
    title_lower = (title or "").lower()
    content_lower = (content or "").lower()
    text_to_analyze = f"{title_lower} {content_lower}"
    
    # Meeting notes
    if any(word in text_to_analyze for word in ["meeting", "conference", "discussion", "session", "workshop", "webinar"]):
        return "meeting_notes"
    
    # Ideas and brainstorming
    if any(word in text_to_analyze for word in ["idea", "concept", "brainstorm", "thought", "inspiration", "innovation"]):
        return "ideas"
    
    # Research and learning
    if any(word in text_to_analyze for word in ["research", "study", "learn", "discover", "fact", "trivia", "knowledge"]):
        return "research"
    
    # Plans and goals
    if any(word in text_to_analyze for word in ["plan", "goal", "objective", "strategy", "roadmap", "milestone"]):
        return "planning"
    
    # References and resources
    if any(word in text_to_analyze for word in ["reference", "resource", "link", "book", "article", "video"]):
        return "reference"
    
    # Fall back to "general" for anything else
    return "general"

def add_journal(supabase, user_id, title=None, content=None, category=None):
    """Adds a journal entry to the database, with automatic categorization."""
    start_time = time.time()
    
    try:
        if not title:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="add_journal",
                entity_type="journal",
                action_details={"execution_time_ms": execution_time_ms},
                success_status=False,
                error_details="A title for the journal entry is required"
            )
            return {"status": "error", "message": "A title for the journal entry is required."}
        
        # Auto-categorize if no category provided
        if not category:
            category = _auto_categorize_journal(title, content)
        
        result = database_personal.add_journal_entry(supabase, user_id, title, content, category)
        journal_id = result.get('id') if result else None
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="add_journal",
            entity_type="journal",
            entity_id=journal_id,
            action_details={
                "title": title,
                "category": category,
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )
        
        return {"status": "ok", "message": f"I've added a journal entry: '{title}' (Category: {category})."}
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="add_journal",
            entity_type="journal",
            action_details={
                "title": title,
                "category": category,
                "execution_time_ms": execution_time_ms
            },
            success_status=False,
            error_details=error_msg
        )
        
        return {"status": "error", "message": f"Failed to add journal entry: {error_msg}"}

def update_journal(supabase, user_id, titleMatch=None, patch=None):
    """Updates an existing journal entry."""
    start_time = time.time()
    
    try:
        if not titleMatch or not patch:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="update_journal",
                entity_type="journal",
                action_details={"execution_time_ms": execution_time_ms},
                success_status=False,
                error_details="A title and data to update are required"
            )
            return {"status": "error", "message": "A title and data to update are required."}
        
        journal = database_personal.find_journal_by_title(supabase, user_id, titleMatch)
        if not journal:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="update_journal",
                entity_type="journal",
                action_details={
                    "titleMatch": titleMatch,
                    "execution_time_ms": execution_time_ms
                },
                success_status=False,
                error_details=f"Journal entry '{titleMatch}' not found"
            )
            return {"status": "not_found", "message": f"I couldn't find a journal entry matching '{titleMatch}'."}
        
        database_personal.update_journal_entry(supabase, user_id, journal['id'], patch)
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="update_journal",
            entity_type="journal",
            entity_id=journal['id'],
            action_details={
                "journal_title": journal['title'],
                "titleMatch": titleMatch,
                "patch": patch,
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )
        
        return {"status": "ok", "message": f"I've updated the journal entry: '{journal['title']}'."}
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="update_journal",
            entity_type="journal",
            action_details={
                "titleMatch": titleMatch,
                "patch": patch,
                "execution_time_ms": execution_time_ms
            },
            success_status=False,
            error_details=error_msg
        )
        
        return {"status": "error", "message": f"Failed to update journal entry: {error_msg}"}

def delete_journal(supabase, user_id, titleMatch=None):
    """Deletes a journal entry from the database."""
    start_time = time.time()
    
    try:
        if not titleMatch:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="delete_journal",
                entity_type="journal",
                action_details={"execution_time_ms": execution_time_ms},
                success_status=False,
                error_details="Please tell me the title of the journal entry to delete"
            )
            return {"status": "error", "message": "Please tell me the title of the journal entry to delete."}
        
        journal = database_personal.find_journal_by_title(supabase, user_id, titleMatch)
        if not journal:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="delete_journal",
                entity_type="journal",
                action_details={
                    "titleMatch": titleMatch,
                    "execution_time_ms": execution_time_ms
                },
                success_status=False,
                error_details=f"Journal entry '{titleMatch}' not found"
            )
            return {"status": "not_found", "message": f"I couldn't find a journal entry matching '{titleMatch}'."}
        
        database_personal.delete_journal_entry(supabase, user_id, journal['id'])
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="delete_journal",
            entity_type="journal",
            entity_id=journal['id'],
            action_details={
                "journal_title": journal['title'],
                "titleMatch": titleMatch,
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )
        
        return {"status": "ok", "message": f"I have deleted the journal entry: '{journal['title']}'."}
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="delete_journal",
            entity_type="journal",
            action_details={
                "titleMatch": titleMatch,
                "execution_time_ms": execution_time_ms
            },
            success_status=False,
            error_details=error_msg
        )
        
        return {"status": "error", "message": f"Failed to delete journal entry: {error_msg}"}

def search_journals(supabase, user_id, query=None):
    """Searches for journal entries by title or content."""
    start_time = time.time()
    
    try:
        if not query:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="search_journals",
                entity_type="journal",
                action_details={"execution_time_ms": execution_time_ms},
                success_status=False,
                error_details="Please tell me what you want to search for"
            )
            return "Please tell me what you want to search for."
        
        results = database_personal.search_journal_entries(supabase, user_id, query)
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="search_journals",
            entity_type="journal",
            action_details={
                "query": query,
                "results_count": len(results) if results else 0,
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )
        
        if not results: 
            return f"I couldn't find any journal entries matching '{query}'."
            
        response_lines = [f"I found {len(results)} journal entries matching '{query}':"]
        for i, item in enumerate(results):
            line = f"{i+1}. **{item['title']}**"
            if item.get('category'): line += f" [Category: {item['category']}]"
            if item.get('content'): line += f": {item['content']}"
            response_lines.append(line)
        return "\n".join(response_lines)
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="search_journals",
            entity_type="journal",
            action_details={
                "query": query,
                "execution_time_ms": execution_time_ms
            },
            success_status=False,
            error_details=error_msg
        )
        
        return f"Failed to search journal entries: {error_msg}"

# --- Memory Tools (from refactored code) ---

def _auto_categorize_memory(title, content):
    """
    Automatically categorizes a memory based on its title and content.
    Returns a sensible category string like "preference", "note", "personal", etc.
    """
    # Default category for empty or None values
    if not title and not content:
        return "uncategorized"
    
    # Simple keyword-based categorization
    title_lower = (title or "").lower()
    content_lower = (content or "").lower()
    text_to_analyze = f"{title_lower} {content_lower}"
    
    # Check for conversation history (special case)
    if "conversation history" in title_lower:
        return "conversation_history"
    
    # Preferences and settings
    if any(word in text_to_analyze for word in ["prefer", "setting", "option", "like", "dislike", "favorite", "hate"]):
        return "preference"
    
    # Personal information
    if any(word in text_to_analyze for word in ["my", "i am", "i'm", "mine", "myself", "personal"]):
        return "personal"
    
    # Contact information
    if any(word in text_to_analyze for word in ["contact", "phone", "email", "address", "website"]):
        return "contact"
    
    # Work-related
    if any(word in text_to_analyze for word in ["work", "job", "office", "colleague", "project", "meeting"]):
        return "work"
    
    # Fall back to "note" for anything else
    return "note"

def add_memory(supabase, user_id, title=None, content=None, category=None):
    start_time = time.time()
    
    try:
        if not title:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="add_memory",
                entity_type="memory",
                action_details={"execution_time_ms": execution_time_ms},
                success_status=False,
                error_details="A title for the memory is required"
            )
            return {"status": "error", "message": "A title for the memory is required."}
        
        # Auto-categorize if no category provided
        if not category:
            category = _auto_categorize_memory(title, content)
        
        result = database_personal.add_memory_entry(supabase, user_id, title, content, category)
        memory_id = result.get('id') if result else None
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="add_memory",
            entity_type="memory",
            entity_id=memory_id,
            action_details={
                "title": title,
                "category": category,
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )
        
        return {"status": "ok", "message": f"I'll remember that: '{title}' (Category: {category})."}
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="add_memory",
            entity_type="memory",
            action_details={
                "title": title,
                "category": category,
                "execution_time_ms": execution_time_ms
            },
            success_status=False,
            error_details=error_msg
        )
        
        return {"status": "error", "message": f"Failed to add memory: {error_msg}"}

def update_memory(supabase, user_id, titleMatch=None, patch=None):
    start_time = time.time()
    
    try:
        if not titleMatch or not patch:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="update_memory",
                entity_type="memory",
                action_details={"execution_time_ms": execution_time_ms},
                success_status=False,
                error_details="A title and data to update are required"
            )
            return {"status": "error", "message": "A title and data to update are required."}
        
        memory = database_personal.find_memory_by_title(supabase, user_id, titleMatch)
        if not memory:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="update_memory",
                entity_type="memory",
                action_details={
                    "titleMatch": titleMatch,
                    "execution_time_ms": execution_time_ms
                },
                success_status=False,
                error_details=f"Memory '{titleMatch}' not found"
            )
            return {"status": "not_found", "message": f"I couldn't find a memory matching '{titleMatch}'."}
        
        database_personal.update_memory_entry(supabase, user_id, memory['id'], patch)
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="update_memory",
            entity_type="memory",
            entity_id=memory['id'],
            action_details={
                "memory_title": memory['title'],
                "titleMatch": titleMatch,
                "patch": patch,
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )
        
        return {"status": "ok", "message": f"I've updated the memory: '{memory['title']}'."}
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="update_memory",
            entity_type="memory",
            action_details={
                "titleMatch": titleMatch,
                "patch": patch,
                "execution_time_ms": execution_time_ms
            },
            success_status=False,
            error_details=error_msg
        )
        
        return {"status": "error", "message": f"Failed to update memory: {error_msg}"}

def delete_memory(supabase, user_id, titleMatch=None):
    start_time = time.time()
    
    try:
        if not titleMatch:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="delete_memory",
                entity_type="memory",
                action_details={"execution_time_ms": execution_time_ms},
                success_status=False,
                error_details="Please tell me the title of the memory to delete"
            )
            return {"status": "error", "message": "Please tell me the title of the memory to delete."}
        
        memory = database_personal.find_memory_by_title(supabase, user_id, titleMatch)
        if not memory:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="delete_memory",
                entity_type="memory",
                action_details={
                    "titleMatch": titleMatch,
                    "execution_time_ms": execution_time_ms
                },
                success_status=False,
                error_details=f"Memory '{titleMatch}' not found"
            )
            return {"status": "not_found", "message": f"I couldn't find a memory matching '{titleMatch}'."}
        
        database_personal.delete_memory_entry(supabase, user_id, memory['id'])
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="delete_memory",
            entity_type="memory",
            entity_id=memory['id'],
            action_details={
                "memory_title": memory['title'],
                "titleMatch": titleMatch,
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )
        
        return {"status": "ok", "message": f"I have deleted the memory: '{memory['title']}'."}
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="delete_memory",
            entity_type="memory",
            action_details={
                "titleMatch": titleMatch,
                "execution_time_ms": execution_time_ms
            },
            success_status=False,
            error_details=error_msg
        )
        
        return {"status": "error", "message": f"Failed to delete memory: {error_msg}"}

def search_memories(supabase, user_id, query=None):
    start_time = time.time()
    
    try:
        if not query:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="search_memories",
                entity_type="memory",
                action_details={"execution_time_ms": execution_time_ms},
                success_status=False,
                error_details="Please tell me what you want to search for"
            )
            return "Please tell me what you want to search for."
        
        results = database_personal.search_memory_entries(supabase, user_id, query)
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="search_memories",
            entity_type="memory",
            action_details={
                "query": query,
                "results_count": len(results) if results else 0,
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )
        
        if not results: 
            return f"I couldn't find any memories matching '{query}'."
            
        response_lines = [f"I found {len(results)} memories matching '{query}':"]
        for i, item in enumerate(results):
            line = f"{i+1}. **{item['title']}**"
            if item.get('content'): line += f": {item['content']}"
            response_lines.append(line)
        return "\n".join(response_lines)
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="search_memories",
            entity_type="memory",
            action_details={
                "query": query,
                "execution_time_ms": execution_time_ms
            },
            success_status=False,
            error_details=error_msg
        )
        
        return f"Failed to search memories: {error_msg}"


# --- Scheduled Action Tools & Helpers (from refactored code) ---

def _build_and_validate_schedule_spec(schedule: dict) -> tuple[str | None, str | None]:
    if not isinstance(schedule, dict): return None, "The schedule format was invalid."
    at_time = schedule.get("at_time")
    if not at_time or ':' not in at_time: return None, "A specific time in HH:MM format is required for the schedule."

    DAY_MAP = {"SU": 0, "MO": 1, "TU": 2, "WE": 3, "TH": 4, "FR": 5, "SA": 6}
    try:
        time_parts = at_time.split(':')
        if len(time_parts) != 2: return None, "The time needs to be in HH:MM format (e.g., 07:00 or 19:30)."
        minute, hour = time_parts[1], time_parts[0]
        
        day_of_week_str = "*"
        if schedule.get("frequency") == "WEEKLY" and schedule.get("by_day"):
            day_codes = [str(DAY_MAP[day.upper()]) for day in schedule["by_day"] if day.upper() in DAY_MAP]
            if not day_codes: return None, "The schedule specified an invalid day of the week."
            day_of_week_str = ",".join(day_codes)

        cron_schedule = f"{minute} {hour} * * {day_of_week_str}"
    except Exception:
        return None, "I couldn't understand that schedule's structure."

    try:
        cron = croniter(cron_schedule, datetime.now(pytz.utc))
        first = cron.get_next(datetime)
        second = cron.get_next(datetime)
        if (second - first).total_seconds() < 3540:
            return None, "Actions can only be scheduled once per hour at most."
    except Exception:
        return None, "That schedule pattern is invalid."
    return cron_schedule, None

def _find_item_from_list(items: list, match_query: str, key: str):
    if not items or not match_query: return None
    query_keywords = set(match_query.lower().split())
    for item in items:
        description = item.get(key, "").lower()
        if not description: continue
        if query_keywords.issubset(description.split()): return item
    return None

def schedule_ai_action(supabase, user_id, action_type=None, schedule=None, description=None, payload=None):
    start_time = time.time()
    
    try:
        if not all([action_type, schedule, description]):
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="schedule_ai_action",
                entity_type="ai_action",
                action_details={"execution_time_ms": execution_time_ms},
                success_status=False,
                error_details="Action type, schedule, and description are required"
            )
            return {"status": "error", "message": "Action type, schedule, and description are required."}
        
        user_context = database_personal.get_user_context_for_ai(supabase, user_id)
        limit = user_context.get('schedule_limit', 5)
        if database_personal.count_active_ai_actions(supabase, user_id) >= limit:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="schedule_ai_action",
                entity_type="ai_action",
                action_details={
                    "action_type_param": action_type,
                    "description": description,
                    "limit": limit,
                    "execution_time_ms": execution_time_ms
                },
                success_status=False,
                error_details=f"Schedule limit of {limit} AI Actions reached"
            )
            return {"status": "limit_reached", "message": f"You have reached your plan's limit of {limit} AI Actions."}

        cron_schedule, error = _build_and_validate_schedule_spec(schedule)
        if error:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="schedule_ai_action",
                entity_type="ai_action",
                action_details={
                    "action_type_param": action_type,
                    "description": description,
                    "schedule": schedule,
                    "execution_time_ms": execution_time_ms
                },
                success_status=False,
                error_details=error
            )
            return {"status": "error", "message": error}

        user_tz = pytz.timezone(user_context.get("timezone", "UTC"))
        next_run_utc = croniter(cron_schedule, datetime.now(user_tz)).get_next(datetime).astimezone(pytz.utc)
        
        result = database_personal.add_ai_action(supabase, user_id, action_type, cron_schedule, next_run_utc.isoformat(), user_tz.zone, description, payload)
        action_id = result.get('id') if result else None
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="schedule_ai_action",
            entity_type="ai_action",
            entity_id=action_id,
            action_details={
                "action_type_param": action_type,
                "description": description,
                "schedule": schedule,
                "cron_schedule": cron_schedule,
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )
        
        return {"status": "ok", "message": f"I've scheduled '{description}' for you."}
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="schedule_ai_action",
            entity_type="ai_action",
            action_details={
                "action_type_param": action_type,
                "description": description,
                "schedule": schedule,
                "execution_time_ms": execution_time_ms
            },
            success_status=False,
            error_details=error_msg
        )
        
        return {"status": "error", "message": f"Failed to schedule AI action: {error_msg}"}

def update_ai_action(supabase, user_id, descriptionMatch=None, patch=None):
    start_time = time.time()
    
    try:
        if not descriptionMatch or not patch:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="update_ai_action",
                entity_type="ai_action",
                action_details={"execution_time_ms": execution_time_ms},
                success_status=False,
                error_details="A description and data to update are required"
            )
            return {"status": "error", "message": "A description and data to update are required."}

        all_actions = database_personal.get_all_active_ai_actions(supabase, user_id)
        action_to_update = _find_item_from_list(all_actions, descriptionMatch, key="description")

        if not action_to_update:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="update_ai_action",
                entity_type="ai_action",
                action_details={
                    "descriptionMatch": descriptionMatch,
                    "execution_time_ms": execution_time_ms
                },
                success_status=False,
                error_details=f"AI Action '{descriptionMatch}' not found"
            )
            return {"status": "not_found", "message": f"I couldn't find an AI Action matching '{descriptionMatch}'."}
        
        # Handle schedule updates
        if 'schedule' in patch:
            new_schedule = patch.pop('schedule')
            cron_schedule, error = _build_and_validate_schedule_spec(new_schedule)
            if error:
                execution_time_ms = int((time.time() - start_time) * 1000)
                _log_action_with_timing(
                    supabase=supabase,
                    user_id=user_id,
                    action_type="update_ai_action",
                    entity_type="ai_action",
                    entity_id=action_to_update['id'],
                    action_details={
                        "descriptionMatch": descriptionMatch,
                        "new_schedule": new_schedule,
                        "execution_time_ms": execution_time_ms
                    },
                    success_status=False,
                    error_details=error
                )
                return {"status": "error", "message": error}
            patch['schedule_spec'] = cron_schedule
            user_context = database_personal.get_user_context_for_ai(supabase, user_id)
            user_tz = pytz.timezone(user_context.get("timezone", "UTC"))
            patch['next_run_at'] = croniter(cron_schedule, datetime.now(user_tz)).get_next(datetime).astimezone(pytz.utc).isoformat()

        database_personal.update_ai_action_entry(supabase, user_id, action_to_update['id'], patch)
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="update_ai_action",
            entity_type="ai_action",
            entity_id=action_to_update['id'],
            action_details={
                "action_description": action_to_update['description'],
                "descriptionMatch": descriptionMatch,
                "patch": patch,
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )
        
        return {"status": "ok", "message": f"I've updated the AI Action: '{action_to_update['description']}'."}
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="update_ai_action",
            entity_type="ai_action",
            action_details={
                "descriptionMatch": descriptionMatch,
                "patch": patch,
                "execution_time_ms": execution_time_ms
            },
            success_status=False,
            error_details=error_msg
        )
        
        return {"status": "error", "message": f"Failed to update AI action: {error_msg}"}

def delete_ai_action(supabase, user_id, descriptionMatch=None):
    start_time = time.time()
    
    try:
        if not descriptionMatch:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="delete_ai_action",
                entity_type="ai_action",
                action_details={"execution_time_ms": execution_time_ms},
                success_status=False,
                error_details="Please provide the description of the AI Action to delete"
            )
            return {"status": "error", "message": "Please provide the description of the AI Action to delete."}
        
        all_actions = database_personal.get_all_active_ai_actions(supabase, user_id)
        action_to_delete = _find_item_from_list(all_actions, descriptionMatch, key="description")
        
        if not action_to_delete:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="delete_ai_action",
                entity_type="ai_action",
                action_details={
                    "descriptionMatch": descriptionMatch,
                    "execution_time_ms": execution_time_ms
                },
                success_status=False,
                error_details=f"AI Action '{descriptionMatch}' not found"
            )
            return {"status": "not_found", "message": f"I couldn't find an AI Action matching '{descriptionMatch}'."}
        
        database_personal.delete_ai_action_entry(supabase, user_id, action_to_delete['id'])
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="delete_ai_action",
            entity_type="ai_action",
            entity_id=action_to_delete['id'],
            action_details={
                "action_description": action_to_delete['description'],
                "descriptionMatch": descriptionMatch,
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )
        
        return {"status": "ok", "message": f"I have deleted the AI Action: '{action_to_delete['description']}'."}
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="delete_ai_action",
            entity_type="ai_action",
            action_details={
                "descriptionMatch": descriptionMatch,
                "execution_time_ms": execution_time_ms
            },
            success_status=False,
            error_details=error_msg
        )
        
        return {"status": "error", "message": f"Failed to delete AI action: {error_msg}"}

def _describe_cron_schedule(schedule_spec: str, user_tz_str: str = "UTC") -> str:
    if not schedule_spec: return "No schedule set"
    try:
        parts = schedule_spec.split()
        if len(parts) != 5: return schedule_spec

        minute, hour, _, _, day_of_week = parts
        
        utc_dt = datetime.now(pytz.utc).replace(hour=int(hour), minute=int(minute), second=0, microsecond=0)
        user_tz = pytz.timezone(user_tz_str)
        local_dt = utc_dt.astimezone(user_tz)
        time_str = local_dt.strftime('%H:%M')

        if day_of_week == "*": return f"every day at {time_str}"
        
        day_map = {"0": "Sunday", "1": "Monday", "2": "Tuesday", "3": "Wednesday", "4": "Thursday", "5": "Friday", "6": "Saturday"}
        days = sorted([int(d) for d in day_of_week.split(',')])
        
        if days == [1, 2, 3, 4, 5]: return f"every weekday at {time_str}"
        if days == [0, 6]: return f"every weekend at {time_str}"

        day_names = [day_map[str(d)] for d in days]
        return f"every {', '.join(day_names)} at {time_str}"
        
    except Exception as e:
        print(f"!!! Error describing cron: {e}")
        return schedule_spec

def list_ai_actions(supabase, user_id):
    try:
        actions = database_personal.get_all_active_ai_actions(supabase, user_id)
        user_context = database_personal.get_user_context_for_ai(supabase, user_id)
        user_tz_str = user_context.get("timezone", "UTC")
    except Exception: return "I had trouble retrieving your AI Actions."

    if not actions: return "You don't have any active AI Actions."

    response_lines = ["Here are your automated AI Actions:"]
    for action in actions:
        human_schedule = _describe_cron_schedule(action['schedule_spec'], user_tz_str)
        response_lines.append(f"  - *{action['description']}* (Runs: {human_schedule})")
    return "\n".join(response_lines)

def task_for_day(supabase, user_id):
    """Shows today's tasks (due today or no deadline) with motivational copywriting."""
    start_time = time.time()
    
    try:
        today_tasks = database_personal.get_tasks_for_today(supabase, user_id)
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Log the action
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="task_for_day",
            entity_type="task",
            action_details={
                "tasks_count": len(today_tasks),
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )
        
        if not today_tasks:
            return {
                "status": "ok",
                "message": "🌟 Amazing! You have a clean slate today! No urgent tasks or deadlines. This is the perfect time to focus on what truly matters to you or tackle something you've been putting off. What would make today feel productive and fulfilling?"
            }
        
        # Create engaging copy based on task count
        if len(today_tasks) == 1:
            intro = "🎯 **Focus Mode Activated!** You have one key task calling for your attention today:"
        elif len(today_tasks) <= 3:
            intro = f"💪 **Power Day Ahead!** You've got {len(today_tasks)} important tasks to conquer today:"
        else:
            intro = f"🚀 **Action-Packed Day!** You have {len(today_tasks)} tasks ready for your attention. Let's break them down:"
        
        task_lines = [intro, ""]
        
        for i, task in enumerate(today_tasks, 1):
            # Add emoji based on difficulty or category
            emoji = "⚡" if task.get('difficulty') == 'easy' else "🔥" if task.get('difficulty') == 'hard' else "💫"
            
            line = f"{emoji} **{task['title']}**"
            
            # Add context clues
            details = []
            if task.get('due_date'):
                details.append("📅 Due today")
            else:
                details.append("🎯 No deadline - perfect flexibility")
                
            if task.get('category'):
                details.append(f"📂 {task['category']}")
            
            if details:
                line += f" ({', '.join(details)})"
            
            if task.get('notes'):
                line += f"\n   💭 *{task['notes']}*"
            
            task_lines.append(line)
        
        # Add motivational closing
        if len(today_tasks) <= 2:
            task_lines.append("\n✨ **You've got this!** These tasks are well within your capabilities. Take them one at a time and celebrate each completion!")
        else:
            task_lines.append("\n🎊 **Pro tip:** Pick your most important task first, then build momentum. You're going to have an incredibly productive day!")
        
        return {
            "status": "ok",
            "message": "\n".join(task_lines)
        }
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        # Log failed action
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="task_for_day",
            entity_type="task",
            action_details={"execution_time_ms": execution_time_ms},
            success_status=False,
            error_details=error_msg
        )
        
        return {"status": "error", "message": f"I had trouble getting your tasks for today: {error_msg}"}

def summary_of_day(supabase, user_id):
    """Shows completed tasks for today with celebratory copywriting."""
    start_time = time.time()
    
    try:
        completed_tasks = database_personal.get_completed_tasks_for_today(supabase, user_id)
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Log the action
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="summary_of_day",
            entity_type="task",
            action_details={
                "completed_count": len(completed_tasks),
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )
        
        if not completed_tasks:
            return {
                "status": "ok",
                "message": "🌱 **Every journey starts with a single step!** You haven't marked any tasks as complete today yet, but that's perfectly okay. Progress isn't always about checking boxes - sometimes it's about planning, thinking, or taking care of yourself. What small win can you celebrate today?"
            }
        
        # Create celebratory copy based on completion count
        if len(completed_tasks) == 1:
            intro = "🎉 **Victory Achieved!** You completed an important task today:"
        elif len(completed_tasks) <= 3:
            intro = f"🏆 **Productivity Champion!** You crushed {len(completed_tasks)} tasks today:"
        else:
            intro = f"🚀 **Absolute Powerhouse!** You demolished {len(completed_tasks)} tasks today - that's incredible:"
        
        task_lines = [intro, ""]
        
        for i, task in enumerate(completed_tasks, 1):
            # Add celebration emoji
            emoji = "✅" if i % 3 == 1 else "🎯" if i % 3 == 2 else "💎"
            
            line = f"{emoji} **{task['title']}**"
            
            # Add completion context
            details = []
            if task.get('difficulty') == 'hard':
                details.append("💪 Tough challenge conquered!")
            elif task.get('difficulty') == 'easy':
                details.append("⚡ Quick win!")
            
            if task.get('category'):
                details.append(f"📂 {task['category']}")
            
            if details:
                line += f" ({', '.join(details)})"
            
            task_lines.append(line)
        
        # Add motivational closing based on performance
        if len(completed_tasks) == 1:
            task_lines.append("\n🌟 **Well done!** Every completed task is a step forward. You're building positive momentum!")
        elif len(completed_tasks) <= 3:
            task_lines.append("\n🎊 **Outstanding work!** You're showing great focus and follow-through. This kind of consistency leads to amazing results!")
        else:
            task_lines.append("\n🎆 **You're on fire!** This level of productivity is truly impressive. You're not just getting things done - you're excelling at it!")
        
        return {
            "status": "ok",
            "message": "\n".join(task_lines)
        }
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        # Log failed action
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="summary_of_day",
            entity_type="task",
            action_details={"execution_time_ms": execution_time_ms},
            success_status=False,
            error_details=error_msg
        )
        
        return {"status": "error", "message": f"I had trouble getting your daily summary: {error_msg}"}

def ai_action_helper(supabase, user_id, **kwargs):
    """General AI action assistance and guidance."""
    start_time = time.time()
    
    try:
        query = kwargs.get('query', '').lower()
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Log the action
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="ai_action_helper",
            entity_type="system",
            action_details={
                "query": query,
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )
        
        # Provide contextual help based on query
        if any(word in query for word in ['schedule', 'automate', 'recurring']):
            return {
                "status": "ok",
                "message": "🤖 **AI Actions are your personal automation assistant!**\n\n**Available automations:**\n⏰ **Daily Summary** - Get automatic updates on your outstanding tasks\n🔄 **Recurring Tasks** - Auto-create tasks that repeat (like 'Weekly planning')\n\n**How to set up:**\n1. Use `schedule_ai_action` to create automations\n2. Set your schedule using cron format (daily, weekly, etc.)\n3. Sit back and let your AI handle the routine stuff!\n\n**Examples:**\n• Daily task summary every morning at 9 AM\n• Weekly goal review every Sunday\n• Monthly reflection reminder\n\nWant me to help you set up a specific automation?"
            }
        
        elif any(word in query for word in ['today', 'daily', 'focus']):
            return {
                "status": "ok",
                "message": "📅 **Daily Productivity Tools at your service!**\n\n🎯 **`task_for_day`** - See what needs your attention today\n   • Shows tasks due today + tasks with no deadline\n   • Motivational formatting to keep you energized\n   • Perfect for morning planning sessions\n\n🏆 **`summary_of_day`** - Celebrate what you've accomplished\n   • Shows all tasks you completed today\n   • Encouraging messages to boost your confidence\n   • Great for evening reflection\n\n💡 **Pro tip:** Use `task_for_day` in the morning to plan, `summary_of_day` in the evening to celebrate!"
            }
        
        else:
            # General help
            return {
                "status": "ok",
                "message": "🎉 **Welcome to your AI Action toolkit!**\n\n**🚀 Quick Actions:**\n• `task_for_day` - What should I focus on today?\n• `summary_of_day` - What did I accomplish today?\n\n**🤖 Automation (AI Actions):**\n• `schedule_ai_action` - Set up recurring automations\n• `list_ai_actions` - See your current automations\n• `update_ai_action` / `delete_ai_action` - Manage automations\n\n**💡 Popular automations:**\n• Daily task summaries (morning motivation)\n• Weekly goal check-ins\n• Monthly reflection reminders\n• Recurring task creation\n\n**Need specific help?** Ask me about 'scheduling automations' or 'daily productivity tools'!"
            }
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        # Log failed action
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="ai_action_helper",
            entity_type="system",
            action_details={"execution_time_ms": execution_time_ms},
            success_status=False,
            error_details=error_msg
        )
        
        return {"status": "error", "message": f"I had trouble providing assistance: {error_msg}"}

# --- The Master Dictionary of All Available Tools ---
AVAILABLE_TOOLS = {
    # Tasks
    "add_task": add_task, "update_task": update_task, "delete_task": delete_task, "complete_task": complete_task,
    # Reminders for Tasks
    "set_reminder": set_reminder, "update_reminder": update_reminder, "delete_reminder": delete_reminder, "list_all_reminders": list_all_reminders,
    # Memories
    "add_memory": add_memory, "update_memory": update_memory, "delete_memory": delete_memory, "search_memories": search_memories,
    # Journals
    "add_journal": add_journal, "update_journal": update_journal, "delete_journal": delete_journal, "search_journals": search_journals,
    # AI Actions (Scheduled Actions)
    "schedule_ai_action": schedule_ai_action, "update_ai_action": update_ai_action, "delete_ai_action": delete_ai_action, "list_ai_actions": list_ai_actions,
    # Daily Productivity Tools
    "task_for_day": task_for_day, "summary_of_day": summary_of_day, "ai_action_helper": ai_action_helper,
}




