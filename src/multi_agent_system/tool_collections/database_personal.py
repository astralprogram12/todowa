# database_personal.py (Correct, Final, and Verified Version)
from supabase import Client
from datetime import date, datetime
import uuid
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
    """Fetches recent memories for a user, excluding conversation history."""
    try:
        res = supabase.table('memory_entries').select('title, content, category, created_at').eq('user_id', user_id).neq('category', 'conversation_history').order('created_at', desc=True).limit(25).execute()
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
    
    
def add_memory_entry(supabase: Client, user_id: str, title: str, content: str | None = None, category: str | None = None):
    entry = {"user_id": user_id, "title": title, "content": content, "category": category}
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

# --- Journal Functions ---

def find_journal_by_title(supabase: Client, user_id: str, title_query: str):
    """Finds a single journal entry using a title search."""
    try:
        res = supabase.table("journals").select("*").eq("user_id", user_id).ilike("title", f"%{title_query}%").limit(1).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"!!! DATABASE ERROR in find_journal_by_title: {e}")
        return None

def add_journal_entry(supabase: Client, user_id: str, title: str, content: str | None = None, category: str | None = None):
    """Adds a new journal entry to the database."""
    entry = {"user_id": user_id, "title": title, "content": content, "category": category}
    res = supabase.table("journals").insert(entry).execute()
    if getattr(res, "error", None): raise Exception(str(res.error))
    return (res.data or [None])[0]

def update_journal_entry(supabase: Client, user_id: str, journal_id: str, patch: dict):
    """Updates an existing journal entry."""
    res = supabase.table("journals").update(patch).eq("id", journal_id).eq("user_id", user_id).execute()
    if getattr(res, "error", None): raise Exception(str(res.error))
    return (res.data or [None])[0]

def delete_journal_entry(supabase: Client, user_id: str, journal_id: str):
    """Deletes a journal entry from the database."""
    supabase.table("journals").delete().eq("id", journal_id).eq("user_id", user_id).execute()

def search_journal_entries(supabase: Client, user_id: str, query: str, limit: int = 5):
    """Searches journal entries by title and content."""
    try:
        res = supabase.table("journals").select("title, content, category, created_at") \
            .eq("user_id", user_id).or_(f"title.ilike.%{query}%,content.ilike.%{query}%") \
            .order("created_at", desc=True).limit(limit).execute()
        return res.data or []
    except Exception as e:
        print(f"!!! DATABASE ERROR in search_journal_entries: {e}")
        return []

def get_journal_context_for_ai(supabase: Client, user_id: str) -> dict:
    """Fetches recent journal entries for context."""
    try:
        res = supabase.table('journals').select('title, content, category, created_at').eq('user_id', user_id).order('created_at', desc=True).limit(10).execute()
        return {"journals": res.data or []}
    except Exception as e:
        print(f"!!! DATABASE ERROR in get_journal_context_for_ai: {e}")
        return {"journals": []}

# --- Conversation History Functions ---

def store_conversation_history(supabase: Client, user_id: str, history: list):
    """Stores conversation history in memory_entries with special category."""
    import json
    try:
        # Delete existing conversation history
        supabase.table('memory_entries').delete().eq('user_id', user_id).eq('category', 'conversation_history').execute()
        
        # Limit to last 10 messages or 5 complete conversations
        limited_history = _limit_conversation_history(history)
        
        # Store new conversation history
        if limited_history:
            conversation_content = json.dumps(limited_history)
            add_memory_entry(supabase, user_id, 
                           title="Recent Conversation History", 
                           content=conversation_content, 
                           category="conversation_history")
    except Exception as e:
        print(f"!!! DATABASE ERROR in store_conversation_history: {e}")

def get_conversation_history(supabase: Client, user_id: str) -> list:
    """Retrieves conversation history from memory_entries."""
    import json
    try:
        res = supabase.table('memory_entries').select('content').eq('user_id', user_id).eq('category', 'conversation_history').limit(1).execute()
        if res.data and res.data[0].get('content'):
            return json.loads(res.data[0]['content'])
        return []
    except Exception as e:
        print(f"!!! DATABASE ERROR in get_conversation_history: {e}")
        return []

def _limit_conversation_history(history: list, max_messages: int = 10, max_conversations: int = 5) -> list:
    """Limits conversation history to max_messages or max_conversations."""
    if not history:
        return []
    
    # First limit by number of messages
    limited_by_messages = history[-max_messages:] if len(history) > max_messages else history
    
    # Then limit by number of complete conversations (user-assistant pairs)
    conversation_count = 0
    result = []
    
    # Count backwards to keep most recent conversations
    for i in range(len(limited_by_messages) - 1, -1, -1):
        msg = limited_by_messages[i]
        result.insert(0, msg)
        
        # Count user messages as conversation starts
        if msg.get('role') == 'user':
            conversation_count += 1
            if conversation_count >= max_conversations:
                break
    
    return result

def log_action(supabase: Client, user_id: str, action_type: str, entity_type: str = None, 
               entity_id: str = None, action_details: dict = None, user_input: str = None,
               success_status: bool = True, error_details: str = None, execution_time_ms: int = None,
               session_id: str = None) -> dict:
    """Logs every action for analytics and insights."""
    try:
        log_entry = {
            "user_id": user_id,
            "session_id": session_id or str(uuid.uuid4()),
            "action_type": action_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action_details": action_details or {},
            "user_input": user_input,
            "success_status": success_status,
            "error_details": error_details,
            "execution_time_ms": execution_time_ms,
            "created_at": datetime.now().isoformat()
        }
        
        res = supabase.table("action_logs").insert(log_entry).execute()
        if getattr(res, "error", None):
            print(f"!!! DATABASE ERROR in log_action: {res.error}")
            return None
        return (res.data or [None])[0]
    except Exception as e:
        print(f"!!! DATABASE ERROR in log_action: {e}")
        return None