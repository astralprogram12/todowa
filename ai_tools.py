# ai_tools.py (Corrected and Merged Version)

import re
from datetime import datetime
import pytz
from croniter import croniter
import time

# Local imports (ensure these files exist and are correct)
import database_personal
import database_silent

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
    """Adds a new task with mandatory category assignment and smart category management."""
    start_time = time.time()
    
    try:
        # Extract title for validation
        title = kwargs.get('title')
        if not title:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="add_task",
                entity_type="task",
                action_details={"execution_time_ms": execution_time_ms},
                success_status=False,
                error_details="Task title is required"
            )
            return {"status": "error", "message": "Task title is required."}
        
        # MANDATORY CATEGORY PROCESSING
        category_input = kwargs.get('category')
        notes = kwargs.get('notes')
        
        # Process category with prioritization logic
        category_result = validate_and_process_category(
            supabase=supabase,
            user_id=user_id,
            category_input=category_input,
            task_title=title,
            task_notes=notes
        )
        
        # Update kwargs with processed category
        kwargs['category'] = category_result['category']
        
        # Process list name and convert all keys to snake_case
        processed_kwargs = _process_list_name(supabase, user_id, kwargs)
        snake_case_args = _convert_keys_to_snake_case(processed_kwargs)

        # Standardize the 'difficulty' field to lowercase to match the database constraint
        if 'difficulty' in snake_case_args and isinstance(snake_case_args.get('difficulty'), str):
            snake_case_args['difficulty'] = snake_case_args['difficulty'].lower()
        
        # Create the task
        result = database_personal.add_task_entry(supabase, user_id, **snake_case_args)
        task_id = result.get('id') if result else None
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Log successful action with category information
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="add_task",
            entity_type="task",
            entity_id=task_id,
            action_details={
                "title": title,
                "category": category_result['category'],
                "category_status": category_result['status'],
                "category_message": category_result['message'],
                "parameters": snake_case_args,
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )
        
        # Enhanced success message with category information
        success_message = f"I've added the task: '{title}'."
        if category_result['status'] in ['auto_suggested', 'existing_partial_match', 'new_category']:
            success_message += f" {category_result['message']}"
        
        return {
            "status": "ok", 
            "message": success_message,
            "category_info": category_result
        }
        
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


def set_reminder(supabase, user_id, id=None, titleMatch=None, title=None, reminderTime=None, **task_kwargs):
    """Sets a reminder for a specific task. If the task doesn't exist, creates it first."""
    start_time = time.time()

    # Normalize: if `title` is passed, use it as `titleMatch`
    if title and not titleMatch:
        titleMatch = title

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
        
        if not titleMatch and not id:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="set_reminder",
                entity_type="reminder",
                action_details={"execution_time_ms": execution_time_ms},
                success_status=False,
                error_details="A task title or ID is required to set a reminder"
            )
            return {"status": "error", "message": "A task title or ID is required to set a reminder."}

        # Try to find existing task first
        task = _find_task(supabase, user_id, id=id, titleMatch=titleMatch)
        
        # If task doesn't exist and we have a titleMatch, create the task first
        if not task and titleMatch:
            print(f"TOOL: Task '{titleMatch}' not found. Creating task first before setting reminder.")
            
            try:
                # Prepare task creation arguments
                task_args = {
                    'title': titleMatch,
                    # Include any additional task properties passed as kwargs
                    **task_kwargs
                }
                
                # Process list name if provided
                processed_task_args = _process_list_name(supabase, user_id, task_args)
                snake_case_args = _convert_keys_to_snake_case(processed_task_args)
                
                # Standardize the 'difficulty' field to lowercase
                if 'difficulty' in snake_case_args and isinstance(snake_case_args.get('difficulty'), str):
                    snake_case_args['difficulty'] = snake_case_args['difficulty'].lower()
                
                # Create the task
                created_task = database_personal.add_task_entry(supabase, user_id, **snake_case_args)
                
                if created_task:
                    task = created_task
                    print(f"TOOL: Successfully created task '{titleMatch}' with ID {task.get('id')}")
                else:
                    raise Exception("Task creation returned no result")
                    
            except Exception as create_error:
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
                    error_details=f"Failed to create task '{titleMatch}' for reminder: {str(create_error)}"
                )
                return {"status": "error", "message": f"I couldn't create the task '{titleMatch}' to set a reminder. Error: {str(create_error)}"}
        
        # If we still don't have a task (e.g., when searching by ID that doesn't exist)
        if not task:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="set_reminder",
                entity_type="reminder",
                action_details={
                    "id": id,
                    "titleMatch": titleMatch,
                    "reminderTime": reminderTime,
                    "execution_time_ms": execution_time_ms
                },
                success_status=False,
                error_details=f"Task with ID '{id}' not found and cannot create task without title"
            )
            return {"status": "not_found", "message": f"I couldn't find the task with ID '{id}' and cannot create a task without a title."}

        # Now set the reminder on the task
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
                "task_was_created": not bool(_find_task(supabase, user_id, id=id, titleMatch=titleMatch)) if task else False,
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




def update_reminder(supabase, user_id, id=None, titleMatch=None, newReminderTime=None, **task_kwargs):
    """Updates the reminder time for a specific task. If the task doesn't exist, creates it first."""
    start_time = time.time()
    
    try:
        if not newReminderTime:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="update_reminder",
                entity_type="reminder",
                action_details={"execution_time_ms": execution_time_ms},
                success_status=False,
                error_details="A new reminder time is required"
            )
            return {"status": "error", "message": "A new reminder time is required."}
        
        if not titleMatch and not id:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="update_reminder",
                entity_type="reminder",
                action_details={"execution_time_ms": execution_time_ms},
                success_status=False,
                error_details="A task title or ID is required to update a reminder"
            )
            return {"status": "error", "message": "A task title or ID is required to update a reminder."}
        
        # Try to find existing task first
        task = _find_task(supabase, user_id, id=id, titleMatch=titleMatch)
        
        # If task doesn't exist and we have a titleMatch, create the task first
        if not task and titleMatch:
            print(f"TOOL: Task '{titleMatch}' not found. Creating task first before updating reminder.")
            
            try:
                # Prepare task creation arguments
                task_args = {
                    'title': titleMatch,
                    # Include any additional task properties passed as kwargs
                    **task_kwargs
                }
                
                # Process list name if provided
                processed_task_args = _process_list_name(supabase, user_id, task_args)
                snake_case_args = _convert_keys_to_snake_case(processed_task_args)
                
                # Standardize the 'difficulty' field to lowercase
                if 'difficulty' in snake_case_args and isinstance(snake_case_args.get('difficulty'), str):
                    snake_case_args['difficulty'] = snake_case_args['difficulty'].lower()
                
                # Create the task
                created_task = database_personal.add_task_entry(supabase, user_id, **snake_case_args)
                
                if created_task:
                    task = created_task
                    print(f"TOOL: Successfully created task '{titleMatch}' with ID {task.get('id')}")
                else:
                    raise Exception("Task creation returned no result")
                    
            except Exception as create_error:
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
                    error_details=f"Failed to create task '{titleMatch}' for reminder update: {str(create_error)}"
                )
                return {"status": "error", "message": f"I couldn't create the task '{titleMatch}' to update the reminder. Error: {str(create_error)}"}
        
        # If we still don't have a task (e.g., when searching by ID that doesn't exist)
        if not task:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="update_reminder",
                entity_type="reminder",
                action_details={
                    "id": id,
                    "titleMatch": titleMatch,
                    "newReminderTime": newReminderTime,
                    "execution_time_ms": execution_time_ms
                },
                success_status=False,
                error_details=f"Task with ID '{id}' not found and cannot create task without title"
            )
            return {"status": "not_found", "message": f"I couldn't find the task with ID '{id}' and cannot create a task without a title."}
        
        # Now update the reminder on the task
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
    """Deletes a reminder from a specific task. Only deletes from existing tasks."""
    start_time = time.time()
    
    try:
        if not titleMatch and not id:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="delete_reminder",
                entity_type="reminder",
                action_details={"execution_time_ms": execution_time_ms},
                success_status=False,
                error_details="A task title or ID is required to delete a reminder"
            )
            return {"status": "error", "message": "A task title or ID is required to delete a reminder."}
        
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
                    "id": id,
                    "execution_time_ms": execution_time_ms
                },
                success_status=False,
                error_details=f"Task '{titleMatch or id}' not found"
            )
            return {"status": "not_found", "message": f"I couldn't find a task matching '{titleMatch or id}'."}
        
        # Check if the task actually has a reminder to delete
        if not task.get('reminder_at'):
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
                success_status=True  # This is successful operation, just no reminder to delete
            )
            return {"status": "ok", "message": f"The task '{task['title']}' doesn't have a reminder set."}
        
        # Delete the reminder
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
                "id": id,
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

# --- Silent Mode Tools ---

