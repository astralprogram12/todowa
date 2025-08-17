# ai_tools.py (Corrected and Merged Version)

import re
from datetime import datetime
import pytz
from croniter import croniter

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

# --- Task & Reminder Tools (Corrected Signatures) ---
# ai_tools.py

def add_task(supabase, user_id, **kwargs):
    """Adds a new task."""
    # FIX: Process list name and convert all keys to snake_case
    processed_kwargs = _process_list_name(supabase, user_id, kwargs)
    snake_case_args = _convert_keys_to_snake_case(processed_kwargs)

    # --- START CORRECTION ---
    # Standardize the 'difficulty' field to lowercase to match the database constraint.
    if 'difficulty' in snake_case_args and isinstance(snake_case_args.get('difficulty'), str):
        snake_case_args['difficulty'] = snake_case_args['difficulty'].lower()
    # --- END CORRECTION ---
    
    database_personal.add_task_entry(supabase, user_id, **snake_case_args)
    return {"status": "ok", "message": f"I've added the task: '{kwargs.get('title')}'."}


def delete_task(supabase, user_id=None, task_id=None, title=None, titleMatch=None, **kwargs):
    title = title or titleMatch
    if not task_id and not title:
        return {"message": "No valid task_id(s) or title provided."}

    query = supabase.table("tasks").delete().eq("user_id", user_id)
    if task_id:
        query = query.eq("id", task_id)
    else:
        query = query.eq("title", title)
    result = query.execute()

    return {"message": f"Deleted task(s) matching {task_id or title}"}


def update_task(supabase, user_id, task_id=None, titleMatch=None, patch=None):
    if not task_id and not titleMatch:
        return {"error": "No task identifier provided"}

    # Find task by task_id or titleMatch
    query = supabase.table("tasks").select("*").eq("user_id", user_id)
    if task_id:
        query = query.eq("id", task_id)
    elif titleMatch:
        query = query.ilike("title", f"%{titleMatch}%")

    task = query.execute()
    if not task.data:
        return {"error": "Task not found"}

    # Apply patch (can be title, due_date, priority, etc.)
    update_fields = {}
    if patch:
        update_fields.update(patch)

    if not update_fields:
        return {"error": "No fields to update"}

    result = supabase.table("tasks").update(update_fields).eq("id", task.data[0]["id"]).execute()

    return {"success": True, "updated": result.data}


def complete_task(
    supabase,
    user_id=None,
    task_ids=None,       # list of task IDs
    title=None,
    titleMatch=None,
    **kwargs
):
    """
    Mark one or multiple tasks as completed ("done").
    Supports task_ids (list), exact title, or partial titleMatch.
    """
    if not task_ids and not title and not titleMatch:
        return {"message": "No valid identifiers provided."}

    query = supabase.table("tasks").update({"status": "done"}).eq("user_id", user_id)

    updated = []

    try:
        if task_ids:
            # Handle multiple IDs
            result = query.in_("id", task_ids).execute()
            updated.extend([t["id"] for t in result.data])
        elif title:
            # Exact title match
            result = query.eq("title", title).execute()
            updated.extend([t["id"] for t in result.data])
        elif titleMatch:
            # Partial title match (may update multiple tasks!)
            result = query.ilike("title", f"%{titleMatch}%").execute()
            updated.extend([t["id"] for t in result.data])

        if not updated:
            return {"message": "No tasks matched the criteria."}

        return {"message": f"Marked {len(updated)} task(s) as done", "updated": updated}

    except Exception as e:
        return {"error": str(e)}


def set_reminder(supabase, user_id, id=None, titleMatch=None, reminderTime=None):
    """Sets a reminder for a specific task."""
    if not reminderTime:
        return {"status": "error", "message": "A specific reminder time is required."}
        
    task = _find_task(supabase, user_id, id=id, titleMatch=titleMatch)
    if not task:
        return {"status": "not_found", "message": f"I couldn't find the task '{titleMatch}' to set a reminder for."}
        
    patch = {"reminder_at": reminderTime, "reminder_sent": False}
    database_personal.update_task_entry(supabase, user_id, task['id'], patch)
    return {"status": "ok", "message": f"Reminder set for '{task['title']}'."}

def update_reminder(supabase, user_id, id=None, titleMatch=None, newReminderTime=None):
    """Updates the reminder time for a specific task."""
    task = _find_task(supabase, user_id, id=id, titleMatch=titleMatch)
    if not task:
        return {"status": "not_found", "message": f"I couldn't find a task matching '{titleMatch}'."}
    
    patch = {"reminder_at": newReminderTime, "reminder_sent": False}
    database_personal.update_task_entry(supabase, user_id, task['id'], patch)
    return {"status": "ok", "message": f"I've updated the reminder for '{task['title']}'."}

def delete_reminder(supabase, user_id, id=None, titleMatch=None):
    """Deletes a reminder from a specific task."""
    task = _find_task(supabase, user_id, id=id, titleMatch=titleMatch)
    if not task:
        return {"status": "not_found", "message": f"I couldn't find a task matching '{titleMatch}'."}
    
    patch = {"reminder_at": None, "reminder_sent": None}
    database_personal.update_task_entry(supabase, user_id, task['id'], patch)
    return {"status": "ok", "message": f"I've removed the reminder from '{task['title']}'."}

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


# --- Memory Tools (from refactored code) ---

