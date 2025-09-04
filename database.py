"""
Handles all database interactions for the multi-agent AI assistant.

This module provides a comprehensive set of functions and a dedicated class
for managing data in the Supabase database. It includes standalone functions
for initial user verification and a `DatabaseManager` class that encapsulates
all data operations for an authenticated user, such as managing tasks,
journal entries, schedules, and more.

Key Features:
- User identification and usage tracking.
- A `DatabaseManager` class for authenticated, user-specific operations.
- CRUD (Create, Read, Update, Delete) operations for various data models.
- Specialized queries for fetching recent context and statistics.
"""

import logging
from supabase import Client
from datetime import datetime, timezone, date, timedelta
from typing import Dict, List, Any, Optional
from config import UNVERIFIED_LIMIT, VERIFIED_LIMIT

logger = logging.getLogger(__name__)

# --- Standalone User Functions ---
# These functions are used to identify a user before a manager is created.


def check_and_update_usage(supabase: Client, sender_phone: str, user_id: str | None) -> tuple[bool, str]:
    """
    Checks if a user is within their usage limits and updates their message count.

    This function enforces the application's usage policy. For registered users,
    it tracks daily message counts, resetting them when a new day begins. For
    unregistered users, it provides a standard message.

    Args:
        supabase: An active Supabase client instance.
        sender_phone: The phone number of the user sending the message.
        user_id: The UUID of the user, if they are registered. None otherwise.

    Returns:
        A tuple containing a boolean indicating if the user is allowed to proceed,
        and a string with an error message if they are not.
    """
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
    """
    Retrieves a user's unique identifier (UUID) using their phone number.

    Args:
        supabase: An active Supabase client instance.
        phone: The phone number to look up.

    Returns:
        The user's UUID as a string if found, otherwise None.
    """
    try:
        res = supabase.table('user_whatsapp').select('user_id').eq('phone', phone).limit(1).execute()
        return res.data[0].get('user_id') if res.data else None
    except Exception as e:
        logger.error(f"DB Error in get_user_id_by_phone: {e}")
        return None

def get_user_context(supabase: Client, user_id: str) -> Dict[str, Any]:
    """
    Fetches user-specific settings, such as their timezone.

    Args:
        supabase: An active Supabase client instance.
        user_id: The UUID of the user.

    Returns:
        A dictionary containing the user's settings. Returns a default
        timezone of 'UTC' if no settings are found.
    """
    try:
        res = supabase.table('user_whatsapp').select('timezone').eq('user_id', user_id).limit(1).execute()
        if res.data:
            return res.data[0]
    except Exception as e:
        logger.error(f"DB Error in get_user_context: {e}")
    return {"timezone": "UTC"} # Return a safe default

# --- Main Database Operations Class ---

