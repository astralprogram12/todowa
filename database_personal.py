# database.py (Consolidated Version)
# This is now the single source of truth for all database operations.

from supabase import Client
from datetime import date, datetime, timezone, timedelta
import uuid
import json
from config import UNVERIFIED_LIMIT, VERIFIED_LIMIT
import re
from src.ai_text_processors.typo_correction_agent import apply_ai_typo_correction

# --- Typo Correction and Validation Functions ---

def apply_typo_correction(text: str) -> str:
    """
    Apply AI-powered typo correction to user input.
    
    This function now uses an AI agent for intelligent, context-aware
    typo correction that works with multiple languages.
    """
    return apply_ai_typo_correction(text)

def validate_priority(priority: str) -> str:
    """Validate and normalize priority value"""
    if not priority:
        return 'medium'  # default
    
    priority_lower = priority.lower().strip()
    valid_priorities = ['low', 'medium', 'high']
    
    if priority_lower in valid_priorities:
        return priority_lower
    
    # Handle common variations
    priority_mapping = {
        'urgent': 'high',
        'important': 'high',
        'critical': 'high',
        'normal': 'medium',
        'regular': 'medium',
        'standard': 'medium',
        'minor': 'low',
        'optional': 'low',
        'later': 'low'
    }
    
    return priority_mapping.get(priority_lower, 'medium')

def validate_difficulty(difficulty: str) -> str:
    """Validate and normalize difficulty value"""
    if not difficulty:
        return 'medium'  # default
    
    difficulty_lower = difficulty.lower().strip()
    valid_difficulties = ['easy', 'medium', 'hard']
    
    if difficulty_lower in valid_difficulties:
        return difficulty_lower
    
    # Handle common variations
    difficulty_mapping = {
        'simple': 'easy',
        'basic': 'easy',
        'quick': 'easy',
        'normal': 'medium',
        'regular': 'medium',
        'standard': 'medium',
        'difficult': 'hard',
        'complex': 'hard',
        'challenging': 'hard',
        'tough': 'hard'
    }
    
    return difficulty_mapping.get(difficulty_lower, 'medium')

def validate_status(status: str) -> str:
    """Validate and normalize status value"""
    if not status:
        return 'todo'  # default
    
    status_lower = status.lower().strip()
    valid_statuses = ['todo', 'doing', 'done']
    
    if status_lower in valid_statuses:
        return status_lower
    
    # Handle common variations
    status_mapping = {
        'pending': 'todo',
        'new': 'todo',
        'open': 'todo',
        'active': 'doing',
        'in-progress': 'doing',
        'in_progress': 'doing',
        'working': 'doing',
        'current': 'doing',
        'completed': 'done',
        'finished': 'done',
        'complete': 'done',
        'closed': 'done'
    }
    
    return status_mapping.get(status_lower, 'todo')

# --- User & Usage ---

def get_user_id_by_phone(supabase: Client, phone: str) -> str | None:
    """Gets a user's UUID from their phone number."""
    try:
        res = supabase.table('user_whatsapp').select('user_id').eq('phone', phone).eq('status', 'connected').is_('wa_connected', True).execute()
        return res.data[0].get('user_id') if res.data else None
    except Exception as e:
        print(f"!!! DATABASE ERROR in get_user_id_by_phone: {e}")
        return None

def get_user_phone_by_id(supabase: Client, user_id: str) -> str | None:
    """Helper to get a user's phone number from their ID (for scheduler)."""
    try:
        res = supabase.table('user_whatsapp').select('phone').eq('user_id', user_id).limit(1).execute()
        return res.data[0].get('phone') if res.data else None
    except Exception as e:
        print(f"!!! DATABASE ERROR in get_user_phone_by_id: {e}")
        return None