def activate_silent_mode(supabase, user_id, **kwargs):
    """Activates silent mode for a specified duration."""
    start_time = time.time()
    
    try:
        # Extract duration from kwargs - support multiple formats
        duration_minutes = kwargs.get('duration_minutes') or kwargs.get('durationMinutes')
        duration_hours = kwargs.get('duration_hours') or kwargs.get('durationHours')
        trigger_type = kwargs.get('trigger_type', 'manual')
        
        # Convert hours to minutes if provided
        if duration_hours and not duration_minutes:
            duration_minutes = int(float(duration_hours) * 60)
        
        if not duration_minutes:
            return {
                "status": "error", 
                "message": "Please specify the duration for silent mode (e.g., 'go silent for 2 hours' or 'don't reply for 60 minutes')"
            }
        
        duration_minutes = int(duration_minutes)
        
        # Validate duration (max 12 hours)
        if duration_minutes > 720:  # 12 hours
            return {
                "status": "error", 
                "message": "Silent mode duration cannot exceed 12 hours. Please choose a shorter duration."
            }
        
        if duration_minutes < 5:  # Minimum 5 minutes
            return {
                "status": "error", 
                "message": "Silent mode duration must be at least 5 minutes."
            }
        
        # Create silent session
        session = database_silent.create_silent_session(supabase, user_id, duration_minutes, trigger_type)
        
        if not session:
            return {
                "status": "error", 
                "message": "Failed to activate silent mode. Please try again."
            }
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Log successful activation
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="activate_silent_mode",
            entity_type="silent_session",
            entity_id=session['id'],
            action_details={
                "duration_minutes": duration_minutes,
                "trigger_type": trigger_type,
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )
        
        # Calculate end time for display
        from datetime import datetime, timezone, timedelta
        end_time = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
        
        # Format duration for display
        if duration_minutes >= 60:
            hours = duration_minutes // 60
            remaining_mins = duration_minutes % 60
            if remaining_mins > 0:
                duration_text = f"{hours} hour{'s' if hours > 1 else ''} and {remaining_mins} minute{'s' if remaining_mins > 1 else ''}"
            else:
                duration_text = f"{hours} hour{'s' if hours > 1 else ''}"
        else:
            duration_text = f"{duration_minutes} minute{'s' if duration_minutes > 1 else ''}"
        
        return {
            "status": "ok",
            "message": f"🔇 **Silent mode activated** for {duration_text}\n\nI'll continue processing your requests but won't send replies until {end_time.strftime('%H:%M UTC')}. I'll send you a summary of all actions taken when silent mode ends.\n\n💡 **To exit early:** Say 'exit silent mode' or 'end silent mode'",
            "silent_session_id": session['id'],
            "end_time": end_time.isoformat()
        }
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="activate_silent_mode",
            entity_type="silent_session",
            action_details={"execution_time_ms": execution_time_ms},
            success_status=False,
            error_details=error_msg
        )
        
        return {"status": "error", "message": f"Failed to activate silent mode: {error_msg}"}

def deactivate_silent_mode(supabase, user_id, **kwargs):
    """Deactivates silent mode and returns accumulated actions summary."""
    start_time = time.time()
    
    try:
        # Get active silent session
        active_session = database_silent.get_active_silent_session(supabase, user_id)
        
        if not active_session:
            return {
                "status": "info",
                "message": "🔊 You're not currently in silent mode."
            }
        
        # End the session
        session_data = database_silent.end_silent_session(supabase, active_session['id'], 'manual_exit')
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Log deactivation
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="deactivate_silent_mode",
            entity_type="silent_session",
            entity_id=active_session['id'],
            action_details={
                "session_duration_minutes": active_session['duration_minutes'],
                "actions_accumulated": active_session['action_count'],
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )
        
        # Generate summary
        summary = generate_silent_mode_summary(session_data)
        
        return {
            "status": "ok",
            "message": f"🔊 **Silent mode ended**\n\n{summary}",
            "accumulated_actions": session_data['accumulated_actions'],
            "action_count": session_data['action_count']
        }
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="deactivate_silent_mode",
            entity_type="silent_session",
            action_details={"execution_time_ms": execution_time_ms},
            success_status=False,
            error_details=error_msg
        )
        
        return {"status": "error", "message": f"Failed to deactivate silent mode: {error_msg}"}

def get_silent_status(supabase, user_id, **kwargs):
    """Gets the current silent mode status for a user."""
    start_time = time.time()
    
    try:
        active_session = database_silent.get_active_silent_session(supabase, user_id)
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        if not active_session:
            return {
                "status": "ok",
                "message": "🔊 Silent mode is currently **off**",
                "is_silent": False
            }
        
        # Calculate remaining time
        from datetime import datetime, timezone, timedelta
        start_time_dt = datetime.fromisoformat(active_session['start_time'].replace('Z', '+00:00'))
        end_time = start_time_dt + timedelta(minutes=active_session['duration_minutes'])
        remaining = end_time - datetime.now(timezone.utc)
        
        if remaining.total_seconds() <= 0:
            # Session expired
            return {
                "status": "ok", 
                "message": "🔊 Silent mode is currently **off**",
                "is_silent": False
            }
        
        remaining_minutes = int(remaining.total_seconds() / 60)
        
        # Format remaining time
        if remaining_minutes >= 60:
            hours = remaining_minutes // 60
            mins = remaining_minutes % 60
            if mins > 0:
                time_text = f"{hours}h {mins}m"
            else:
                time_text = f"{hours}h"
        else:
            time_text = f"{remaining_minutes}m"
        
        return {
            "status": "ok",
            "message": f"🔇 Silent mode is **active**\n\n⏱️ **Remaining:** {time_text}\n📊 **Actions accumulated:** {active_session['action_count']}\n🚪 **To exit:** Say 'exit silent mode'",
            "is_silent": True,
            "remaining_minutes": remaining_minutes,
            "action_count": active_session['action_count'],
            "session_id": active_session['id']
        }
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        return {"status": "error", "message": f"Failed to check silent status: {error_msg}"}

def generate_silent_mode_summary(session_data):
    """Generates a human-readable summary of actions taken during silent mode."""
    try:
        if not session_data or not session_data.get('accumulated_actions'):
            return "📊 **Silent Mode Summary**\n\nNo actions were taken during this silent period."
        
        actions = session_data['accumulated_actions']
        total_actions = len(actions)
        
        # Categorize actions
        action_types = {}
        for action in actions:
            action_type = action.get('action_type', 'unknown')
            action_types[action_type] = action_types.get(action_type, 0) + 1
        
        # Calculate duration
        duration_minutes = session_data.get('duration_minutes', 0)
        if duration_minutes >= 60:
            hours = duration_minutes // 60
            remaining_mins = duration_minutes % 60
            if remaining_mins > 0:
                duration_text = f"{hours} hour{'s' if hours > 1 else ''} and {remaining_mins} minute{'s' if remaining_mins > 1 else ''}"
            else:
                duration_text = f"{hours} hour{'s' if hours > 1 else ''}"
        else:
            duration_text = f"{duration_minutes} minute{'s' if duration_minutes > 1 else ''}"
        
        # Build summary
        summary = f"📊 **Silent Mode Summary** ({duration_text})\n\n"
        summary += f"✅ **Total actions processed:** {total_actions}\n\n"
        
        if action_types:
            summary += "📈 **Actions by type:**\n"
            for action_type, count in sorted(action_types.items()):
                emoji = {
                    'add_task': '➕',
                    'update_task': '✏️',
                    'complete_task': '✅',
                    'delete_task': '🗑️',
                    'set_reminder': '⏰',
                    'add_memory': '🧠',
                    'search_memories': '🔍',
                    'add_journal': '📝',
                    'schedule_ai_action': '🤖'
                }.get(action_type, '🔹')
                
                action_name = action_type.replace('_', ' ').title()
                summary += f"  {emoji} {action_name}: {count}\n"
        
        summary += "\n🔊 **You're back online!** I'm ready to respond to your messages again."
        
        return summary
        
    except Exception as e:
        print(f"!!! ERROR in generate_silent_mode_summary: {e}")
        return "📊 **Silent Mode Summary**\n\nSummary generation failed, but silent mode has ended successfully."

def accumulate_silent_action(supabase, user_id, action_type, action_details):
    """Accumulates an action during silent mode instead of executing it."""
    try:
        active_session = database_silent.get_active_silent_session(supabase, user_id)
        
        if not active_session:
            return False  # Not in silent mode
        
        # Add action to accumulated actions
        action_data = {
            'action_type': action_type,
            'details': action_details,
            'user_input': action_details.get('user_input', '')
        }
        
        success = database_silent.add_action_to_silent_session(supabase, active_session['id'], action_data)
        
        if success:
            print(f"Action {action_type} accumulated in silent session {active_session['id']}")
        
        return success
        
    except Exception as e:
        print(f"!!! ERROR in accumulate_silent_action: {e}")
        return False

