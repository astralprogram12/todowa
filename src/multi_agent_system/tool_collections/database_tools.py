# tool_collections/database_tools.py
# Collection of database-related tools - Enhanced with full Supabase support

import sys
import os

# --- [FIX] Correctly Add Project Root to Python Path ---
# This block dynamically finds the project's root directory (where run.py is)
# and adds it to the system path. This is the correct way to ensure that
# modules like 'database_personal' can be imported from anywhere in the project.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.append(project_root)
# --- End of Fix ---

# --- Import original database modules with error handling ---
try:
    import database_personal
    import database_silent
    import database_project
except ImportError as e:
    print(f"FATAL ERROR in database_tools.py: Could not import a database module.")
    print(f"This is likely a file path issue. The path '{project_root}' was added to sys.path.")
    print(f"Original Error: {e}")
    # This is a critical failure, so we re-raise the exception to stop the app from starting incorrectly.
    raise e

# This is a placeholder decorator from your original file.
# It's kept here to ensure the code structure remains the same.
def register_tool(*args, **kwargs):
    """Placeholder decorator for proper module imports"""
    def decorator(func):
        return func
    return decorator

# ==============================================================================
# The rest of your file is well-structured and remains unchanged.
# All the functions below will now work because the imports above are fixed.
# ==============================================================================

# Task-related tools
@register_tool(
    name="query_tasks",
    category="database",
    description="Query tasks from the database"
)
def query_tasks(supabase, user_id, **query_params):
    """Query tasks from the database with optional filters."""
    return database_personal.query_tasks(supabase, user_id, **query_params)

@register_tool(
    name="get_task_by_id",
    category="database",
    description="Get a task by ID"
)
def get_task_by_id(supabase, user_id, task_id):
    """Get a task by its ID."""
    tasks = database_personal.query_tasks(supabase, user_id, id=task_id)
    return tasks[0] if tasks else None

@register_tool(
    name="find_task_by_title",
    category="database",
    description="Find a task by title (partial match)"
)
def find_task_by_title(supabase, user_id, title):
    """Find a task by its title (partial match)."""
    tasks = database_personal.query_tasks(supabase, user_id, title_like=title)
    return tasks[0] if tasks else None

# Task operations
@register_tool(
    name="add_task",
    category="database",
    description="Add a new task"
)
def add_task(supabase, user_id, **kwargs):
    """Add a new task to the database."""
    return database_personal.add_task_entry(supabase, user_id, **kwargs)

@register_tool(
    name="update_task",
    category="database",
    description="Update an existing task"
)
def update_task(supabase, user_id, task_id, patch):
    """Update an existing task."""
    return database_personal.update_task_entry(supabase, user_id, task_id, patch)

@register_tool(
    name="delete_task",
    category="database",
    description="Delete a task"
)
def delete_task(supabase, user_id, task_id):
    """Delete a task."""
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
    """Get the user's silent mode status."""
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
    """Activate silent mode for the user."""
    return database_silent.create_silent_session(supabase, user_id, duration_minutes, trigger_type)

@register_tool(
    name="deactivate_silent_mode",
    category="database",
    description="Deactivate silent mode for the user"
)
def deactivate_silent_mode(supabase, user_id):
    """Deactivate silent mode for the user."""
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
    """Get all active AI actions for the user."""
    return database_personal.get_all_active_ai_actions(supabase, user_id)

# Reminder tools
@register_tool(
    name="get_all_reminders",
    category="database",
    description="Get all reminders for the user"
)
def get_all_reminders(supabase, user_id):
    """Get all reminders for the user."""
    return database_personal.get_all_reminders(supabase, user_id)

# Context functions
@register_tool(
    name="get_task_context_for_ai",
    category="database",
    description="Get task context for AI"
)
def get_task_context_for_ai(supabase, user_id):
    """Get task context for AI."""
    return database_personal.get_task_context_for_ai(supabase, user_id)

@register_tool(
    name="get_memory_context_for_ai",
    category="database",
    description="Get memory context for AI"
)
def get_memory_context_for_ai(supabase, user_id):
    """Get memory context for AI."""
    return database_personal.get_memory_context_for_ai(supabase, user_id)

@register_tool(
    name="get_user_context_for_ai",
    category="database",
    description="Get user context for AI"
)
def get_user_context_for_ai(supabase, user_id):
    """Get user context for AI."""
    return database_personal.get_user_context_for_ai(supabase, user_id)

# Conversation history tools
@register_tool(
    name="store_conversation_history",
    category="database",
    description="Store conversation history"
)
def store_conversation_history(supabase, user_id, history):
    """Store conversation history."""
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
    """Get conversation history."""
    return database_personal.get_conversation_history(supabase, user_id)