def check_and_update_usage(supabase: Client, sender_phone: str, user_id: str | None) -> tuple[bool, str]:
    """Checks and updates the daily message count for a user."""
    today = date.today().isoformat()
    limit = VERIFIED_LIMIT if user_id else UNVERIFIED_LIMIT
    try:
        if user_id:
            res = supabase.table('user_whatsapp').select('daily_message_count, last_message_date').eq('user_id', user_id).execute()
            data = res.data[0] if res.data else {}
            count = data.get('daily_message_count', 0)
            last_date = data.get('last_message_date')
            if last_date != today:
                supabase.table('user_whatsapp').update({'daily_message_count': 1, 'last_message_date': today}).eq('user_id', user_id).execute()
                return (True, "")
            if count < limit:
                supabase.table('user_whatsapp').update({'daily_message_count': count + 1}).eq('user_id', user_id).execute()
                return (True, "")
            return (False, f"You have reached your daily limit of {limit} messages.")
        else:
            return (False, "Please register to use the service.")
    except Exception as e:
        print(f"!!! DATABASE ERROR in check_and_update_usage: {e}")
        return (False, "Sorry, I'm having trouble with my database right now.")

# --- AI Context Gathering ---

def get_user_context_for_ai(supabase: Client, user_id: str) -> dict:
    """Fetches all user-specific context for the AI."""
    try:
        res = supabase.table('user_whatsapp').select('timezone, schedule_limit, auto_silent_enabled, auto_silent_start_hour, auto_silent_end_hour').eq('user_id', user_id).execute()
        context = {"timezone": "UTC", "schedule_limit": 5, "auto_silent_enabled": True, "auto_silent_start_hour": 7, "auto_silent_end_hour": 11}
        if res.data:
            context.update(res.data[0])
        return context
    except Exception as e:
        print(f"!!! DATABASE ERROR in get_user_context_for_ai: {e}")
        return {"timezone": "UTC", "schedule_limit": 5}

def get_task_context_for_ai(supabase: Client, user_id: str) -> dict:
    """Fetches recent tasks for a user."""
    try:
        tasks_res = supabase.table('tasks').select('id, title, status, due_date, reminder_at, category').eq('user_id', user_id).order('created_at', desc=True).limit(50).execute()
        return {"tasks": tasks_res.data or []}
    except Exception as e:
        print(f"!!! DATABASE ERROR in get_task_context_for_ai: {e}")
        return {"tasks": []}

def get_memory_context_for_ai(supabase: Client, user_id: str) -> dict:
    """Fetches recent memories for a user."""
    try:
        res = supabase.table('memory_entries').select('title, content, category, created_at').eq('user_id', user_id).neq('category', 'conversation_history').order('created_at', desc=True).limit(25).execute()
        return {"memories": res.data or []}
    except Exception as e:
        print(f"!!! DATABASE ERROR in get_memory_context_for_ai: {e}")
        return {"memories": []}

def get_journal_context_for_ai(supabase: Client, user_id: str) -> dict:
    """Fetches recent journal entries for context."""
    try:
        res = supabase.table('journals').select('title, content, category, created_at').eq('user_id', user_id).order('created_at', desc=True).limit(10).execute()
        return {"journals": res.data or []}
    except Exception as e:
        print(f"!!! DATABASE ERROR in get_journal_context_for_ai: {e}")
        return {"journals": []}

# --- Task Functions ---

def add_task_entry(supabase: Client, user_id: str, **kwargs):
    """Add a task entry with proper constraint validation"""
    kwargs['user_id'] = user_id
    
    # Validate and clean inputs
    if not kwargs.get('title') or len(kwargs['title'].strip()) == 0: 
        raise ValueError("Task title cannot be empty.")
    
    # Apply typo correction to title
    kwargs['title'] = apply_typo_correction(kwargs['title'])
    
    # Validate and normalize constraint fields
    if 'priority' in kwargs and kwargs['priority']:
        kwargs['priority'] = validate_priority(kwargs['priority'])
    
    if 'difficulty' in kwargs and kwargs['difficulty']:
        kwargs['difficulty'] = validate_difficulty(kwargs['difficulty'])
        
    if 'status' in kwargs and kwargs['status']:
        kwargs['status'] = validate_status(kwargs['status'])
    
    try:
        res = supabase.table("tasks").insert(kwargs).execute()
        if getattr(res, "error", None): 
            print(f"Task creation error: {res.error}")
            raise Exception(str(res.error))
        return (res.data or [None])[0]
    except Exception as e:
        print(f"Task creation error: {e}")
        raise e