def handle_silent_mode(supabase, user_id, user_input, **kwargs):
    """Intelligently handles silent mode requests - activation, deactivation, or status checking."""
    start_time = time.time()
    
    try:
        input_lower = user_input.lower().strip()
        
        # Check for deactivation patterns
        deactivation_patterns = [
            r"\b(exit|end|stop|deactivate|turn\s+off)\s+silent",
            r"\b(back\s+online|resume\s+replies?)"
        ]
        
        for pattern in deactivation_patterns:
            if re.search(pattern, input_lower):
                return deactivate_silent_mode(supabase, user_id, **kwargs)
        
        # Check for status checking patterns
        status_patterns = [
            r"\b(silent\s+status|am\s+i\s+silent|in\s+silent\s+mode)",
            r"\b(silent\s+mode\s+status|check\s+silent)"
        ]
        
        for pattern in status_patterns:
            if re.search(pattern, input_lower):
                return get_silent_status(supabase, user_id, **kwargs)
        
        # Default to activation if none of the above matched
        # Extract duration if specified
        duration_match = re.search(r"\b(\d+)\s+(hour|hours|minute|minutes?|mins?)\b", input_lower)
        if duration_match:
            duration_value = int(duration_match.group(1))
            duration_unit = duration_match.group(2)
            
            if 'hour' in duration_unit:
                kwargs['duration_minutes'] = duration_value * 60
            else:  # minutes
                kwargs['duration_minutes'] = duration_value
        
        return activate_silent_mode(supabase, user_id, **kwargs)
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="handle_silent_mode",
            entity_type="silent_session",
            action_details={
                "user_input": user_input,
                "execution_time_ms": execution_time_ms
            },
            success_status=False,
            error_details=error_msg
        )
        
        return {"status": "error", "message": f"Failed to handle silent mode request: {error_msg}"}

def check_and_end_expired_silent_sessions(supabase):
    """Checks for and ends expired silent sessions. Used by scheduler."""
    try:
        expired_sessions = database_silent.get_expired_silent_sessions(supabase)
        ended_count = 0
        
        for session in expired_sessions:
            session_data = database_silent.end_silent_session(supabase, session['id'], 'expired')
            if session_data:
                ended_count += 1
                
                # Generate and send summary to user
                try:
                    user_phone = database_personal.get_user_phone_by_id(supabase, session['user_id'])
                    if user_phone:
                        summary = generate_silent_mode_summary(session_data)
                        # This would be sent via the messaging service
                        print(f"Silent mode summary ready for user {session['user_id']}: {summary[:100]}...")
                        
                except Exception as summary_error:
                    print(f"!!! ERROR sending silent mode summary: {summary_error}")
        
        return ended_count
        
    except Exception as e:
        print(f"!!! ERROR in check_and_end_expired_silent_sessions: {e}")
        return 0

# --- AI Interaction Features ---

def guide_tool(supabase, user_id, **kwargs):
    """Provides guidance on how to use the app when user is confused."""
    start_time = time.time()
    
    try:
        topic = kwargs.get('topic', '').lower()
        
        # Different guidance based on topic
        if 'task' in topic or 'todo' in topic:
            guidance = """📝 **Task Management Guide**

**🎯 Basic Task Operations:**
• **Add:** "Add task: Buy groceries" or "Remember: Call dentist"
• **List:** "Show my tasks" or "What do I need to do?"
• **Complete:** "Done: Buy groceries" or "Mark task 1 as completed"
• **Update:** "Change task 1 to: Buy organic groceries"
• **Delete:** "Remove task: Buy groceries"

**⏰ Reminders:**
• "Remind me to call mom at 3 PM"
• "Set reminder in 2 hours: Check email"

💡 **Tip:** I understand natural language, so speak naturally!"""
        
        elif 'remind' in topic or 'alarm' in topic:
            guidance = """⏰ **Reminder Guide**

**📅 Set Reminders:**
• "Remind me to call mom at 3 PM tomorrow"
• "Alert me in 30 minutes: Check the oven"
• "Set reminder for Dec 25th: Christmas dinner"

**🔧 Manage Reminders:**
• "Show my reminders" - List all active reminders
• "Cancel reminder for: Call mom"
• "Move reminder to 4 PM: Meeting with John"

💡 **Pro tip:** You can set reminders for both specific times and durations!"""
        
        elif 'silent' in topic or 'quiet' in topic:
            guidance = """🔇 **Silent Mode Guide**

**🤫 Activate Silent Mode:**
• "Don't reply for 1 hour" - Manual silent mode
• "Be quiet for 30 minutes"
• "Go silent until 3 PM"

**⚙️ Auto Silent Mode:**
• "Enable daily silent mode 7-11 AM" - Automatic daily quiet hours
• "Turn off auto silent mode"

**🚪 Exit Early:**
• "Exit silent mode" or "End silent mode"
• "Am I in silent mode?" - Check status

💡 **Note:** I'll process your requests during silent mode and send a summary when it ends!"""
        
        elif 'schedule' in topic or 'automat' in topic or 'recurring' in topic:
            guidance = """🤖 **Automation & Scheduling Guide**

**📅 Daily Summaries:**
• "Send me daily summary at 8 AM"
• "What should I focus on today?" - Instant task summary
• "What did I accomplish today?" - Completion summary

**🔄 Recurring Tasks:**
• "Create task 'Take vitamins' every day at 9 AM"
• "Weekly meeting reminder every Monday"

**⚙️ Manage Automations:**
• "Show my scheduled actions"
• "Cancel daily summary automation"

💡 **Popular:** Morning motivation and evening celebration summaries!"""
        
        else:
            # General guidance
            guidance = """🌟 **Welcome to your AI Assistant!**

**🚀 What I can help with:**

📝 **Task Management**
• Add, complete, update, and organize your tasks
• Set reminders for important deadlines
• Get daily summaries of what needs attention

🤖 **Smart Automation** 
• Schedule recurring reminders and summaries
• Get morning motivation and evening celebrations
• Create repeating tasks automatically

🔇 **Silent Mode**
• Go quiet for focused work periods
• Set automatic daily quiet hours
• Get summaries of activity when you return

💬 **Natural Conversation**
• Ask me anything - I understand natural language!
• Get advice on productivity and task organization
• Chat casually when you need a break

**🎯 Quick Start:**
1. Try: "Add task: Learn something new"
2. Ask: "What should I focus on today?"
3. Say: "Don't reply for 30 minutes" when you need focus time

**Need specific help?** Just ask me about any feature!"""
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Log the guidance request
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="guide",
            entity_type="help",
            action_details={
                "topic": topic,
                "guidance_type": "app_usage",
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )
        
        return {
            "status": "ok",
            "message": guidance
        }
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="guide",
            entity_type="help",
            action_details={"execution_time_ms": execution_time_ms},
            success_status=False,
            error_details=error_msg
        )
        
        return {"status": "error", "message": f"I had trouble providing guidance: {error_msg}"}

