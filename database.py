# database.py

from supabase import Client
from datetime import date, datetime
from config import UNVERIFIED_LIMIT, VERIFIED_LIMIT

# --- User and Usage Functions ---
def get_user_id_by_phone(supabase: Client, phone: str) -> str | None:
    try:
        res = supabase.table('user_whatsapp').select('user_id').eq('phone', phone).eq('status', 'connected').is_('wa_connected', True).execute()
        return res.data[0].get('user_id') if res.data else None
    except Exception as e:
        print(f"!!! DATABASE ERROR in get_user_id_by_phone: {e}")
        return None

def check_and_update_usage(supabase: Client, sender_phone: str, user_id: str | None) -> tuple[bool, str]:
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

# --- Context and Query Functions ---

def get_user_context_for_ai(supabase: Client, user_id: str) -> dict: # <-- NEW
    """Fetches user-specific context, like their timezone."""
    try:
        res = supabase.table('user_whatsapp').select('timezone').eq('user_id', user_id).execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        print(f"!!! DATABASE ERROR in get_user_context_for_ai: {e}")
        return {}

def get_list_context_for_ai(supabase: Client, user_id: str) -> dict:
    try:
        lists_res = supabase.table('lists').select('id, name, color').eq('user_id', user_id).execute()
        return {"lists": lists_res.data if lists_res.data else []}
    except Exception as e:
        print(f"!!! DATABASE ERROR in get_list_context_for_ai: {e}")
        return {"lists": []}

def get_task_context_for_ai(supabase: Client, user_id: str) -> dict:
    try:
        tasks_res = supabase.table('tasks').select(
            # <-- MODIFIED: Added reminder_at to the context for the AI to see
            'id, title, status, due_date, priority, difficulty, category, tags, reminder_at, list:lists(name)'
        ).eq('user_id', user_id).order('created_at', desc=True).limit(50).execute()
        
        tasks = tasks_res.data or []
        for task in tasks:
            if task.get('list') and isinstance(task.get('list'), dict):
                task['list_name'] = task['list']['name']
                del task['list']

        return {"tasks": tasks}
    except Exception as e:
        print(f"!!! DATABASE ERROR in get_task_context_for_ai: {e}")
        return {"tasks": []}

def query_tasks(supabase: Client, user_id: str, **filters):
    q = supabase.table("tasks").select("*").eq("user_id", user_id)
    if filters.get('title_like'): q = q.ilike('title', f"%{filters['title_like']}%")
    if filters.get('id'): q = q.eq('id', filters['id'])
    res = q.execute()
    if getattr(res, "error", None): raise Exception(str(res.error))
    return res.data or []

def query_lists(supabase: Client, user_id: str, **filters):
    q = supabase.table("lists").select("*").eq("user_id", user_id)
    if filters.get('name'): q = q.ilike('name', filters['name'])
    if filters.get('id'): q = q.eq('id', filters['id'])
    res = q.execute()
    if getattr(res, "error", None): raise Exception(str(res.error))
    return res.data or []

# --- Database Action Functions ---
def add_task_entry(supabase: Client, user_id: str, **kwargs):
    kwargs['user_id'] = user_id
    res = supabase.table("tasks").insert(kwargs).execute()
    if getattr(res, "error", None): raise Exception(str(res.error))
    return (res.data or [None])[0]

def update_task_entry(supabase: Client, user_id: str, task_id: str, patch: dict):
    update_res = supabase.table("tasks").update(patch).eq("id", task_id).eq("user_id", user_id).execute()
    if getattr(update_res, "error", None):
        raise Exception(str(update_res.error))
    
    fetch_res = supabase.table("tasks").select("*").eq("id", task_id).eq("user_id", user_id).execute()
    if getattr(fetch_res, "error", None):
        raise Exception(str(fetch_res.error))

    return (fetch_res.data or [None])[0]

def delete_task_entry(supabase: Client, user_id: str, task_id: str):
    supabase.table('tasks').delete().eq('id', task_id).eq('user_id', user_id).execute()