def update_task_entry(supabase: Client, user_id: str, task_id: str, patch: dict):
    res = supabase.table("tasks").update(patch).eq("id", task_id).eq("user_id", user_id).execute()
    if getattr(res, "error", None): raise Exception(str(res.error))
    return (res.data or [None])[0]

def delete_task_entry(supabase: Client, user_id: str, task_id: str):
    supabase.table('tasks').delete().eq('id', task_id).eq('user_id', user_id).execute()

def query_tasks(supabase: Client, user_id: str, **filters):
    q = supabase.table("tasks").select("*").eq("user_id", user_id)
    if filters.get('title_like'): q = q.ilike('title', f"%{filters['title_like']}%")
    if filters.get('id'): q = q.eq('id', filters['id'])
    res = q.execute()
    if getattr(res, "error", None): raise Exception(str(res.error))
    return res.data or []

# --- Memory & Journal Functions ---

def add_memory_entry(supabase: Client, user_id: str, title: str, content: str | None = None, category: str | None = None):
    if not title or len(title.strip()) == 0: raise ValueError("Title cannot be empty.")
    entry = {"user_id": user_id, "title": title.strip(), "content": content, "category": category}
    res = supabase.table("memory_entries").insert(entry).execute()
    if getattr(res, "error", None): raise Exception(str(res.error))
    return (res.data or [None])[0]

def update_memory_entry(supabase: Client, user_id: str, memory_id: str, patch: dict):
    res = supabase.table("memory_entries").update(patch).eq("id", memory_id).eq("user_id", user_id).execute()
    if getattr(res, "error", None): raise Exception(str(res.error))
    return (res.data or [None])[0]

def delete_memory_entry(supabase: Client, user_id: str, memory_id: str):
    supabase.table("memory_entries").delete().eq("id", memory_id).eq("user_id", user_id).execute()

def search_memory_entries(supabase: Client, user_id: str, query: str, limit: int = 5):
    try:
        sanitized_query = query.replace("'", "''")
        res = supabase.table("memory_entries").select("title, content, created_at").eq("user_id", user_id).or_(f"title.ilike.%{sanitized_query}%,content.ilike.%{sanitized_query}%").order("created_at", desc=True).limit(limit).execute()
        return res.data or []
    except Exception as e:
        print(f"!!! DATABASE ERROR in search_memory_entries: {e}")
        return []

def add_journal_entry(supabase: Client, user_id: str, title: str, content: str | None = None, category: str | None = None):
    # This function is very similar to add_memory_entry
    if not title or len(title.strip()) == 0: raise ValueError("Title cannot be empty.")
    entry = {"user_id": user_id, "title": title.strip(), "content": content, "category": category}
    res = supabase.table("journals").insert(entry).execute()
    if getattr(res, "error", None): raise Exception(str(res.error))
    return (res.data or [None])[0]

# --- AI Action & Reminder Functions ---

def get_all_reminders(supabase: Client, user_id: str) -> list:
    try:
        res = supabase.table("tasks").select("title, reminder_at").eq("user_id", user_id).not_.is_("reminder_at", "null").eq("reminder_sent", False).order("reminder_at", desc=False).execute()
        return res.data or []
    except Exception as e:
        print(f"!!! DATABASE ERROR in get_all_reminders: {e}")
        return []