def chat_tool(supabase, user_id, **kwargs):
    """Handles casual conversation, random questions, and social interaction."""
    start_time = time.time()
    
    try:
        user_message = kwargs.get('message', '').lower()
        context = kwargs.get('context', '')
        
        # Detect conversation type and respond appropriately
        if any(greeting in user_message for greeting in ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']):
            responses = [
                "Hello! 👋 Great to see you! How can I help you stay productive today?",
                "Hi there! 😊 I'm here and ready to help you tackle your tasks!",
                "Hey! 🌟 What's on your agenda today? Let's make it happen!",
                "Good to see you! ✨ Ready to turn your goals into achievements?"
            ]
            import random
            response = random.choice(responses)
        
        elif any(word in user_message for word in ['test', 'testing', 'check']):
            response = "🧪 **Test successful!** ✅\n\nI'm working perfectly and ready to help! Try asking me to:\n• Add a task\n• Show your schedule\n• Set a reminder\n• Or just chat - I'm here for you! 😊"
        
        elif any(word in user_message for word in ['how are you', 'how do you feel', 'what\'s up']):
            response = "I'm doing great, thank you for asking! 🤖✨\n\nI'm energized and ready to help you be productive! Whether you need task management, reminders, or just want to chat - I'm here for you.\n\nHow are YOU doing today? Any goals you'd like to tackle? 🎯"
        
        elif any(word in user_message for word in ['thank you', 'thanks', 'appreciate']):
            response = "You're very welcome! 😊🙏\n\nIt's my pleasure to help you stay organized and productive. That's what I'm here for!\n\nIs there anything else I can assist you with today? ✨"
        
        elif any(word in user_message for word in ['joke', 'funny', 'humor', 'laugh']):
            jokes = [
                "Why don't tasks ever get lonely? Because they always stick together in a to-do list! 📝😄",
                "What did one reminder say to another? 'Don't worry, I've got your back... at 3 PM!' ⏰😊",
                "Why are productivity apps so optimistic? Because they always believe you'll get things DONE! ✅🎉",
                "What's a task's favorite music? Heavy metal... because it likes being COMPLETED! 🎵✅"
            ]
            import random
            response = random.choice(jokes)
        
        elif any(word in user_message for word in ['weather', 'time', 'date']):
            response = "🤖 I'm focused on helping you with tasks and productivity, so I don't have access to current weather or time data.\n\nBut I can help you:\n• Plan your day with task summaries\n• Set reminders for time-sensitive items\n• Schedule recurring actions\n\nWhat would you like to organize or plan today? 📅✨"
        
        elif any(word in user_message for word in ['bored', 'nothing to do', 'free time']):
            response = "🌟 **Feeling free? Perfect time to be productive!**\n\nHere are some ideas:\n• ✅ Catch up on any pending tasks\n• 🧹 Organize your task list\n• 📝 Plan tomorrow's priorities\n• 🎯 Set some new goals\n• 🤖 Set up automations to make life easier\n\nOr just chat with me - I'm always here! What sounds interesting to you?"
        
        elif any(word in user_message for word in ['random', 'anything', 'whatever', 'idk', "don't know"]):
            responses = [
                "🎲 **Random productivity tip:** The 2-minute rule - if something takes less than 2 minutes, do it now instead of adding it to your task list!\n\nWhat's one quick thing you could tackle right now? ⚡",
                "🌟 **Fun fact:** Your brain loves checking things off lists because it releases dopamine - that's why task completion feels so satisfying!\n\nWant to get that dopamine hit? Show me your tasks! 📝✨",
                "💡 **Productivity thought:** The best time to plant a tree was 20 years ago. The second best time is now!\n\nWhat 'tree' (goal/project) would you like to start planting today? 🌱",
                "🎯 **Daily wisdom:** You don't have to be perfect, you just have to be consistent.\n\nWhat's one small thing you can do consistently? Let's make it a task! 📈"
            ]
            import random
            response = random.choice(responses)
        
        else:
            # General conversational response
            response = "😊 I hear you! While I love our chat, I'm especially good at helping with productivity and organization.\n\n🤔 **What's on your mind?**\n• Need help with tasks or reminders?\n• Want to plan your day?\n• Looking for productivity tips?\n• Just want to keep chatting?\n\nI'm here for whatever you need! ✨"
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Log the chat interaction
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="chat",
            entity_type="conversation",
            action_details={
                "user_message": kwargs.get('message', '')[:100],  # First 100 chars for privacy
                "response_type": "casual_conversation",
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )
        
        return {
            "status": "ok",
            "message": response
        }
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="chat",
            entity_type="conversation",
            action_details={"execution_time_ms": execution_time_ms},
            success_status=False,
            error_details=error_msg
        )
        
        return {"status": "error", "message": "😅 I got a bit tongue-tied there! What would you like to chat about?"}

def expert_tool(supabase, user_id, **kwargs):
    """Provides expert advice on task management, productivity, and goal achievement."""
    start_time = time.time()
    
    try:
        advice_topic = kwargs.get('topic', '').lower()
        context = kwargs.get('context', '')
        
        # Provide expert advice based on the topic
        if any(word in advice_topic for word in ['combine', 'merge', 'group', 'organize tasks']):
            advice = """🧠 **Expert Advice: Task Organization & Combining**

**🎯 Smart Task Combination Strategies:**

**1. Context Grouping** 📍
• Combine tasks by location: "Grocery store tasks" → Buy milk + pharmacy + dry cleaning
• Batch by tool needed: All computer tasks together

**2. Time-Boxing** ⏰
• Small tasks (< 15min): Batch 3-4 together
• "Quick wins session": Email replies + bills + calls

**3. Energy Matching** ⚡
• High-energy tasks: Creative work, problem-solving
• Low-energy tasks: Administrative, organizing, emails

**4. Project Clustering** 📊
• Group related tasks under main projects
• Example: "Website Launch" → Design + Content + Testing + Deploy

**💡 Pro Tips:**
• Don't combine more than 3-5 small tasks
• Keep one "Big Rock" (important task) separate
• Use task priorities to avoid combining urgent with non-urgent

**Want me to help organize your current tasks?** Show me your list!"""
        
        elif any(word in advice_topic for word in ['first step', 'start', 'begin', 'getting started']):
            advice = """🚀 **Expert Advice: First Steps to Success**

**📋 The SMART Start Framework:**

**1. Start Ridiculously Small** 🐣
• Goal: "Get fit" → First step: "Put on gym shoes"
• Goal: "Learn coding" → First step: "Open coding tutorial"
• Goal: "Organize house" → First step: "Clear one drawer"

**2. Make it Specific** 🎯
• Vague: "Work on project" → Specific: "Write project outline"
• Vague: "Be healthier" → Specific: "Drink one extra glass of water"

**3. Time-bound** ⏰
• "Today I will..." instead of "Someday I'll..."
• Set mini-deadlines: "By 3 PM, I'll have..."

**4. Link to Existing Habits** 🔗
• "After I drink my morning coffee, I'll..."
• "Before I check email, I'll..."

**🎯 The 2-Minute Rule:**
If the first step takes less than 2 minutes, do it NOW!

**Example Breakdown:**
• Goal: "Launch business"
• Step 1: "Write one business idea on paper" (2 min)
• Step 2: "Google one competitor" (5 min)
• Step 3: "List 3 potential customers" (10 min)

**Ready to break down your goal?** Tell me what you want to achieve!"""
        
        elif any(word in advice_topic for word in ['priority', 'important', 'urgent', 'focus']):
            advice = """⚡ **Expert Advice: Priority & Focus Mastery**

**📊 The Eisenhower Matrix:**

**Quadrant 1: DO FIRST** 🔥
• Urgent + Important → Handle immediately
• Examples: Emergencies, crises, deadlines

**Quadrant 2: SCHEDULE** 📅
• Important but Not Urgent → Plan these!
• Examples: Exercise, learning, relationship building
• **This is where success lives!**

**Quadrant 3: DELEGATE** 👥
• Urgent but Not Important → Give to others
• Examples: Some emails, calls, interruptions

**Quadrant 4: ELIMINATE** 🗑️
• Neither urgent nor important → Stop doing these
• Examples: Social media scrolling, busywork

**🎯 Daily Focus Strategy:**

**The Big 3 Rule:**
1. Choose 3 most important tasks for today
2. Complete Big 3 before anything else
3. Everything else is bonus

**Energy Management:**
• Peak energy hours → Most important/creative work
• Low energy hours → Administrative tasks
• Match task difficulty to your energy level

**💡 Pro Questions to Ask:**
• "What moves me closer to my goals?"
• "What happens if I don't do this today?"
• "Am I being productive or just busy?"

**Want a priority assessment of your tasks?** Share your list!"""
        
        elif any(word in advice_topic for word in ['procrastination', 'motivation', 'stuck', 'overwhelmed']):
            advice = """💪 **Expert Advice: Beating Procrastination & Overwhelm**

**🧠 Why We Procrastinate:**
• Task feels too big → Break it down
• Perfectionism → Aim for "good enough" first
• Fear of failure → Focus on learning, not perfection
• Lack of clarity → Define the exact next step

**⚡ Instant Action Techniques:**

**1. The 5-Minute Rule**
• Commit to just 5 minutes
• Often momentum carries you forward
• If not, you still made progress!

**2. Swiss Cheese Method**
• Poke random holes in big tasks
• Do any small part that appeals to you
• Gradually the task becomes manageable

**3. Implementation Intention**
• "When X happens, I will do Y"
• "When I sit at my desk, I will open my task list"
• "When I feel overwhelmed, I will write down 3 tasks"

**🛠️ Overwhelm Busters:**

**Brain Dump Technique:**
1. Write EVERYTHING down (10 minutes)
2. Categorize: Must do, Should do, Could do
3. Pick ONE from "Must do"
4. Ignore the rest until #3 is done

**The NOT-To-Do List:**
• List things you'll STOP doing
• Often more powerful than adding tasks
• Examples: Check email less, say no to meetings

**🎯 Mindset Shifts:**
• "I have to" → "I choose to"
• "This is hard" → "This will help me grow"
• "I'm behind" → "I'm exactly where I need to be"

**Feeling stuck on something specific?** Tell me about it!"""
        
        elif any(word in advice_topic for word in ['habit', 'routine', 'consistency', 'daily']):
            advice = """🔄 **Expert Advice: Building Bulletproof Habits**

**🧱 The Habit Stack Formula:**

**After [EXISTING HABIT], I will [NEW HABIT]**
• After I pour coffee, I'll review my daily tasks
• After I sit at my desk, I'll write down my top 3 priorities
• After I brush my teeth, I'll plan tomorrow's schedule

**📈 The 1% Better Principle:**
• Don't aim for perfection, aim for consistency
• Small improvements compound exponentially
• Better to do 5 minutes daily than 1 hour weekly

**🎯 Habit Design Rules:**

**1. Start Stupidly Small** 🐣
• Want to exercise? → Start with 1 push-up
• Want to read? → Start with 1 page
• Want to meditate? → Start with 1 breath

**2. Make it Obvious** 👀
• Put your task list where you'll see it
• Set visual reminders
• Use your phone wallpaper as a cue

**3. Make it Attractive** ✨
• Pair habits with things you enjoy
• "After I complete my daily tasks, I can have coffee"
• Celebrate small wins immediately

**4. Make it Easy** ⚡
• Reduce friction to starting
• Prepare everything the night before
• Use the 2-minute rule

**🔗 Keystone Habits** (These trigger other good habits):
• Morning routine → Sets up whole day
• Exercise → Improves energy for everything
• Daily planning → Increases productivity
• Evening review → Prepares next day

**📊 Tracking Success:**
• Track the behavior, not just the outcome
• Use a simple "X" on a calendar
• Never miss twice in a row
• Focus on consistency over perfection

**Ready to build a habit?** What area of your life needs consistency?"""
        
        elif any(word in advice_topic for word in ['goal', 'achieve', 'success', 'plan']):
            advice = """🎯 **Expert Advice: Goal Achievement Mastery**

**🏗️ The SMART-ER Goals Framework:**

**SMART:**
• **S**pecific: Clear and well-defined
• **M**easurable: Trackable progress
• **A**chievable: Realistic given resources
• **R**elevant: Aligned with your values
• **T**ime-bound: Has a deadline

**ER (The game-changers):**
• **E**valuate: Regular progress reviews
• **R**eadjust: Adapt based on what you learn

**🎨 Goal Visualization Technique:**
1. **Outcome Goals** → "Lose 20 pounds"
2. **Process Goals** → "Exercise 4x/week"
3. **Identity Goals** → "Become a healthy person"

**Focus most on Process + Identity!**

**⚡ The Goal Pyramid:**
```
     🏆 Outcome Goal (What)
    🎯🎯 Process Goals (How)
   📋📋📋 Daily Actions (When)
  ⚡⚡⚡⚡ Habits (Automatic)
```

**🔄 Monthly Goal Review Questions:**
• What's working well?
• What obstacles did I hit?
• What do I need to adjust?
• What support do I need?
• Am I still excited about this goal?

**📈 Success Accelerators:**

**1. Implementation Intentions**
• "I will [BEHAVIOR] at [TIME] in [LOCATION]"
• "I will work on my goal at 9 AM in my home office"

**2. If-Then Planning**
• "If X happens, then I will do Y"
• "If I feel unmotivated, then I'll do just 5 minutes"

**3. Social Accountability**
• Tell someone your goal
• Regular check-ins
• Join communities with similar goals

**4. Environment Design**
• Make success easier
• Remove barriers and distractions
• Set up visual reminders

**🚀 Quick Start Protocol:**
1. Write your goal in present tense: "I am..."
2. Identify the first 3 actions needed
3. Schedule them in your calendar
4. Set up your environment for success
5. Track daily progress

**What goal are you working toward?** Let's break it down together!"""
        
        else:
            # General productivity advice
            advice = """🎯 **Expert Productivity Consultation**

**🚀 Core Principles of High Performance:**

**1. Focus on Systems, Not Goals** 📈
• Goals are what you want to achieve
• Systems are what you do daily
• Example: Don't just want "6-pack abs", build a "daily exercise system"

**2. The Power of Constraint** ⚡
• Limitation breeds creativity
• Too many options = decision paralysis
• Pick 3 priorities max per day

**3. Energy Management > Time Management** 🔋
• Match high-energy to important tasks
• Protect your peak performance hours
• Take breaks before you need them

**4. Progress Compounds** 📊
• 1% better daily = 37x better in a year
• Consistency beats intensity
• Small improvements add up exponentially

**🛠️ Advanced Productivity Strategies:**

**Time Blocking** 📅
• Assign specific times to specific tasks
• Include buffer time for unexpected items
• Block time for both work and rest

**The Two-List Strategy (Buffett's Method)** 📝
1. List your top 25 goals/tasks
2. Circle your top 5 most important
3. The other 20? Avoid at all costs until top 5 are done

**Pareto Principle (80/20 Rule)** ⚡
• 80% of results come from 20% of efforts
• Identify your high-impact activities
• Double down on what works

**🎯 Questions for Reflection:**
• What would make the biggest difference in my life?
• What am I avoiding that I know I should do?
• What would I do if I had unlimited confidence?
• How can I make this easier for myself?

**🔥 Ready for Specific Advice?**
Tell me about:
• Your biggest challenge right now
• A goal you're working toward
• An area where you feel stuck
• What success looks like for you

I'll give you targeted strategies!"""
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Log the expert consultation
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="expert_advice",
            entity_type="consultation",
            action_details={
                "advice_topic": advice_topic,
                "consultation_type": "productivity_expert",
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )
        
        return {
            "status": "ok",
            "message": advice
        }
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="expert_advice",
            entity_type="consultation",
            action_details={"execution_time_ms": execution_time_ms},
            success_status=False,
            error_details=error_msg
        )
        
        return {"status": "error", "message": f"I had trouble providing expert advice: {error_msg}"}


