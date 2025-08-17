# database_personal.py (Correct, Final, and Verified Version)
from supabase import Client
from datetime import date
from config import UNVERIFIED_LIMIT, VERIFIED_LIMIT

# --- User and Usage Functions ---

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

# --- AI Context Functions ---

def get_user_context_for_ai(supabase: Client, user_id: str) -> dict:
    """Fetches user-specific context: timezone and schedule limit."""
    try:
        res = supabase.table('user_whatsapp').select('timezone, schedule_limit').eq('user_id', user_id).execute()
        if res.data:
            return res.data[0]
        return {"timezone": "UTC", "schedule_limit": 5} # Safe defaults
    except Exception as e:
        print(f"!!! DATABASE ERROR in get_user_context_for_ai: {e}")
        return {"timezone": "UTC", "schedule_limit": 5}



def get_task_context_for_ai(supabase: Client, user_id: str) -> dict:
    """Fetches recent tasks for a user, including reminder info."""
    try:
        tasks_res = supabase.table('tasks').select(
            'id, title, status, due_date, reminder_at, category'
        ).eq('user_id', user_id).order('created_at', desc=True).limit(50).execute()
        return {"memories": tasks_res.data or []}        

    except Exception as e:
        print(f"!!! DATABASE ERROR in get_task_context_for_ai: {e}")
        return {"tasks": []}

def get_memory_context_for_ai(supabase: Client, user_id: str) -> dict:
    """Fetches recent memories for a user."""
    try:
        res = supabase.table('memory_entries').select('title, content, created_at').eq('user_id', user_id).order('created_at', desc=True).limit(25).execute()
        return {"memories": res.data or []}
    except Exception as e:
        print(f"!!! DATABASE ERROR in get_memory_context_for_ai: {e}")
        return {"memories": []}

# --- Task Functions ---

def add_task_entry(supabase: Client, user_id: str, **kwargs):
    kwargs['user_id'] = user_id
    res = supabase.table("tasks").insert(kwargs).execute()
    if getattr(res, "error", None): raise Exception(str(res.error))
    return (res.data or [None])[0]

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

# --- Memory Functions ---

def find_memory_by_title(supabase: Client, user_id: str, title_query: str):
    """
    Finds a single memory entry using a simple, direct ilike search on the whole phrase.
    This is more robust against complex RLS policies.
    """
    try:
        # Simple, direct search - just like the task search
        res = supabase.table("memory_entries").select("*").eq("user_id", user_id).ilike("title", f"%{title_query}%").limit(1).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"!!! DATABASE ERROR in find_memory_by_title: {e}")
        return None
    
    
def add_memory_entry(supabase: Client, user_id: str, title: str, content: str | None = None):
    entry = {"user_id": user_id, "title": title, "content": content}
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
        res = supabase.table("memory_entries").select("title, content, created_at") \
            .eq("user_id", user_id).or_(f"title.ilike.%{query}%,content.ilike.%{query}%") \
            .order("created_at", desc=True).limit(limit).execute()
        return res.data or []
    except Exception as e:
        print(f"!!! DATABASE ERROR in search_memory_entries: {e}")
        return []

# --- Scheduled Action Functions ---
def get_all_reminders(supabase: Client, user_id: str) -> list:
    """Fetches all tasks that have an active, non-sent reminder."""
    try:
        res = supabase.table("tasks") \
            .select("title, reminder_at") \
            .eq("user_id", user_id) \
            .not_.is_("reminder_at", "null") \
            .eq("reminder_sent", False) \
            .order("reminder_at", desc=False) \
            .execute()
        return res.data or []
    except Exception as e:
        print(f"!!! DATABASE ERROR in get_all_reminders: {e}")
        return []

# --- RENAMED AI Action Functions ---

def add_ai_action(supabase: Client, user_id: str, action_type: str, schedule_spec: str, next_run_at: str, timezone: str, description: str, payload: dict = None):
    entry = {"user_id": user_id, "action_type": action_type, "schedule_spec": schedule_spec,
             "next_run_at": next_run_at, "timezone": timezone, "description": description,
             "action_payload": payload, "status": "active"}
    res = supabase.table("ai_actions").insert(entry).execute() # Table name is now ai_actions
    if getattr(res, "error", None): raise Exception(str(res.error))
    return (res.data or [None])[0]

def get_all_active_ai_actions(supabase: Client, user_id: str) -> list:
    """Fetches all active AI Actions for a user."""
    try:
        # This is the query we are testing.
        res = supabase.table("ai_actions").select("*").eq("user_id", user_id).eq("status", "active").execute()
        return res.data or []
    except Exception as e:
        print(f"!!! DATABASE ERROR in get_all_active_ai_actions: {e}")
        return []
    

def update_ai_action_entry(supabase: Client, user_id: str, action_id: str, patch: dict):
    res = supabase.table("ai_actions").update(patch).eq("id", action_id).eq("user_id", user_id).execute()
    if getattr(res, "error", None): raise Exception(str(res.error))
    return (res.data or [None])[0]

def delete_ai_action_entry(supabase: Client, user_id: str, action_id: str):
    supabase.table("ai_actions").delete().eq("id", action_id).eq("user_id", user_id).execute()

def count_active_ai_actions(supabase: Client, user_id: str) -> int:
    try:
        res = supabase.table("ai_actions").select("id", count="exact").eq("user_id", user_id).eq("status", "active").execute()
        return res.count
    except Exception as e:
        print(f"!!! DATABASE ERROR in count_active_ai_actions: {e}")
        return 0
    

def find_ai_action_by_description(supabase: Client, user_id: str, description_query: str):
    """
    Finds a single scheduled action using a more flexible keyword search.
    It will match if the description contains ALL keywords from the query.
    """
    try:
        # Split the AI's query into individual keywords
        keywords = description_query.split()
        
        # Start the query
        q = supabase.table("ai_actions").select("*").eq("user_id", user_id)
        
        # Add an 'ilike' filter for EACH keyword
        for keyword in keywords:
            q = q.ilike("description", f"%{keyword}%")
            
        # Limit to the first result that matches all keywords
        res = q.limit(1).execute()
        
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"!!! DATABASE ERROR in find_ai_action_by_description: {e}")
        return None