def get_all_active_ai_actions(supabase: Client, user_id: str) -> list:
    try:
        res = supabase.table("ai_actions").select("*").eq("user_id", user_id).eq("status", "active").execute()
        return res.data or []
    except Exception as e:
        print(f"!!! DATABASE ERROR in get_all_active_ai_actions: {e}")
        return []

# --- Silent Mode Functions ---

def create_silent_session(supabase: Client, user_id: str, duration_minutes: int, trigger_type: str = 'manual'):
    try:
        end_active_silent_sessions(supabase, user_id, 'system')
        data = {'user_id': user_id, 'duration_minutes': duration_minutes, 'trigger_type': trigger_type, 'is_active': True, 'accumulated_actions': [], 'action_count': 0}
        res = supabase.table('silent_sessions').insert(data).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"!!! DATABASE ERROR in create_silent_session: {e}")
        return None

def get_active_silent_session(supabase: Client, user_id: str):
    try:
        res = supabase.table('silent_sessions').select('*').eq('user_id', user_id).eq('is_active', True).order('start_time', desc=True).limit(1).execute()
        if res.data:
            session = res.data[0]
            start_time = datetime.fromisoformat(session['start_time'].replace('Z', '+00:00'))
            end_time = start_time + timedelta(minutes=session['duration_minutes'])
            if datetime.now(timezone.utc) > end_time:
                end_silent_session(supabase, session['id'], 'expired')
                return None
            return session
        return None
    except Exception as e:
        print(f"!!! DATABASE ERROR in get_active_silent_session: {e}")
        return None

def end_silent_session(supabase: Client, session_id: str, exit_reason: str = 'manual_exit'):
    try:
        session_res = supabase.table('silent_sessions').select('*').eq('id', session_id).execute()
        if not session_res.data: return None
        update_data = {'is_active': False, 'end_time': datetime.now(timezone.utc).isoformat(), 'exit_reason': exit_reason}
        supabase.table('silent_sessions').update(update_data).eq('id', session_id).execute()
        return session_res.data[0]
    except Exception as e:
        print(f"!!! DATABASE ERROR in end_silent_session: {e}")
        return None

def end_active_silent_sessions(supabase: Client, user_id: str, exit_reason: str = 'system'):
    try:
        res = supabase.table('silent_sessions').update({'is_active': False, 'end_time': datetime.now(timezone.utc).isoformat(), 'exit_reason': exit_reason}).eq('user_id', user_id).eq('is_active', True).execute()
        return len(res.data)
    except Exception as e:
        print(f"!!! DATABASE ERROR in end_active_silent_sessions: {e}")
        return 0

# --- Project Functions ---

def get_project_context_for_ai(supabase: Client, user_id: str):
    # This is currently a placeholder and needs to be implemented with real queries.
    return {
        "user_context": {"name": "Budi", "username": "Budi#1234"},
        "active_project": {"name": "Website Redesign", "id": "proj-uuid-abcde"},
        "user_role_in_project": {"name": "Admin", "permissions": ["can_add_task", "can_confirm_tasks"]},
        "project_tasks": [{"title": "Draft homepage mockups", "assignees": ["Andi#5567"]}],
    }

# --- Logging Functions ---

def log_action(supabase: Client, user_id: str, action_type: str, entity_type: str = None, 
               entity_id: str = None, action_details: dict = None, user_input: str = None,
               success_status: bool = True, error_details: str = None, execution_time_ms: int = None,
               session_id: str = None):
    try:
        log_entry = {
            "user_id": user_id, "session_id": session_id or str(uuid.uuid4()), "action_type": action_type,
            "entity_type": entity_type, "entity_id": entity_id, "action_details": action_details or {},
            "user_input": user_input, "success_status": success_status, "error_details": error_details,
            "execution_time_ms": execution_time_ms, "created_at": datetime.now().isoformat()
        }
        supabase.table("action_logs").insert(log_entry).execute()
    except Exception as e:
        print(f"!!! DATABASE ERROR in log_action: {e}")