# --- Utility Functions ---

def convert_utc_to_user_timezone(supabase, user_id, utc_time_str):
    """Converts UTC time string to user's timezone for display purposes."""
    start_time = time.time()
    
    try:
        # Get user timezone from context
        user_context = database_personal.get_user_context_for_ai(supabase, user_id)
        user_timezone = user_context.get('timezone', 'UTC')
        
        if user_timezone == 'UTC':
            return utc_time_str  # No conversion needed
        
        # Parse the UTC time string
        if utc_time_str.endswith('Z'):
            utc_time_str = utc_time_str[:-1] + '+00:00'
        
        utc_time = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
        
        # Convert to user timezone
        user_tz = pytz.timezone(user_timezone)
        user_time = utc_time.astimezone(user_tz)
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="convert_timezone",
            entity_type="utility",
            action_details={
                "utc_time": utc_time_str,
                "user_timezone": user_timezone,
                "converted_time": user_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )
        
        return user_time.strftime('%Y-%m-%d %H:%M:%S %Z')
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="convert_timezone",
            entity_type="utility",
            action_details={
                "utc_time": utc_time_str,
                "execution_time_ms": execution_time_ms
            },
            success_status=False,
            error_details=error_msg
        )
        
        # Return original time if conversion fails
        return utc_time_str


def ai_confusion_helper(supabase, user_id, content_description, user_input=None, context_hint=None):
    """Helps AI determine where to store information when confused about classification.
    
    This tool should ONLY be called when the AI is genuinely confused about whether
    something should be stored as a task, memory, journal entry, etc.
    """
    start_time = time.time()
    
    try:
        # Analyze the content to provide guidance
        content_lower = (content_description or "").lower()
        user_input_lower = (user_input or "").lower()
        context_lower = (context_hint or "").lower()
        
        all_text = f"{content_lower} {user_input_lower} {context_lower}"
        
        # Decision tree based on content analysis
        recommendations = []
        confidence_scores = {}
        
        # Task indicators
        task_keywords = ["do", "complete", "finish", "deadline", "due", "remind", "schedule", 
                        "todo", "task", "action", "need to", "have to", "must", "should"]
        task_score = sum(1 for keyword in task_keywords if keyword in all_text)
        
        # Memory indicators (personal facts, preferences, relationships)
        memory_keywords = ["remember", "my", "i am", "i like", "i don't like", "preference", 
                          "favorite", "hate", "love", "important", "note", "fact", "personal"]
        memory_score = sum(1 for keyword in memory_keywords if keyword in all_text)
        
        # Journal indicators (experiences, thoughts, reflections)
        journal_keywords = ["today", "yesterday", "happened", "felt", "think", "believe", 
                           "experience", "learned", "discovered", "reflection", "idea", "thought"]
        journal_score = sum(1 for keyword in journal_keywords if keyword in all_text)
        
        confidence_scores = {
            "task": task_score,
            "memory": memory_score,
            "journal": journal_score
        }
        
        # Determine the best recommendation
        max_score = max(confidence_scores.values())
        
        if max_score == 0:
            # No clear indicators, provide general guidance
            guidance = {
                "primary_recommendation": "memory",  # Default to memory for unclear content
                "reasoning": "Content doesn't clearly fit specific categories. Consider using memory for factual information, journal for experiences/thoughts, or task for actionable items.",
                "alternatives": ["journal", "task"],
                "confidence": "low"
            }
        else:
            # Find the category with highest score
            best_category = max(confidence_scores.keys(), key=lambda k: confidence_scores[k])
            
            reasoning_map = {
                "task": "Content contains action-oriented language suggesting something needs to be done.",
                "memory": "Content appears to be personal information or facts worth remembering.",
                "journal": "Content seems to be experiential, reflective, or thought-based."
            }
            
            alternatives = [cat for cat in confidence_scores.keys() if cat != best_category and confidence_scores[cat] > 0]
            confidence = "high" if max_score >= 3 else "medium" if max_score >= 2 else "low"
            
            guidance = {
                "primary_recommendation": best_category,
                "reasoning": reasoning_map[best_category],
                "alternatives": alternatives or ["Consider other categories if this doesn't feel right"],
                "confidence": confidence
            }
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="ai_confusion_helper",
            entity_type="utility",
            action_details={
                "content_description": content_description,
                "user_input": user_input,
                "context_hint": context_hint,
                "recommendation": guidance["primary_recommendation"],
                "confidence": guidance["confidence"],
                "scores": confidence_scores,
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )
        
        return {
            "status": "ok",
            "guidance": guidance,
            "message": f"Based on the content analysis, I recommend storing this as a {guidance['primary_recommendation']}. {guidance['reasoning']}"
        }
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="ai_confusion_helper",
            entity_type="utility",
            action_details={
                "content_description": content_description,
                "execution_time_ms": execution_time_ms
            },
            success_status=False,
            error_details=error_msg
        )
        
        return {
            "status": "error", 
            "message": f"I had trouble analyzing the content: {error_msg}",
            "guidance": {
                "primary_recommendation": "memory",
                "reasoning": "Defaulting to memory due to analysis error.",
                "alternatives": ["journal", "task"],
                "confidence": "low"
            }
        }

