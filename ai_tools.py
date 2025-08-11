# ai_tools.py

import database
from datetime import datetime
import re

def _to_snake_case(s):
    return re.sub(r'(?<!^)(?=[A-Z])', '_', s).lower()

def _convert_keys_to_snake_case(d):
    if not isinstance(d, dict):
        return d
    return {_to_snake_case(k): _convert_keys_to_snake_case(v) for k, v in d.items()}

def _find_task(supabase, user_id, id=None, titleMatch=None):
    if id:
        tasks = database.query_tasks(supabase, user_id, id=id)
        if tasks:
            return tasks[0]
    if titleMatch:
        tasks = database.query_tasks(supabase, user_id, title_like=titleMatch)
        if tasks:
            return tasks[0]
    return None

def _find_list_id_by_name(supabase, user_id, list_name):
    if not list_name:
        return None
    lists = database.query_lists(supabase, user_id, name=list_name)
    if lists:
        return lists[0]['id']
    print(f"TOOL: Could not find list with name '{list_name}'")
    return None

def _process_list_name(supabase, user_id, args):
    if 'list' in args:
        list_name = args.pop('list')
        if list_name:
            list_id = _find_list_id_by_name(supabase, user_id, list_name)
            if list_id:
                args['list_id'] = list_id
        else:
            args['list_id'] = None
    return args

def add_task(supabase, user_id, **kwargs):
    processed_kwargs = _process_list_name(supabase, user_id, kwargs)
    snake_case_args = _convert_keys_to_snake_case(processed_kwargs)
    return database.add_task_entry(supabase, user_id, **snake_case_args)

def update_task(supabase, user_id, id=None, titleMatch=None, patch=None):
    if not patch:
        return {"status": "error", "message": "Patch data is required."}
    
    task_to_update = _find_task(supabase, user_id, id, titleMatch)
    if not task_to_update:
        return {"status": "not_found", "message": "Could not find task to update."}

    processed_patch = _process_list_name(supabase, user_id, patch)
    snake_case_patch = _convert_keys_to_snake_case(processed_patch)
    return database.update_task_entry(supabase, user_id, task_to_update['id'], snake_case_patch)

def complete_task(supabase, user_id, id=None, titleMatch=None, done=True):
    task_to_complete = _find_task(supabase, user_id, id, titleMatch)
    if not task_to_complete:
        return {"status": "not_found", "message": "Could not find task to complete."}
    
    status = "done" if done else "todo"
    patch = {"status": status}
    if status == 'done':
        patch['completed_at'] = datetime.utcnow().isoformat()

    return database.update_task_entry(supabase, user_id, task_to_complete['id'], patch)

def delete_task(supabase, user_id, id=None, titleMatch=None):
    task_to_delete = _find_task(supabase, user_id, id, titleMatch)
    if not task_to_delete:
        if not id and not titleMatch:
            return {"status": "error", "message": "You must provide a specific task title or ID to delete."}
        return {"status": "not_found", "message": f"Could not find task '{titleMatch}' to delete."}

    database.delete_task_entry(supabase, user_id, task_to_delete['id'])
    return {"status": "ok", "message": f"Deleted task '{task_to_delete['title']}'."}

def set_reminder(supabase, user_id, id=None, titleMatch=None, reminderTime=None): # <-- NEW
    """Tool to find a task and set a reminder for it."""
    if not reminderTime:
        return {"status": "error", "message": "A specific reminder time is required."}
    
    task_to_remind = _find_task(supabase, user_id, id, titleMatch)
    if not task_to_remind:
        return {"status": "not_found", "message": "Could not find the task to set a reminder for."}
        
    patch = {
        "reminder_at": reminderTime,
        "reminder_sent": False
    }
    
    return database.update_task_entry(supabase, user_id, task_to_remind['id'], patch)


AVAILABLE_TOOLS = {
    "add_task": add_task,
    "update_task": update_task,
    "complete_task": complete_task,
    "delete_task": delete_task,
    "set_reminder": set_reminder, # <-- NEW
}