class DatabaseManager:
    """
    Manages all database operations for a specific, authenticated user.

    This class provides a structured and secure way to interact with the database.
    An instance of this class is tied to a specific user, ensuring that all
    operations are performed within the context of that user's data permissions.

    Attributes:
        supabase (Client): The authenticated Supabase client instance.
        user_id (str): The UUID of the user associated with this manager.
    """
    def __init__(self, supabase_client: Client, user_id: str):
        """
        Initializes the DatabaseManager for a specific user.

        Args:
            supabase_client: An authenticated Supabase client instance.
            user_id: The UUID of the user for whom to perform operations.

        Raises:
            ValueError: If the Supabase client or user_id is not provided.
        """
        if not supabase_client or not user_id:
            raise ValueError("Supabase client and user_id are required for DatabaseManager.")
        self.supabase = supabase_client
        self.user_id = user_id

    def _handle_db_response(self, res, error_message: str) -> List[Dict[str, Any]]:
        """
        A private helper to consistently handle Supabase API responses.

        This method checks if a response from a database operation was successful
        and contained data. It logs a warning if no data is returned.

        Args:
            res: The response object from a Supabase query.
            error_message: The error message to log if the response is empty.

        Returns:
            A list of dictionaries representing the data from the response,
            or an empty list if the operation failed or returned no data.
        """
        if hasattr(res, 'data') and res.data:
            return res.data
        logger.warning(f"{error_message}: No data returned or an error occurred.")
        return []
        
     # --- Task Table Operations ---

    def create_task(self, title: str, description: Optional[str] = None, notes: Optional[str] = None, priority: str = "medium", due_date: Optional[str] = None, category: str = "general") -> Dict[str, Any]:
        """
        Creates a new task in the database for the user.

        Args:
            title: The title of the task.
            description: A brief summary or description of the task.
            notes: Additional details or notes for the task.
            priority: The priority level (e.g., 'low', 'medium', 'high').
            due_date: The date the task is due, in ISO format.
            category: The category to assign to the task.

        Returns:
            A dictionary representing the newly created task.

        Raises:
            ValueError: If the task title is empty.
            Exception: If the database fails to return the created task data.
        """
        if not title:
            raise ValueError("Task title cannot be empty.")
            
        task_data = {
            "user_id": self.user_id,
            "title": title,
            "description": description,
            "notes": notes,
            "priority": (priority or "medium").lower(),
            "status": "todo",
            "category": (category or "general").lower(),
            "due_date": due_date,
        }
        res = self.supabase.table("tasks").insert(task_data).execute()
        data = self._handle_db_response(res, "Failed to insert task")
        if not data:
            raise Exception("Database failed to return created task data.")
        return data[0]

    def get_tasks_by_ids(self, task_ids: List[str], order_by: str = 'created_at', ascending: bool = False):
        """
        Retrieves a specific set of tasks from the database by their unique IDs.

        Args:
            task_ids: A list of task IDs to retrieve.
            order_by: The field to sort the results by.
            ascending: A boolean indicating whether to sort in ascending order.

        Returns:
            A dictionary containing the success status and the list of tasks.
        """
        try:
            query = self.supabase.table('tasks').select('*')
            query = query.in_('id', task_ids)
            query = query.order(order_by, desc=not ascending)
            result = query.execute()
            
            if not result.data:
                return {"success": True, "data": []}
            return {"success": True, "data": result.data}

        except Exception as e:
            logger.error(f"Database error fetching tasks by IDs: {e}")
            return {"success": False, "error": str(e)}
        
    def get_tasks(self, status: Optional[str] = None, priority: Optional[str] = None, category: Optional[str] = None, limit: int = 25, order_by: str = 'created_at', ascending: bool = False) -> List[Dict[str, Any]]:
        """
        Retrieves a list of tasks for the user, with optional filters.

        Args:
            status: Filter tasks by their status (e.g., 'todo', 'done').
            priority: Filter tasks by their priority.
            category: Filter tasks by their category.
            limit: The maximum number of tasks to return.
            order_by: The field to sort the results by.
            ascending: Whether to sort in ascending order.

        Returns:
            A list of dictionaries, where each dictionary is a task.
        """
        query = self.supabase.table("tasks").select("*").eq("user_id", self.user_id)
        if status: query = query.eq('status', status)
        if priority: query = query.eq('priority', priority)
        if category: query = query.eq('category', category)
        
        res = query.order(order_by, desc=not ascending).limit(limit).execute()
        
        return self._handle_db_response(res, "Could not retrieve tasks")

    def update_task(self, task_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Updates a specific task with new data.

        Args:
            task_id: The unique ID of the task to update.
            patch: A dictionary containing the fields to update.

        Returns:
            A dictionary representing the updated task, or None if not found.
        """
        patch["updated_at"] = datetime.now(timezone.utc).isoformat()
        res = self.supabase.table("tasks").update(patch).eq("id", task_id).eq("user_id", self.user_id).execute()
        data = self._handle_db_response(res, f"Failed to update task {task_id}")
        return data[0] if data else None

    def delete_task(self, task_id: str) -> bool:
        """
        Deletes a specific task from the database.

        Args:
            task_id: The unique ID of the task to delete.

        Returns:
            True if the deletion was successful, False otherwise.
        """
        res = self.supabase.table('tasks').delete().eq('id', task_id).eq('user_id', self.user_id).execute()
        return bool(self._handle_db_response(res, f"Failed to delete task {task_id}"))

    def get_task_stats(self) -> Dict[str, int]:
        """
        Retrieves statistics about the user's tasks.

        Returns:
            A dictionary with the counts of completed and pending tasks.
        """
        completed_res = self.supabase.table("tasks").select("id", count='exact').eq("user_id", self.user_id).eq("status", "done").execute()
        pending_res = self.supabase.table("tasks").select("id", count='exact').eq("user_id", self.user_id).eq("status", "todo").execute()
        return {"completed_count": completed_res.count or 0, "pending_count": pending_res.count or 0}

    # --- Schedule Table Operations ---

    def create_schedule(self, action_type: str, action_payload: Dict, schedule_type: str, schedule_value: str, timezone: str, next_run_at: str) -> Dict[str, Any]:
        """
        Creates a new entry in the 'scheduled_actions' table.

        Args:
            action_type: The type of action to be scheduled.
            action_payload: The data required to execute the action.
            schedule_type: The type of schedule (e.g., 'recurring', 'one-time').
            schedule_value: The value for the schedule (e.g., a cron string).
            timezone: The timezone for the schedule.
            next_run_at: The ISO timestamp for the next scheduled run.

        Returns:
            A dictionary representing the newly created schedule.

        Raises:
            Exception: If the database fails to return the created schedule data.
        """
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
        Fetches a list of schedules for the user.

        Args:
            status: The status of the schedules to retrieve (defaults to 'active').
            limit: The maximum number of schedules to return.

        Returns:
            A list of dictionaries, where each dictionary is a schedule.
        """
        res = self.supabase.table("scheduled_actions").select("*") \
            .eq("user_id", self.user_id) \
            .eq("status", status) \
            .limit(limit) \
            .execute()
        return self._handle_db_response(res, "Could not retrieve schedules")

    def update_schedule(self, schedule_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Updates a specific schedule by its unique ID.

        Args:
            schedule_id: The unique ID of the schedule to update.
            patch: A dictionary containing the fields to update.

        Returns:
            A dictionary representing the updated schedule, or None if not found.
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
        Deletes a specific schedule by its unique ID.

        Args:
            schedule_id: The unique ID of the schedule to delete.

        Returns:
            True if the deletion was successful, False otherwise.
        """
        res = self.supabase.table('scheduled_actions').delete() \
            .eq('id', schedule_id) \
            .eq('user_id', self.user_id) \
            .execute()
        return bool(self._handle_db_response(res, f"Failed to delete schedule {schedule_id}"))
    
    # --- Journal Table Operations ---
    def create_journal_entry_in_db(self, title: str, content: str, category: str, entry_type: str) -> Dict[str, Any]:
        """
        Creates a new journal entry in the database.

        Args:
            title: The title of the journal entry.
            content: The main content of the journal entry.
            category: The category for the journal entry.
            entry_type: The type of entry (e.g., 'note', 'memory').

        Returns:
            A dictionary representing the newly created journal entry.

        Raises:
            ValueError: If the title or content is empty.
            Exception: If the database fails to return the created entry data.
        """
        if not title or not content:
            raise ValueError("Journal title and content cannot be empty.")
            
        entry_data = {
            "user_id": self.user_id,
            "title": title, 
            "content": content,
            "category": (category or "general").lower(), 
            "entry_type": entry_type,
        }
        res = self.supabase.table("journals").insert(entry_data).execute()
        data = self._handle_db_response(res, "Failed to insert journal entry")
        if not data:
            raise Exception("Database failed to return created journal entry data.")
        return data[0]

    def search_journal_entries_by_titles(self, titles: List[str], limit: int = 10) -> List[Dict]:
        """
        Searches for journal entries that match a list of titles.

        Args:
            titles: A list of titles to search for.
            limit: The maximum number of entries to return.

        Returns:
            A list of dictionaries, where each dictionary is a journal entry.
        """
        res = self.supabase.table('journals').select('*') \
            .eq('user_id', self.user_id) \
            .in_('title', titles) \
            .limit(limit) \
            .execute()
        return self._handle_db_response(res, f"No journal entries found for titles: {titles}")

    def update_journal_entry_in_db(self, patch: Dict[str, Any], id: Optional[int] = None, title_match: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Updates journal entries based on a unique ID or an exact title match.

        Args:
            patch: A dictionary containing the fields to update.
            id: The unique ID of the journal entry to update.
            title_match: The exact title of the journal entry to update.

        Returns:
            A list of dictionaries representing the updated journal entries.

        Raises:
            ValueError: If neither an ID nor a title_match is provided.
        """
        patch["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        query = self.supabase.table("journals").update(patch).eq("user_id", self.user_id)
        
        if id is not None:
            query = query.eq("id", id)
            identifier_text = f"ID: {id}"
        elif title_match is not None:
            query = query.eq("title", title_match)
            identifier_text = f"title: {title_match}"
        else:
            raise ValueError("No identifier (id or title_match) provided for update.")

        res = query.execute()
        return self._handle_db_response(res, f"Failed to update journal entry with {identifier_text}")

    def delete_journal_entry_in_db(self, id: Optional[int] = None, title_match: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Deletes journal entries based on a unique ID or an exact title match.

        Args:
            id: The unique ID of the journal entry to delete.
            title_match: The exact title of the journal entry to delete.

        Returns:
            A list of dictionaries representing the deleted journal entries.

        Raises:
            ValueError: If neither an ID nor a title_match is provided.
        """
        query = self.supabase.table('journals').delete().eq('user_id', self.user_id)

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
        """
        Creates a new AI memory or updates it if it already exists.

        This 'upsert' operation is based on a combination of the user ID and
        the memory type, ensuring that each memory type is unique per user.

        Args:
            memory_type: The type of memory being stored (e.g., 'user_preferences').
            data: A JSON-serializable dictionary containing the structured memory data.
            content: A text representation of the memory.
            importance: An integer rating of the memory's importance.

        Returns:
            A dictionary representing the created or updated memory.

        Raises:
            ValueError: If the memory type is not provided.
            Exception: If the database fails to return the upserted data.
        """
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
        """
        Retrieves AI memories for the user, with an optional filter by type.

        Args:
            memory_type: The specific type of memories to retrieve. If None,
                         memories of all types are returned.
            limit: The maximum number of memories to return.

        Returns:
            A list of dictionaries, where each dictionary is a memory.
        """
        query = self.supabase.table("ai_brain_memories").select("*").eq("user_id", self.user_id)
        if memory_type:
            query = query.eq('brain_data_type', memory_type)
        res = query.limit(limit).execute()
        return self._handle_db_response(res, f"No memories found for type: {memory_type}")

    def delete_memory(self, memory_id: str) -> bool:
        """
        Deletes a specific AI memory by its unique ID.

        Args:
            memory_id: The unique ID of the memory to delete.

        Returns:
            True if the deletion was successful, False otherwise.
        """
        res = self.supabase.table('ai_brain_memories').delete().eq('id', memory_id).eq('user_id', self.user_id).execute()
        return bool(self._handle_db_response(res, f"Failed to delete memory {memory_id}"))

    # --- Tech Support Table Operations ---
    def create_tech_support_ticket(self, message: str, status: str = "open") -> Dict[str, Any]:
        """
        Creates a new tech support ticket in the database.

        Args:
            message: The user's message describing the issue.
            status: The initial status of the ticket (defaults to 'open').

        Returns:
            A dictionary representing the newly created ticket.

        Raises:
            ValueError: If the message is empty.
            Exception: If the database fails to return the created ticket data.
        """
        if not message:
            raise ValueError("Ticket message cannot be empty.")

        ticket_data = {
            "user_id": self.user_id,
            "message": message,
            "status": status,
        }
        res = self.supabase.table("tech_support_tickets").insert(ticket_data).execute()
        data = self._handle_db_response(res, "Failed to create tech support ticket")
        if not data:
            raise Exception("Database failed to return created tech support ticket data.")
        return data[0]
    
    def get_recent_tasks_and_journals(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetches tasks and journal entries created in the last 3 days.

        This provides a lean, relevant context for synthesis agents, helping them
        generate more informed and context-aware responses.

        Returns:
            A dictionary containing two keys, 'tasks' and 'journal_entries',
            each with a list of recent items.
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

            # Fetch recent journal entries
            journal_res = self.supabase.table('journals').select('*') \
                .eq('user_id', self.user_id) \
                .gte('created_at', three_days_ago_iso) \
                .order('created_at', desc=True).limit(25).execute()
            results["journal_entries"] = self._handle_db_response(journal_res, "No recent journal entries found.")

        except Exception as e:
            logger.error(f"DB Error fetching recent context: {e}")

        return results

    # --- Financial Table Operations ---

    def create_financial_transaction_in_db(self, transaction_type: str, amount: float, currency: str, category: str, description: str) -> Dict[str, Any]:
        """
        Inserts a new financial transaction into the database.

        Args:
            transaction_type: The type of transaction (e.g., 'income', 'expense').
            amount: The monetary value of the transaction.
            currency: The currency of the transaction (e.g., 'USD').
            category: The category of the transaction (e.g., 'groceries', 'salary').
            description: A brief description of the transaction.

        Returns:
            A dictionary representing the newly created transaction.

        Raises:
            ValueError: If any of the required fields are missing.
            Exception: If the database fails to return the created transaction data.
        """
        if not all([transaction_type, amount, currency, category]):
            raise ValueError("Missing required fields for financial transaction.")

        transaction_data = {
            "user_id": self.user_id,
            "transaction_type": transaction_type,
            "amount": amount,
            "currency": currency,
            "category": category,
            "description": description,
            "transaction_date": datetime.now(timezone.utc).isoformat()
        }
        res = self.supabase.table("financial_transactions").insert(transaction_data).execute()
        data = self._handle_db_response(res, "Failed to insert financial transaction")
        if not data:
            raise Exception("Database failed to return created financial transaction data.")
        return data[0]

    def create_or_update_budget_in_db(self, category: str, amount: float, period: str) -> Dict[str, Any]:
        """
        Creates or updates a budget for a given category and time period.

        This method performs an 'upsert' operation based on the user, category,
        and period, allowing users to set a budget and update it later.

        Args:
            category: The category the budget applies to (e.g., 'food').
            amount: The budgeted amount.
            period: The budget period (e.g., 'monthly', 'weekly', 'yearly').

        Returns:
            A dictionary representing the created or updated budget.

        Raises:
            ValueError: If required fields are missing or the period is unsupported.
            Exception: If the database fails to return the upserted data.
        """
        if not all([category, amount, period]):
            raise ValueError("Missing required fields for budget.")

        today = date.today()
        if period == 'monthly':
            start_date = today.replace(day=1)
            end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        elif period == 'weekly':
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)
        elif period == 'yearly':
            start_date = today.replace(month=1, day=1)
            end_date = today.replace(month=12, day=31)
        else:
            raise ValueError(f"Unsupported budget period: {period}")

        budget_data = {
            "user_id": self.user_id,
            "category": category,
            "amount": amount,
            "period": period,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }

        res = self.supabase.table("budgets").upsert(budget_data, on_conflict="user_id,category,period").execute()
        data = self._handle_db_response(res, f"Failed to upsert budget for category {category}")
        if not data:
            raise Exception("Database failed to return created/updated budget data.")
        return data[0]