# === CATEGORY MANAGEMENT SYSTEM ===
# Enhanced category management with existing category prioritization

def get_existing_categories(supabase, user_id, limit=50):
    """Retrieve all existing categories used by the user, sorted by frequency."""
    start_time = time.time()
    
    try:
        # Query all tasks to get category usage statistics
        tasks = database_personal.query_tasks(supabase, user_id, completed=False, limit=1000)
        
        if not tasks:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="get_existing_categories",
                entity_type="utility",
                action_details={"execution_time_ms": execution_time_ms, "categories_found": 0},
                success_status=True
            )
            return []
        
        # Count category usage frequency
        category_counts = {}
        for task in tasks:
            category = task.get('category')
            if category and category.strip():
                category = category.strip().lower()
                category_counts[category] = category_counts.get(category, 0) + 1
        
        # Sort by frequency (most used first)
        sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        categories = [cat[0] for cat in sorted_categories[:limit]]
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="get_existing_categories",
            entity_type="utility",
            action_details={
                "execution_time_ms": execution_time_ms,
                "categories_found": len(categories),
                "top_categories": categories[:5]
            },
            success_status=True
        )
        
        return categories
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="get_existing_categories",
            entity_type="utility",
            action_details={"execution_time_ms": execution_time_ms},
            success_status=False,
            error_details=error_msg
        )
        
        return []


def _calculate_category_match_score(content, category):
    """Calculate how well a category matches the task content (0.0 to 1.0)."""
    content = content.lower()
    category = category.lower()
    
    # Direct category name match
    if category in content:
        return 1.0
    
    # Define category keyword mappings
    category_keywords = {
        'work': ['work', 'job', 'office', 'project', 'task', 'deadline', 'meeting', 'team', 'client', 'business'],
        'personal': ['personal', 'family', 'home', 'house', 'self', 'me', 'my'],
        'health': ['health', 'doctor', 'medical', 'appointment', 'exercise', 'gym', 'workout', 'medicine'],
        'finance': ['money', 'pay', 'bill', 'budget', 'bank', 'finance', 'expense', 'invoice', 'payment'],
        'shopping': ['buy', 'shop', 'store', 'purchase', 'grocery', 'market', 'mall'],
        'travel': ['travel', 'trip', 'vacation', 'flight', 'hotel', 'book', 'ticket'],
        'social': ['friend', 'social', 'party', 'event', 'dinner', 'lunch', 'meet'],
        'learning': ['learn', 'study', 'read', 'book', 'course', 'education', 'training'],
        'maintenance': ['fix', 'repair', 'clean', 'maintain', 'service', 'replace'],
        'creative': ['create', 'design', 'art', 'write', 'blog', 'creative', 'draw'],
        'communication': ['call', 'email', 'message', 'contact', 'reach out', 'follow up'],
        'planning': ['plan', 'organize', 'schedule', 'prepare', 'arrange', 'setup']
    }
    
    # Check if this category has keyword mappings
    keywords = category_keywords.get(category, [category])
    
    # Calculate match score based on keyword presence
    matches = sum(1 for keyword in keywords if keyword in content)
    if matches > 0:
        return min(0.8, matches * 0.3)  # Max 0.8 for keyword matches
    
    # Partial string matching
    if any(part in content for part in category.split()):
        return 0.4
    
    return 0.0


def _infer_category_from_content(title, notes=None):
    """Infer an appropriate category name from task content."""
    content = f"{title} {notes or ''}".lower()
    
    # Category inference rules based on keywords
    inference_rules = [
        (['meeting', 'call', 'standup', 'sync', 'review', 'discussion'], 'work'),
        (['doctor', 'appointment', 'medical', 'health', 'gym', 'exercise'], 'health'),
        (['buy', 'purchase', 'shop', 'store', 'grocery', 'market'], 'shopping'),
        (['pay', 'bill', 'invoice', 'budget', 'bank', 'finance'], 'finance'),
        (['clean', 'fix', 'repair', 'maintain', 'service'], 'maintenance'),
        (['travel', 'trip', 'vacation', 'flight', 'hotel', 'book'], 'travel'),
        (['learn', 'study', 'read', 'course', 'training', 'education'], 'learning'),
        (['family', 'home', 'house', 'personal'], 'personal'),
        (['create', 'design', 'write', 'blog', 'art', 'creative'], 'creative'),
        (['email', 'message', 'contact', 'follow up', 'reach out'], 'communication'),
        (['plan', 'organize', 'schedule', 'prepare', 'arrange'], 'planning'),
        (['friend', 'social', 'party', 'event', 'dinner', 'lunch'], 'social')
    ]
    
    # Find best matching category
    for keywords, category in inference_rules:
        if any(keyword in content for keyword in keywords):
            return category
    
    # Default fallback
    return 'general'


def suggest_best_category(supabase, user_id, task_title, task_notes=None, existing_categories=None):
    """Suggest the best matching existing category for a task, or recommend creating a new one."""
    start_time = time.time()
    
    try:
        # Get existing categories if not provided
        if existing_categories is None:
            existing_categories = get_existing_categories(supabase, user_id)
        
        if not existing_categories:
            # No existing categories - will need to create a new one
            suggested_category = _infer_category_from_content(task_title, task_notes)
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="suggest_best_category",
                entity_type="utility",
                action_details={
                    "task_title": task_title,
                    "suggested_category": suggested_category,
                    "match_type": "new_inferred",
                    "execution_time_ms": execution_time_ms
                },
                success_status=True
            )
            
            return {
                "status": "suggest_new",
                "suggested_category": suggested_category,
                "match_confidence": "medium",
                "existing_matches": [],
                "reasoning": f"Inferred '{suggested_category}' from task content. No existing categories found."
            }
        
        # Analyze task content
        content_to_analyze = f"{task_title} {task_notes or ''}".lower()
        
        # Score existing categories against task content
        category_scores = []
        for category in existing_categories:
            score = _calculate_category_match_score(content_to_analyze, category)
            if score > 0:
                category_scores.append((category, score))
        
        # Sort by score
        category_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Determine best recommendation
        if category_scores and category_scores[0][1] >= 0.6:  # High confidence match
            best_match = category_scores[0][0]
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="suggest_best_category",
                entity_type="utility",
                action_details={
                    "task_title": task_title,
                    "suggested_category": best_match,
                    "match_type": "existing_high_confidence",
                    "match_score": category_scores[0][1],
                    "execution_time_ms": execution_time_ms
                },
                success_status=True
            )
            
            return {
                "status": "existing_match",
                "suggested_category": best_match,
                "match_confidence": "high",
                "existing_matches": [cat[0] for cat in category_scores[:3]],
                "reasoning": f"Strong match with existing '{best_match}' category based on task content."
            }
            
        elif category_scores and category_scores[0][1] >= 0.3:  # Medium confidence match
            best_match = category_scores[0][0]
            alternatives = [cat[0] for cat in category_scores[:3]]
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="suggest_best_category",
                entity_type="utility",
                action_details={
                    "task_title": task_title,
                    "suggested_category": best_match,
                    "match_type": "existing_medium_confidence",
                    "match_score": category_scores[0][1],
                    "alternatives": alternatives,
                    "execution_time_ms": execution_time_ms
                },
                success_status=True
            )
            
            return {
                "status": "existing_match",
                "suggested_category": best_match,
                "match_confidence": "medium",
                "existing_matches": alternatives,
                "reasoning": f"Possible match with '{best_match}'. Consider alternatives: {', '.join(alternatives[:2])}."
            }
        
        else:  # No good matches - suggest creating new category
            suggested_category = _infer_category_from_content(task_title, task_notes)
            top_existing = [cat[0] for cat in category_scores[:3]] if category_scores else existing_categories[:3]
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="suggest_best_category",
                entity_type="utility",
                action_details={
                    "task_title": task_title,
                    "suggested_category": suggested_category,
                    "match_type": "new_inferred_no_good_match",
                    "existing_options": top_existing,
                    "execution_time_ms": execution_time_ms
                },
                success_status=True
            )
            
            return {
                "status": "suggest_new",
                "suggested_category": suggested_category,
                "match_confidence": "low",
                "existing_matches": top_existing,
                "reasoning": f"No strong match found. Suggest new category '{suggested_category}' or choose from existing: {', '.join(top_existing[:2])}."
            }
            
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="suggest_best_category",
            entity_type="utility",
            action_details={
                "task_title": task_title,
                "execution_time_ms": execution_time_ms
            },
            success_status=False,
            error_details=error_msg
        )
        
        # Fallback - infer from content
        fallback_category = _infer_category_from_content(task_title, task_notes)
        return {
            "status": "error_fallback",
            "suggested_category": fallback_category,
            "match_confidence": "low",
            "existing_matches": [],
            "reasoning": f"Error occurred during analysis. Fallback suggestion: '{fallback_category}'."
        }


