# tool_collections/database_tools.py
# Collection of database-related tools - Enhanced with full Supabase support

import sys
import os

# Import original database modules
# First add user_input_files to path if not already there
user_input_files_dir = os.path.join('/workspace', 'user_input_files')
if user_input_files_dir not in sys.path:
    sys.path.append(user_input_files_dir)

# Now import the modules
import database_personal
import database_silent
import database_project

# Task-related tools
def register_tool(*args, **kwargs):
    """Placeholder decorator for proper module imports"""
    def decorator(func):
        return func
    return decorator

@register_tool(
    name="query_tasks",
    category="database",
    description="Query tasks from the database"
)
def query_tasks(supabase, user_id, **query_params):
    """Query tasks from the database with optional filters.
    
    Args:
        supabase: The Supabase client
        user_id: The ID of the user
        **query_params: Optional query parameters
            - completed: Filter by completion status
            - category: Filter by category
            - priority: Filter by priority
            - due_date_start: Filter by due date (start)
            - due_date_end: Filter by due date (end)
            - limit: Maximum number of tasks to return
            - offset: Offset for pagination
            
    Returns:
        List of tasks matching the query parameters
    """
    return database_personal.query_tasks(supabase, user_id, **query_params)

@register_tool(
    name="get_task_by_id",
    category="database",
    description="Get a task by ID"
)
def get_task_by_id(supabase, user_id, task_id):
    """Get a task by its ID.
    
    Args:
        supabase: The Supabase client
        user_id: The ID of the user
        task_id: The ID of the task
        
    Returns:
        The task with the specified ID, or None if not found
    """
    tasks = database_personal.query_tasks(supabase, user_id, id=task_id)
    return tasks[0] if tasks else None

@register_tool(
    name="find_task_by_title",
    category="database",
    description="Find a task by title (partial match)"
)
def find_task_by_title(supabase, user_id, title):
    """Find a task by its title (partial match).
    
    Args:
        supabase: The Supabase client
        user_id: The ID of the user
        title: The title to search for
        
    Returns:
        The first task with a matching title, or None if not found
    """
    tasks = database_personal.query_tasks(supabase, user_id, title_like=title)
    return tasks[0] if tasks else None

# Task operations
@register_tool(
    name="add_task",
    category="database",
    description="Add a new task"
)
def add_task(supabase, user_id, **kwargs):
    """Add a new task to the database.
    
    Args:
        supabase: The Supabase client
        user_id: The ID of the user
        **kwargs: Task properties (title, category, due_date, etc.)
        
    Returns:
        The newly created task
    """
    return database_personal.add_task_entry(supabase, user_id, **kwargs)

@register_tool(
    name="update_task",
    category="database",
    description="Update an existing task"
)
def update_task(supabase, user_id, task_id, patch):
    """Update an existing task.
    
    Args:
        supabase: The Supabase client
        user_id: The ID of the user
        task_id: The ID of the task to update
        patch: Dictionary of fields to update
        
    Returns:
        The updated task
    """
    return database_personal.update_task_entry(supabase, user_id, task_id, patch)

