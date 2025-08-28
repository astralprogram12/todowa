import logging
from supabase import Client
from datetime import datetime, timezone, date, timedelta
from typing import Dict, List, Any, Optional
from config import UNVERIFIED_LIMIT, VERIFIED_LIMIT

logger = logging.getLogger(__name__)

# --- Standalone User Functions ---
# These functions are used to identify a user before a manager is created.


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
    
def get_user_id_by_phone(supabase: Client, phone: str) -> Optional[str]:
    """Gets a user's UUID from their phone number."""
    try:
        res = supabase.table('user_whatsapp').select('user_id').eq('phone', phone).limit(1).execute()
        return res.data[0].get('user_id') if res.data else None
    except Exception as e:
        logger.error(f"DB Error in get_user_id_by_phone: {e}")
        return None

def get_user_context(supabase: Client, user_id: str) -> Dict[str, Any]:
    """Fetches user-specific settings like timezone."""
    try:
        res = supabase.table('user_whatsapp').select('timezone').eq('user_id', user_id).limit(1).execute()
        if res.data:
            return res.data[0]
    except Exception as e:
        logger.error(f"DB Error in get_user_context: {e}")
    return {"timezone": "UTC"} # Return a safe default

# --- Main Database Operations Class ---

class DatabaseManager:
    """Manages all database operations for a specific, authenticated user."""
    def __init__(self, supabase_client: Client, user_id: str):
        """
        Initializes the DatabaseManager.

        Args:
            supabase_client: An authenticated Supabase client instance.
            user_id: The UUID of the user for whom to perform operations.
        """
        if not supabase_client or not user_id:
            raise ValueError("Supabase client and user_id are required for DatabaseManager.")
        self.supabase = supabase_client
        self.user_id = user_id

    def _handle_db_response(self, res, error_message: str) -> List[Dict[str, Any]]:
        """A helper to consistently handle Supabase responses."""
        if hasattr(res, 'data') and res.data:
            return res.data
        logger.warning(f"{error_message}: No data returned or an error occurred.")
        return []
        
     # --- Task Table Operations ---

    def create_task(self, title: str, description: Optional[str] = None, notes: Optional[str] = None, priority: str = "medium", due_date: Optional[str] = None, category: str = "general") -> Dict[str, Any]:
        """
        UPDATED: Now includes the 'description' field for a task summary, distinct from 'notes'.
        (Note: Ensure your 'tasks' table in Supabase has a 'description' column).
        """
        if not title:
            raise ValueError("Task title cannot be empty.")
        task_data = {
            "user_id": self.user_id,
            "title": title,
            "description": description,  # <-- NEWLY ADDED
            "notes": notes,
            "priority": priority.lower(),
            "status": "todo",
            "category": category.lower(),
            "due_date": due_date,
        }
        res = self.supabase.table("tasks").insert(task_data).execute()
        data = self._handle_db_response(res, "Failed to insert task")
        if not data:
            raise Exception("Database failed to return created task data.")
        return data[0]

    def get_tasks_by_ids(self, task_ids: List[str], order_by: str = 'created_at', ascending: bool = False):
        """
        Retrieves a specific set of tasks from the database by their IDs.
        """
        try:
            query = self.supabase.table('tasks').select('*')
            
            # Use the .in_() filter to match any ID in the provided list
            query = query.in_('id', task_ids)
            
            # Apply ordering
            query = query.order(order_by, desc=not ascending)
            
            result = query.execute()
            
            if not result.data:
                return {"success": True, "data": []}
            return {"success": True, "data": result.data}

        except Exception as e:
            logger.error(f"Database error fetching tasks by IDs: {e}")
            return {"success": False, "error": str(e)}
        
    def get_tasks(self, status: Optional[str] = None, priority: Optional[str] = None, category: Optional[str] = None, limit: int = 25, order_by: str = 'created_at', ascending: bool = False) -> List[Dict[str, Any]]:
        query = self.supabase.table("tasks").select("*").eq("user_id", self.user_id)
        if status: query = query.eq('status', status)
        if priority: query = query.eq('priority', priority)
        if category: query = query.eq('category', category)
        
        # Corrected line:
        res = query.order(order_by, desc=not ascending).limit(limit).execute()
        
        return self._handle_db_response(res, "Could not retrieve tasks")

    def update_task(self, task_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        patch["updated_at"] = datetime.now(timezone.utc).isoformat()
        res = self.supabase.table("tasks").update(patch).eq("id", task_id).eq("user_id", self.user_id).execute()
        data = self._handle_db_response(res, f"Failed to update task {task_id}")
        return data[0] if data else None

    def delete_task(self, task_id: str) -> bool:
        res = self.supabase.table('tasks').delete().eq('id', task_id).eq('user_id', self.user_id).execute()
        return bool(self._handle_db_response(res, f"Failed to delete task {task_id}"))

    def get_task_stats(self) -> Dict[str, int]:
        completed_res = self.supabase.table("tasks").select("id", count='exact').eq("user_id", self.user_id).eq("status", "done").execute()
        pending_res = self.supabase.table("tasks").select("id", count='exact').eq("user_id", self.user_id).eq("status", "todo").execute()
        return {"completed_count": completed_res.count or 0, "pending_count": pending_res.count or 0}



    ##################schedule agent

    def create_schedule(self, action_type: str, action_payload: Dict, schedule_type: str, schedule_value: str, timezone: str, next_run_at: str) -> Dict[str, Any]:
        """Creates a new entry in the 'scheduled_actions' table."""
        schedule_data = {
            "user_id": self.user_id, "action_type": action_type,
            "action_payload": action_payload, "schedule_type": schedule_type,
            "schedule_value": schedule_value, "timezone": timezone,
            "next_run_at": next_run_at, "status": "active"
        }
        res = self.supabase.table("scheduled_actions").insert(schedule_data).execute()
        data = self._handle_db_response(res, "Failed to insert schedule")
        if not data:
            raise Exception("Database failed to return created schedule data.")
        return data[0]

    def get_schedules(self, status: str = 'active', limit: int = 50) -> List[Dict[str, Any]]:
        """
        NEW: Fetches a list of schedules for the user.
        Defaults to fetching active schedules.
        """
        res = self.supabase.table("scheduled_actions").select("*") \
            .eq("user_id", self.user_id) \
            .eq("status", status) \
            .limit(limit) \
            .execute()
        return self._handle_db_response(res, "Could not retrieve schedules")

    def update_schedule(self, schedule_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        NEW: Updates a specific schedule by its unique ID.
        """
        patch["updated_at"] = datetime.now(timezone.utc).isoformat()
        res = self.supabase.table("scheduled_actions").update(patch) \
            .eq("id", schedule_id) \
            .eq("user_id", self.user_id) \
            .execute()
        data = self._handle_db_response(res, f"Failed to update schedule {schedule_id}")
        return data[0] if data else None

    def delete_schedule(self, schedule_id: str) -> bool:
        """
        NEW: Deletes a specific schedule by its unique ID.
        This is effectively how a user "cancels" a schedule.
        """
        res = self.supabase.table('scheduled_actions').delete() \
            .eq('id', schedule_id) \
            .eq('user_id', self.user_id) \
            .execute()
        # Check if any rows were affected
        return bool(self._handle_db_response(res, f"Failed to delete schedule {schedule_id}"))
    
    # --- Journal Table Operations ---
    def create_journal_entry_in_db(self, title: str, content: str, category: str, entry_type: str) -> Dict[str, Any]:
        if not title or not content:
            raise ValueError("Journal title and content cannot be empty.")
        entry_data = {
            "user_id": self.user_id,
            "title": title, 
            "content": content,
            "category": category.lower(), 
            "entry_type": entry_type,
        }
        res = self.supabase.table("journals").insert(entry_data).execute()
        data = self._handle_db_response(res, "Failed to insert journal entry")
        if not data:
            raise Exception("Database failed to return created journal entry data.")
        return data[0]

    def search_journal_entries_by_titles(self, titles: List[str], limit: int = 10) -> List[Dict]:
        res = self.supabase.table('journals').select('*') \
            .eq('user_id', self.user_id) \
            .in_('title', titles) \
            .limit(limit) \
            .execute()
        return self._handle_db_response(res, f"No journal entries found for titles: {titles}")

    def update_journal_entry_in_db(self, patch: Dict[str, Any], id: Optional[int] = None, title_match: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Updates journal entries based on a unique ID or an exact title match.
        The ID is the preferred and safer method.
        """
        patch["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        query = self.supabase.table("journals").update(patch).eq("user_id", self.user_id)
        
        # Build the query based on the provided identifier
        if id is not None:
            query = query.eq("id", id)
            identifier_text = f"ID: {id}"
        elif title_match is not None:
            query = query.eq("title", title_match)
            identifier_text = f"title: {title_match}"
        else:
            # This case is already handled by the tool, but it's good practice
            raise ValueError("No identifier (id or title_match) provided for update.")

        res = query.execute()
        return self._handle_db_response(res, f"Failed to update journal entry with {identifier_text}")

    def delete_journal_entry_in_db(self, id: Optional[int] = None, title_match: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Deletes journal entries based on a unique ID or an exact title match.
        The ID is the preferred and safer method.
        """
        query = self.supabase.table('journals').delete().eq('user_id', self.user_id)

        # Build the query based on the provided identifier
        if id is not None:
            query = query.eq("id", id)
            identifier_text = f"ID: {id}"
        elif title_match is not None:
            query = query.eq("title", title_match)
            identifier_text = f"title: {title_match}"
        else:
            raise ValueError("No identifier (id or title_match) provided for deletion.")
            
        res = query.execute()
        return self._handle_db_response(res, f"Failed to delete journal entry with {identifier_text}")
    
    # --- AI Brain (Memory) Table Operations ---

    def create_or_update_memory(self, memory_type: str, data: Dict, content: str, importance: int = 10) -> Dict[str, Any]:
        if not memory_type:
            raise ValueError("Memory type is required.")
        memory_data = {
            "user_id": self.user_id, 
            "brain_data_type": memory_type,
            "content_json": data, 
            "content": content, 
            "importance": importance
        }
        res = self.supabase.table("ai_brain_memories").upsert(memory_data, on_conflict="user_id, brain_data_type").execute()
        data = self._handle_db_response(res, f"Failed to upsert memory type {memory_type}")
        if not data:
            raise Exception("Database failed to return created/updated memory data.")
        return data[0]

    def get_memories(self, memory_type: Optional[str] = None, limit: int = 25) -> List[Dict[str, Any]]:
        query = self.supabase.table("ai_brain_memories").select("*").eq("user_id", self.user_id)
        if memory_type:
            query = query.eq('brain_data_type', memory_type)
        res = query.limit(limit).execute()
        return self._handle_db_response(res, f"No memories found for type: {memory_type}")

    def delete_memory(self, memory_id: str) -> bool:
        res = self.supabase.table('ai_brain_memories').delete().eq('id', memory_id).eq('user_id', self.user_id).execute()
        return bool(self._handle_db_response(res, f"Failed to delete memory {memory_id}"))
    
    ##################33

    def get_recent_tasks_and_journals(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetches tasks and journal entries created in the last 3 days for the user.
        This provides a lean, relevant context for synthesis agents.
        """
        results = {
            "tasks": [],
            "journal_entries": []
        }
        try:
            three_days_ago = datetime.now(timezone.utc) - timedelta(days=3)
            three_days_ago_iso = three_days_ago.isoformat()

            # Fetch recent tasks
            tasks_res = self.supabase.table('tasks').select('*') \
                .eq('user_id', self.user_id) \
                .gte('created_at', three_days_ago_iso) \
                .order('created_at', desc=True).limit(25).execute()
            results["tasks"] = self._handle_db_response(tasks_res, "No recent tasks found.")

            # Fetch recent journal entries (assuming table name is 'journals')
            journal_res = self.supabase.table('journals').select('*') \
                .eq('user_id', self.user_id) \
                .gte('created_at', three_days_ago_iso) \
                .order('created_at', desc=True).limit(25).execute()
            results["journal_entries"] = self._handle_db_response(journal_res, "No recent journal entries found.")

        except Exception as e:
            logger.error(f"DB Error fetching recent context: {e}")
            # Return empty lists on error to prevent crashes

        return results    