def validate_and_process_category(supabase, user_id, category_input, task_title, task_notes=None):
    """Validate a category input and return the final category to use.
    
    This function prioritizes existing categories and handles category creation.
    """
    start_time = time.time()
    
    try:
        # If no category provided, suggest one
        if not category_input or not category_input.strip():
            suggestion = suggest_best_category(supabase, user_id, task_title, task_notes)
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="validate_and_process_category",
                entity_type="utility",
                action_details={
                    "task_title": task_title,
                    "category_input": "empty",
                    "suggestion_status": suggestion["status"],
                    "final_category": suggestion["suggested_category"],
                    "execution_time_ms": execution_time_ms
                },
                success_status=True
            )
            
            return {
                "status": "auto_suggested",
                "category": suggestion["suggested_category"],
                "suggestion_info": suggestion,
                "message": f"Auto-assigned category '{suggestion['suggested_category']}' based on task content."
            }
        
        # Clean and normalize input
        category_input = category_input.strip().lower()
        
        # Get existing categories
        existing_categories = get_existing_categories(supabase, user_id)
        
        # Check for exact match with existing category
        for existing_cat in existing_categories:
            if existing_cat.lower() == category_input:
                execution_time_ms = int((time.time() - start_time) * 1000)
                _log_action_with_timing(
                    supabase=supabase,
                    user_id=user_id,
                    action_type="validate_and_process_category",
                    entity_type="utility",
                    action_details={
                        "task_title": task_title,
                        "category_input": category_input,
                        "final_category": existing_cat,
                        "match_type": "exact_existing",
                        "execution_time_ms": execution_time_ms
                    },
                    success_status=True
                )
                
                return {
                    "status": "existing_match",
                    "category": existing_cat,
                    "message": f"Using existing category '{existing_cat}'."
                }
        
        # Check for partial matches with existing categories
        partial_matches = []
        for existing_cat in existing_categories:
            if (category_input in existing_cat.lower() or 
                existing_cat.lower() in category_input or
                _calculate_category_match_score(category_input, existing_cat) > 0.5):
                partial_matches.append(existing_cat)
        
        if partial_matches:
            # Use the first (most frequently used) partial match
            best_match = partial_matches[0]
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            _log_action_with_timing(
                supabase=supabase,
                user_id=user_id,
                action_type="validate_and_process_category",
                entity_type="utility",
                action_details={
                    "task_title": task_title,
                    "category_input": category_input,
                    "final_category": best_match,
                    "match_type": "partial_existing",
                    "partial_matches": partial_matches,
                    "execution_time_ms": execution_time_ms
                },
                success_status=True
            )
            
            return {
                "status": "existing_partial_match",
                "category": best_match,
                "alternatives": partial_matches,
                "message": f"Using similar existing category '{best_match}' (matches '{category_input}')."
            }
        
        # No existing match - create new category
        # Capitalize properly for consistency
        new_category = category_input.title()
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="validate_and_process_category",
            entity_type="utility",
            action_details={
                "task_title": task_title,
                "category_input": category_input,
                "final_category": new_category,
                "match_type": "new_category",
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )
        
        return {
            "status": "new_category",
            "category": new_category,
            "message": f"Created new category '{new_category}'."
        }
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="validate_and_process_category",
            entity_type="utility",
            action_details={
                "task_title": task_title,
                "category_input": category_input,
                "execution_time_ms": execution_time_ms
            },
            success_status=False,
            error_details=error_msg
        )
        
        # Fallback to inferred category
        fallback_category = _infer_category_from_content(task_title, task_notes)
        return {
            "status": "error_fallback",
            "category": fallback_category,
            "message": f"Error processing category. Using fallback: '{fallback_category}'."
        }


def list_user_categories(supabase, user_id, limit=20):
    """List all categories used by the user, sorted by frequency."""
    start_time = time.time()
    
    try:
        categories = get_existing_categories(supabase, user_id, limit)
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="list_user_categories",
            entity_type="utility",
            action_details={
                "categories_count": len(categories),
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )
        
        if not categories:
            return {"status": "ok", "message": "No categories found. Categories will be created automatically when you add tasks.", "categories": []}
        
        category_list = ', '.join(categories[:10])  # Show top 10
        message = f"Your categories (by usage): {category_list}"
        if len(categories) > 10:
            message += f" and {len(categories) - 10} more."
        
        return {
            "status": "ok",
            "message": message,
            "categories": categories
        }
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="list_user_categories",
            entity_type="utility",
            action_details={"execution_time_ms": execution_time_ms},
            success_status=False,
            error_details=error_msg
        )
        
        return {"status": "error", "message": f"Failed to list categories: {error_msg}"}

# --- INTELLIGENT CONTEXT CLASSIFIER (Central Decision Tree Orchestrator) ---

