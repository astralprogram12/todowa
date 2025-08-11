# ai_tools.py (Corrected)

import database
from datetime import datetime
import re

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
    Helper to find a SINGLE task by ID first, then by titleMatch.
    Returns a single dictionary or None.
    """
    if id:
        tasks = database.query_tasks(supabase, user_id, id=id)
        if tasks:
            return tasks[0]  # <-- FIX 1: Return the first object from the list
    if titleMatch:
        tasks = database.query_tasks(supabase, user_id, title_like=titleMatch)
        if tasks:
            return tasks[0]  # <-- FIX 2: Return the first object from the list
    return None

def _find_list_id_by_name(supabase, user_id, list_name):
    """Helper to find a list's ID by its name."""
    if not list_name:
        return None
    lists = database.query_lists(supabase, user_id, name=list_name)
    if lists:
        return lists[0]['id']  # <-- FIX 3: Return the 'id' from the first object
    print(f"TOOL: Could not find list with name '{list_name}'")
    return None

def _process_list_name(supabase, user_id, args):
    """Checks for a 'list' key (a name) and replaces it with 'list_id'."""
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
    """Tool to add a task, with list name translation."""
    print(f"TOOL: add_task with raw args {kwargs}")
    processed_kwargs = _process_list_name(supabase, user_id, kwargs)
    snake_case_args = _convert_keys_to_snake_case(processed_kwargs)
    print(f"TOOL: Translated args to {snake_case_args}")
    return database.add_task_entry(supabase, user_id, **snake_case_args)

def update_task(supabase, user_id, id=None, titleMatch=None, patch=None):
    """Tool to update a task, with list name translation."""
    print(f"TOOL: update_task matching {{id:'{id}', titleMatch:'{titleMatch}'}} with raw patch {patch}")
    if not patch:
        return {"status": "error", "message": "Patch data is required."}
    
    # task_to_update is now a single dictionary or None, thanks to the fix in _find_task
    task_to_update = _find_task(supabase, user_id, id, titleMatch)
    if not task_to_update:
        return {"status": "not_found", "message": "Could not find task to update."}

    processed_patch = _process_list_name(supabase, user_id, patch)
    snake_case_patch = _convert_keys_to_snake_case(processed_patch)
    print(f"TOOL: Translated patch to {snake_case_patch}")
    # No error will happen here now
    return database.update_task_entry(supabase, user_id, task_to_update['id'], snake_case_patch)

def complete_task(supabase, user_id, id=None, titleMatch=None, done=True):
    """Tool to mark a task as done or todo."""
    print(f"TOOL: complete_task matching {{id:'{id}', titleMatch:'{titleMatch}'}}")
    # task_to_complete is now a single dictionary or None
    task_to_complete = _find_task(supabase, user_id, id, titleMatch)
    if not task_to_complete:
        return {"status": "not_found", "message": "Could not find task to complete."}
    
    status = "done" if done else "todo"
    patch = {"status": status}
    if status == 'done':
        patch['completed_at'] = datetime.utcnow().isoformat()

    # No error will happen here now
    return database.update_task_entry(supabase, user_id, task_to_complete['id'], patch)

def delete_task(supabase, user_id, id=None, titleMatch=None):
    """Tool to find and delete a task."""
    print(f"TOOL: delete_task matching {{id:'{id}', titleMatch:'{titleMatch}'}}")
    # task_to_delete is now a single dictionary or None
    task_to_delete = _find_task(supabase, user_id, id, titleMatch)
    if not task_to_delete:
        if not id and not titleMatch:
            return {"status": "error", "message": "You must provide a specific task title or ID to delete."}
        return {"status": "not_found", "message": f"Could not find task '{titleMatch}' to delete."}

    # No errors will happen here now
    database.delete_task_entry(supabase, user_id, task_to_delete['id'])
    return {"status": "ok", "message": f"Deleted task '{task_to_delete['title']}'."}

AVAILABLE_TOOLS = {
    "add_task": add_task,
    "update_task": update_task,
    "complete_task": complete_task,
    "delete_task": delete_task,
}