def add_memory(supabase, user_id, title=None, content=None):
    if not title: return {"status": "error", "message": "A title for the memory is required."}
    database_personal.add_memory_entry(supabase, user_id, title, content)
    return {"status": "ok", "message": f"I'll remember that: '{title}'."}

def update_memory(supabase, user_id, titleMatch=None, patch=None):
    if not titleMatch or not patch: return {"status": "error", "message": "A title and data to update are required."}
    memory = database_personal.find_memory_by_title(supabase, user_id, titleMatch)
    if not memory: return {"status": "not_found", "message": f"I couldn't find a memory matching '{titleMatch}'."}
    database_personal.update_memory_entry(supabase, user_id, memory['id'], patch)
    return {"status": "ok", "message": f"I've updated the memory: '{memory['title']}'."}

def delete_memory(supabase, user_id, titleMatch=None):
    if not titleMatch: return {"status": "error", "message": "Please tell me the title of the memory to delete."}
    memory = database_personal.find_memory_by_title(supabase, user_id, titleMatch)
    if not memory: return {"status": "not_found", "message": f"I couldn't find a memory matching '{titleMatch}'."}
    database_personal.delete_memory_entry(supabase, user_id, memory['id'])
    return {"status": "ok", "message": f"I have deleted the memory: '{memory['title']}'."}

def search_memories(supabase, user_id, query=None):
    if not query: return "Please tell me what you want to search for."
    results = database_personal.search_memory_entries(supabase, user_id, query)
    if not results: return f"I couldn't find any memories matching '{query}'."
    response_lines = [f"I found {len(results)} memories matching '{query}':"]
    for i, item in enumerate(results):
        line = f"{i+1}. **{item['title']}**"
        if item.get('content'): line += f": {item['content']}"
        response_lines.append(line)
    return "\n".join(response_lines)


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
    if not all([action_type, schedule, description]):
        return {"status": "error", "message": "Action type, schedule, and description are required."}
    
    user_context = database_personal.get_user_context_for_ai(supabase, user_id)
    limit = user_context.get('schedule_limit', 5)
    if database_personal.count_active_ai_actions(supabase, user_id) >= limit:
        return {"status": "limit_reached", "message": f"You have reached your plan's limit of {limit} AI Actions."}

    cron_schedule, error = _build_and_validate_schedule_spec(schedule)
    if error: return {"status": "error", "message": error}

    user_tz = pytz.timezone(user_context.get("timezone", "UTC"))
    next_run_utc = croniter(cron_schedule, datetime.now(user_tz)).get_next(datetime).astimezone(pytz.utc)
    
    database_personal.add_ai_action(supabase, user_id, action_type, cron_schedule, next_run_utc.isoformat(), user_tz.zone, description, payload)
    return {"status": "ok", "message": f"I've scheduled '{description}' for you."}

def update_ai_action(supabase, user_id, descriptionMatch=None, patch=None):
    if not descriptionMatch or not patch: return {"status": "error", "message": "A description and data to update are required."}

    all_actions = database_personal.get_all_active_ai_actions(supabase, user_id)
    action_to_update = _find_item_from_list(all_actions, descriptionMatch, key="description")

    if not action_to_update: return {"status": "not_found", "message": f"I couldn't find an AI Action matching '{descriptionMatch}'."}
    
    if 'schedule' in patch:
        new_schedule = patch.pop('schedule')
        cron_schedule, error = _build_and_validate_schedule_spec(new_schedule)
        if error: return {"status": "error", "message": error}
        patch['schedule_spec'] = cron_schedule
        user_context = database_personal.get_user_context_for_ai(supabase, user_id)
        user_tz = pytz.timezone(user_context.get("timezone", "UTC"))
        patch['next_run_at'] = croniter(cron_schedule, datetime.now(user_tz)).get_next(datetime).astimezone(pytz.utc).isoformat()

    database_personal.update_ai_action_entry(supabase, user_id, action_to_update['id'], patch)
    return {"status": "ok", "message": f"I've updated the AI Action: '{action_to_update['description']}'."}

def delete_ai_action(supabase, user_id, descriptionMatch=None):
    if not descriptionMatch: return {"status": "error", "message": "Please provide the description of the AI Action to delete."}
    all_actions = database_personal.get_all_active_ai_actions(supabase, user_id)
    action_to_delete = _find_item_from_list(all_actions, descriptionMatch, key="description")
    
    if not action_to_delete: return {"status": "not_found", "message": f"I couldn't find an AI Action matching '{descriptionMatch}'."}
    
    database_personal.delete_ai_action_entry(supabase, user_id, action_to_delete['id'])
    return {"status": "ok", "message": f"I have deleted the AI Action: '{action_to_delete['description']}'."}

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

# --- The Master Dictionary of All Available Tools ---
AVAILABLE_TOOLS = {
    # Tasks
    "add_task": add_task, "update_task": update_task, "delete_task": delete_task, "complete_task": complete_task,
    # Reminders for Tasks
    "set_reminder": set_reminder, "update_reminder": update_reminder, "delete_reminder": delete_reminder, "list_all_reminders": list_all_reminders,
    # Memories
    "add_memory": add_memory, "update_memory": update_memory, "delete_memory": delete_memory, "search_memories": search_memories,
    # AI Actions (Scheduled Actions)
    "schedule_ai_action": schedule_ai_action, "update_ai_action": update_ai_action, "delete_ai_action": delete_ai_action, "list_ai_actions": list_ai_actions,
}