def intelligent_context_classifier(supabase, user_id, user_input, conversation_context=None):
    """
    The central orchestrating function that implements the intelligent decision tree logic.
    Analyzes user input and routes to the appropriate function based on intent classification.
    
    Returns a classification result with recommended action and confidence score.
    """
    start_time = time.time()
    
    try:
        if not user_input:
            return {
                "status": "error",
                "message": "No input provided for classification",
                "classification": "unknown",
                "confidence": 0.0
            }
        
        # Normalize input for analysis
        input_lower = user_input.lower().strip()
        context_lower = (conversation_context or "").lower()
        full_text = f"{input_lower} {context_lower}"
        
        # Initialize classification scores
        classification_scores = {
            "task": 0.0,
            "reminder": 0.0,
            "memory": 0.0,
            "journal": 0.0,
            "guide": 0.0,
            "expert": 0.0,
            "chat": 0.0,
            "ai_action": 0.0,
            "silent": 0.0
        }
        
        # DECISION TREE BRANCH 1: COMMAND/PREFERENCE DETECTION → MEMORIES (HIGHEST PRIORITY)
        memory_patterns = [
            # Behavioral commands (high priority)
            r"\b(never|always|don't)\s+(ask|remind|tell|show|do)",
            r"\b(remember|note)\s+(that\s+)?i\s+(prefer|like|hate|want)",
            r"\bmy\s+(preference|style|way)\b",
            r"\bfrom\s+now\s+on\b",
            r"\b(whenever|every\s+time)\s+i\b",
            # Personal information
            r"\bi\s+(am|live|work|prefer|like|hate)\b",
            r"\bmy\s+(name|email|phone|address|favorite)\b",
            # Instructions and rules  
            r"\b(when\s+i\s+say|if\s+i\s+say|make\s+sure)\b",
            r"\b(rule|instruction|guideline)\b",
            # Strong behavioral indicators
            r"\bjust\s+(do|tell|show)\b",
            r"\balways\s+(remember|do|make|ensure)\b"
        ]
        
        for pattern in memory_patterns:
            if re.search(pattern, full_text):
                classification_scores["memory"] += 0.5  # Increased weight for memory
        
        # Boost memory score for explicit memory keywords
        memory_keywords = ["remember", "note", "preference", "always", "never", "my", "i am", "i like", "i hate"]
        memory_score = sum(0.2 for keyword in memory_keywords if keyword in full_text)  # Increased weight
        classification_scores["memory"] += memory_score
        
        # DECISION TREE BRANCH 2: SILENT MODE DETECTION → ACTIVATE/DEACTIVATE SILENT MODE (HIGH PRIORITY)
        silent_patterns = [
            # Silent mode activation
            r"\b(go\s+silent|activate\s+silent|turn\s+on\s+silent)\b",
            r"\b(silent\s+mode|quiet\s+mode)\b",
            r"\b(don't\s+reply|stop\s+replying|no\s+replies?)\b",
            r"\b(silent\s+for|quiet\s+for)\b",
            # Silent mode deactivation
            r"\b(exit\s+silent|end\s+silent|stop\s+silent)\b",
            r"\b(deactivate\s+silent|turn\s+off\s+silent)\b",
            r"\b(back\s+online|resume\s+replies?)\b",
            # Silent mode status
            r"\b(silent\s+status|am\s+i\s+silent|in\s+silent\s+mode)\b",
            r"\b(silent\s+mode\s+status)\b"
        ]
        
        for pattern in silent_patterns:
            if re.search(pattern, full_text):
                classification_scores["silent"] += 0.7  # High priority for silent mode
        
        # Boost silent score for explicit silent keywords
        silent_keywords = ["silent", "quiet", "don't reply", "stop replying", "no replies"]
        silent_score = sum(0.3 for keyword in silent_keywords if keyword in full_text)
        classification_scores["silent"] += silent_score
        
        # DECISION TREE BRANCH 3: GENERAL KNOWLEDGE DETECTION → JOURNAL
        journal_patterns = [
            r"\bi\s+(learned|discovered|found\s+out|read)\s+(that)?\b",
            r"\b(did\s+you\s+know|fun\s+fact|interesting)\b",
            r"\b(today\s+i|yesterday\s+i|this\s+week\s+i)\b",
            r"\b(meeting\s+notes|research\s+shows|study\s+found)\b",
            r"\b(brainstorming|idea|concept|thought)\b"
        ]
        
        for pattern in journal_patterns:
            if re.search(pattern, full_text):
                classification_scores["journal"] += 0.3
        
        journal_keywords = ["learned", "discovered", "fact", "research", "study", "meeting", "idea", "thought"]
        journal_score = sum(0.15 for keyword in journal_keywords if keyword in full_text)
        classification_scores["journal"] += journal_score
        
        # DECISION TREE BRANCH 4: RECURRING ACTION DETECTION → AI ACTIONS (HIGH PRIORITY)
        ai_action_patterns = [
            r"\b(every|daily|weekly|monthly|each)\s+(day|week|month|morning|evening)\b",
            r"\b(recurring|repeat|schedule|automat)\b",
            r"\b(every\s+\d+\s+(days|weeks|months))\b",
            r"\b(daily\s+reminder|weekly\s+summary)\b",
            # Specific recurring reminder patterns
            r"\bevery\s+\w+\s+(morning|evening|afternoon).*remind\b",
            r"\b(daily|weekly|monthly).*remind\b"
        ]
        
        for pattern in ai_action_patterns:
            if re.search(pattern, full_text):
                classification_scores["ai_action"] += 0.6  # Higher weight for AI actions
        
        # DECISION TREE BRANCH 5: REMINDER DETECTION → SET REMINDERS 
        # Note: This comes AFTER ai_action to avoid conflicts
        reminder_patterns = [
            r"\b(remind|alert|notify)\s+me\b",
            r"\b(at|on|by|before|after)\s+\d",
            r"\b(tomorrow|today|next\s+week|monday|tuesday|wednesday|thursday|friday)\b",
            r"\b(meeting|appointment|call|deadline)\b",
            r"\b(in\s+\d+\s+(minutes|hours|days))\b"
        ]
        
        # Only apply reminder patterns if AI action score is low
        if classification_scores["ai_action"] < 0.3:
            for pattern in reminder_patterns:
                if re.search(pattern, full_text):
                    classification_scores["reminder"] += 0.4
        else:
            # Reduce reminder score when AI action is detected
            for pattern in reminder_patterns:
                if re.search(pattern, full_text):
                    classification_scores["reminder"] += 0.2  # Lower weight when AI action present
        
        # DECISION TREE BRANCH 6: TASK DETECTION → ADD TASK
        task_patterns = [
            r"\b(add\s+task|create\s+task|new\s+task)\b",
            r"\b(i\s+need\s+to|i\s+have\s+to|i\s+should|i\s+must)\b",
            r"\b(do|complete|finish|work\s+on)\b",
            r"\b(todo|to-do|task)\b",
            r"\b(project|assignment|deadline)\b"
        ]
        
        for pattern in task_patterns:
            if re.search(pattern, full_text):
                classification_scores["task"] += 0.3
        
        # DECISION TREE BRANCH 7: GUIDE MODE DETECTION
        guide_patterns = [
            r"\b(how\s+do\s+i|help\s+me|i\s+don't\s+know)\b",
            r"\b(what\s+can\s+you\s+do|how\s+does\s+this\s+work)\b",
            r"\b(explain|show\s+me|teach\s+me)\b",
            r"\b(confused|lost|new\s+user)\b"
        ]
        
        for pattern in guide_patterns:
            if re.search(pattern, full_text):
                classification_scores["guide"] += 0.4
        
        # DECISION TREE BRANCH 8: EXPERT MODE DETECTION
        expert_patterns = [
            r"\b(what's\s+the\s+best\s+way|how\s+should\s+i|any\s+tips)\b",
            r"\b(advice|strategy|recommend)\b",
            r"\b(productive|organize|prioritize|focus)\b",
            r"\b(goal|achievement|success)\b"
        ]
        
        for pattern in expert_patterns:
            if re.search(pattern, full_text):
                classification_scores["expert"] += 0.4
        
        # DECISION TREE BRANCH 9: CHAT MODE DETECTION
        chat_patterns = [
            r"\b(hello|hi|hey|good\s+morning|good\s+afternoon)\b",
            r"\b(how\s+are\s+you|what's\s+up|thank\s+you|thanks)\b",
            r"\b(test|testing|check|random)\b",
            r"\b(joke|funny|bored|chat)\b"
        ]
        
        for pattern in chat_patterns:
            if re.search(pattern, full_text):
                classification_scores["chat"] += 0.3
        
        # Calculate final classification
        max_score = max(classification_scores.values())
        
        if max_score < 0.2:
            # Very low confidence - use confusion helper
            classification = "confusion"
            confidence = 0.1
            recommended_action = "ai_confusion_helper"
        else:
            # Find the highest scoring classification
            classification = max(classification_scores.keys(), key=lambda k: classification_scores[k])
            confidence = min(max_score, 1.0)  # Cap at 1.0
            
            # Map classification to recommended action
            action_mapping = {
                "task": "add_task",
                "reminder": "set_reminder", 
                "memory": "add_memory",
                "journal": "add_journal",
                "guide": "guide",
                "expert": "expert", 
                "chat": "chat",
                "ai_action": "schedule_ai_action",
                "silent": "handle_silent_mode"
            }
            recommended_action = action_mapping.get(classification, "chat")
        
        # Determine confidence level
        if confidence >= 0.8:
            confidence_level = "high"
        elif confidence >= 0.6:
            confidence_level = "medium"
        elif confidence >= 0.4:
            confidence_level = "low"
        else:
            confidence_level = "confused"
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Log the classification
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="intelligent_context_classifier",
            entity_type="classification",
            action_details={
                "user_input": user_input[:200],  # Truncate for logging
                "classification": classification,
                "confidence": confidence,
                "confidence_level": confidence_level,
                "recommended_action": recommended_action,
                "all_scores": classification_scores,
                "execution_time_ms": execution_time_ms
            },
            success_status=True
        )
        
        return {
            "status": "ok",
            "classification": classification,
            "confidence": confidence,
            "confidence_level": confidence_level,
            "recommended_action": recommended_action,
            "all_scores": classification_scores,
            "user_input": user_input,
            "reasoning": f"Classified as '{classification}' with {confidence_level} confidence ({confidence:.2f})"
        }
        
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        _log_action_with_timing(
            supabase=supabase,
            user_id=user_id,
            action_type="intelligent_context_classifier",
            entity_type="classification",
            action_details={
                "user_input": user_input[:200] if user_input else "",
                "execution_time_ms": execution_time_ms
            },
            success_status=False,
            error_details=error_msg
        )
        
        return {
            "status": "error",
            "message": f"Classification failed: {error_msg}",
            "classification": "unknown",
            "confidence": 0.0
        }

# --- The Master Dictionary of All Available Tools ---
AVAILABLE_TOOLS = {
    # Core Decision Tree Function
    "intelligent_context_classifier": intelligent_context_classifier,
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
    # Silent Mode Tools
    "activate_silent_mode": activate_silent_mode, "deactivate_silent_mode": deactivate_silent_mode, "get_silent_status": get_silent_status,
    "handle_silent_mode": handle_silent_mode,
    # AI Interaction Features
    "guide": guide_tool, "chat": chat_tool, "expert": expert_tool,
    # Utility Functions
    "convert_utc_to_user_timezone": convert_utc_to_user_timezone, "ai_confusion_helper": ai_confusion_helper,
    # Category Management
    "list_user_categories": list_user_categories,
}