@register_tool(
    name="delete_task",
    category="database",
    description="Delete a task"
)
def delete_task(supabase, user_id, task_id):
    """Delete a task.
    
    Args:
        supabase: The Supabase client
        user_id: The ID of the user
        task_id: The ID of the task to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        database_personal.delete_task_entry(supabase, user_id, task_id)
        return True
    except Exception as e:
        print(f"ERROR in delete_task: {str(e)}")
        return False

# Silent mode tools
@register_tool(
    name="get_silent_status",
    category="database",
    description="Get the user's silent mode status"
)
def get_silent_status(supabase, user_id):
    """Get the user's silent mode status.
    
    Args:
        supabase: The Supabase client
        user_id: The ID of the user
        
    Returns:
        Dictionary with silent mode status information
    """
    session = database_silent.get_active_silent_session(supabase, user_id)
    return {
        "is_silent": session is not None,
        "session": session
    }

@register_tool(
    name="activate_silent_mode",
    category="database",
    description="Activate silent mode for the user"
)
def activate_silent_mode(supabase, user_id, duration_minutes=60, trigger_type='manual'):
    """Activate silent mode for the user.
    
    Args:
        supabase: The Supabase client
        user_id: The ID of the user
        duration_minutes: Duration in minutes for silent mode
        trigger_type: Type of trigger (manual, auto, etc.)
        
    Returns:
        The created silent session
    """
    return database_silent.create_silent_session(supabase, user_id, duration_minutes, trigger_type)

@register_tool(
    name="deactivate_silent_mode",
    category="database",
    description="Deactivate silent mode for the user"
)
def deactivate_silent_mode(supabase, user_id):
    """Deactivate silent mode for the user.
    
    Args:
        supabase: The Supabase client
        user_id: The ID of the user
        
    Returns:
        The ended silent session
    """
    session = database_silent.get_active_silent_session(supabase, user_id)
    if session:
        return database_silent.end_silent_session(supabase, session['id'], 'manual_exit')
    return None

# AI Actions tools
@register_tool(
    name="get_all_active_ai_actions",
    category="database",
    description="Get all active AI actions for the user"
)
def get_all_active_ai_actions(supabase, user_id):
    """Get all active AI actions for the user.
    
    Args:
        supabase: The Supabase client
        user_id: The ID of the user
        
    Returns:
        List of active AI actions
    """
    return database_personal.get_all_active_ai_actions(supabase, user_id)

# Reminder tools
@register_tool(
    name="get_all_reminders",
    category="database",
    description="Get all reminders for the user"
)
def get_all_reminders(supabase, user_id):
    """Get all reminders for the user.
    
    Args:
        supabase: The Supabase client
        user_id: The ID of the user
        
    Returns:
        List of reminders
    """
    return database_personal.get_all_reminders(supabase, user_id)

# Context functions
@register_tool(
    name="get_task_context_for_ai",
    category="database",
    description="Get task context for AI"
)
def get_task_context_for_ai(supabase, user_id):
    """Get task context for AI.
    
    Args:
        supabase: The Supabase client
        user_id: The ID of the user
        
    Returns:
        Task context dictionary
    """
    return database_personal.get_task_context_for_ai(supabase, user_id)

@register_tool(
    name="get_memory_context_for_ai",
    category="database",
    description="Get memory context for AI"
)
def get_memory_context_for_ai(supabase, user_id):
    """Get memory context for AI.
    
    Args:
        supabase: The Supabase client
        user_id: The ID of the user
        
    Returns:
        Memory context dictionary
    """
    return database_personal.get_memory_context_for_ai(supabase, user_id)

@register_tool(
    name="get_user_context_for_ai",
    category="database",
    description="Get user context for AI"
)
def get_user_context_for_ai(supabase, user_id):
    """Get user context for AI.
    
    Args:
        supabase: The Supabase client
        user_id: The ID of the user
        
    Returns:
        User context dictionary
    """
    return database_personal.get_user_context_for_ai(supabase, user_id)

# Conversation history tools
@register_tool(
    name="store_conversation_history",
    category="database",
    description="Store conversation history"
)
def store_conversation_history(supabase, user_id, history):
    """Store conversation history.
    
    Args:
        supabase: The Supabase client
        user_id: The ID of the user
        history: Conversation history
        
    Returns:
        True if successful, False otherwise
    """
    try:
        database_personal.store_conversation_history(supabase, user_id, history)
        return True
    except Exception as e:
        print(f"ERROR in store_conversation_history: {str(e)}")
        return False

@register_tool(
    name="get_conversation_history",
    category="database",
    description="Get conversation history"
)
def get_conversation_history(supabase, user_id):
    """Get conversation history.
    
    Args:
        supabase: The Supabase client
        user_id: The ID of the user
        
    Returns:
        Conversation history
    """
    return database_personal.get_conversation_history(supabase, user_id)
