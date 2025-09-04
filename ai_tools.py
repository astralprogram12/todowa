"""
AI Tools Library: The Execution Layer for the Multi-Agent System.

This module defines the concrete implementations of the tools that AI agents
can execute. Each function in this file is decorated with `@tool` from the
`tools` module, registering it with the central `tool_registry`. These tools
form the practical capabilities of the AI assistant, allowing it to perform
actions like searching the internet, managing a database, and more.

A key feature of this module is the `db_tool_handler` decorator, which
abstracts away common logic for database-dependent tools, such as response
formatting and error handling.
"""

import logging
from typing import Dict, Any, Optional, List
from functools import wraps
from datetime import datetime

from tools import tool 
from database import DatabaseManager
from ddgs.ddgs import DDGS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@tool(name="internet_search", description="Searches the web using DuckDuckGo for up-to-date information.", category="web")
def internet_search(query: str, num_results: int = 5) -> Dict[str, Any]:
    """
    Performs an internet search using the DuckDuckGo Search library.

    Args:
        query: The search query.
        num_results: The maximum number of results to return.

    Returns:
        A dictionary containing the success status and the search results,
        or an error message if the search fails.
    """
    logger.info(f"Performing internet search for: '{query}'")
    
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query=query, max_results=num_results))

    except Exception as e:
        logger.error(f"The 'ddgs' library failed for query '{query}'. Error: {e}")
        return {
            "success": False,
            "error": f"The web search library failed to execute for the query '{query}'. Please try a different query."
        }

    if not results:
        logger.warning(f"Web search for '{query}' yielded no results.")
        return {"success": True, "data": {"summary": f"No search results found for '{query}'.", "results": []}}

    snippets = [{"title": r.get("title"), "link": r.get("href"), "snippet": r.get("body")} for r in results if r.get("body")]

    return {
        "success": True, 
        "data": {
            "summary": f"Found {len(snippets)} relevant results for '{query}'.",
            "results": snippets
        }
    }

def db_tool_handler(func):
    """
    A decorator for database tools to standardize response and error handling.

    This decorator wraps functions that interact with the database. It injects
    the `db_manager` instance, calls the underlying function, and formats the
    output into a standard dictionary format (`{'success': True, 'data': ...}`).
    It also provides a unified error handling mechanism, catching exceptions
    and formatting them into a standard error response.

    Args:
        func: The tool function to be decorated.

    Returns:
        The wrapped function with standardized response and error handling.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            if 'db_manager' not in kwargs:
                raise ValueError(f"Tool '{func.__name__}' requires a 'db_manager' argument.")
            
            result_data = func(*args, **kwargs)
            
            return {"success": True, "data": result_data}
        except Exception as e:
            logger.exception(f"Error in tool '{func.__name__}': {e}")
            return {"success": False, "error": str(e)}
    return wrapper

# ==================== TASK & REMINDER TOOLS ====================
@tool(name="create_task", description="Creates a new task with a title, a short description, and detailed notes.", category="tasks")
@db_tool_handler
def create_task(db_manager: DatabaseManager, title: str, description: Optional[str] = None, notes: Optional[str] = None, priority: str = "medium", due_date: Optional[str] = None, category: str = "general"):
    """
    Creates a new task in the database.

    Args:
        db_manager: The database manager instance.
        title: The title of the task.
        description: A brief summary of the task.
        notes: Detailed notes for the task.
        priority: The priority of the task.
        due_date: The due date for the task.
        category: The category of the task.

    Returns:
        The newly created task object.
    """
    return db_manager.create_task(
        title=title,
        description=description,
        notes=notes,
        priority=priority,
        due_date=due_date,
        category=category
    )

@tool(name="update_task", description="Updates an existing task by its specific ID.", category="tasks")
@db_tool_handler
def update_task(db_manager: DatabaseManager, task_id: str, patch: Dict[str, Any]):
    """
    Updates an existing task with new data.

    Args:
        db_manager: The database manager instance.
        task_id: The unique ID of the task to update.
        patch: A dictionary of fields to update.

    Returns:
        The updated task object.
    """
    return db_manager.update_task(task_id, patch)

@tool(name="delete_task", description="Deletes an existing task by its specific ID.", category="tasks")
@db_tool_handler
def delete_task(db_manager: DatabaseManager, task_id: str):
    """
    Deletes a task from the database.

    Args:
        db_manager: The database manager instance.
        task_id: The unique ID of the task to delete.

    Returns:
        A boolean indicating the success of the deletion.
    """
    return db_manager.delete_task(task_id)

@tool(name="get_tasks", description="Retrieves a list of tasks, either by specific IDs or with filters.", category="tasks")
@db_tool_handler
def get_tasks(db_manager: DatabaseManager, status: Optional[str] = None, priority: Optional[str] = None, category: Optional[str] = None, limit: int = 25, order_by: str = 'created_at', ascending: bool = False, task_ids: Optional[List[str]] = None):
    """
    Retrieves tasks based on specified criteria.

    If `task_ids` are provided, it fetches those specific tasks. Otherwise, it
    filters by status, priority, and category.

    Args:
        db_manager: The database manager instance.
        status: Filter by task status.
        priority: Filter by task priority.
        category: Filter by task category.
        limit: The maximum number of tasks to return.
        order_by: The field to sort the tasks by.
        ascending: Whether to sort in ascending order.
        task_ids: A list of specific task IDs to retrieve.

    Returns:
        A list of task objects.
    """
    if task_ids:
        return db_manager.get_tasks_by_ids(task_ids, order_by=order_by, ascending=ascending)
    else:
        return db_manager.get_tasks(
            status=status, 
            priority=priority, 
            category=category, 
            limit=limit, 
            order_by=order_by, 
            ascending=ascending
        )
    
@tool(name="get_task_stats", description="Gets statistics about the user's tasks.", category="tasks")
@db_tool_handler
def get_task_stats(db_manager: DatabaseManager):
    """
    Retrieves statistics about the user's tasks.

    Args:
        db_manager: The database manager instance.

    Returns:
        A dictionary with task statistics (e.g., completed_count, pending_count).
    """
    return db_manager.get_task_stats()

# ==================== JOURNAL TOOLS ====================

@tool(name="create_journal_entry", category="journal")
@db_tool_handler
def create_journal_entry(db_manager: DatabaseManager, content: Optional[str] = None, title: Optional[str] = None, category: str = "general", entry_type: str = 'free_form') -> Dict:
    """
    Creates a new journal entry.

    If only content is provided, a title is generated from it. If only a title
    is provided, it's used as the content.

    Args:
        db_manager: The database manager instance.
        content: The main content of the journal entry.
        title: The title of the journal entry.
        category: The category for the entry.
        entry_type: The type of journal entry.

    Returns:
        The newly created journal entry.
    """
    if not content and not title:
        raise ValueError("Cannot create a journal entry with no title or content.")
    final_content = content or title
    final_title = title or f"Note: {final_content[:40]}..."
    return db_manager.create_journal_entry_in_db(
        title=final_title, 
        content=final_content, 
        category=category, 
        entry_type=entry_type
    )

@tool(name="search_journal_entries", category="journal")
@db_tool_handler
def search_journal_entries(db_manager: DatabaseManager, titles: List[str], limit: int = 10) -> List[Dict]:
    """
    Searches for journal entries by their titles.

    Args:
        db_manager: The database manager instance.
        titles: A list of titles to search for.
        limit: The maximum number of entries to return.

    Returns:
        A list of matching journal entries.
    """
    return db_manager.search_journal_entries_by_titles(titles=titles, limit=limit)

@tool(name="update_journal_entry", category="journal")
@db_tool_handler
def update_journal_entry(db_manager: DatabaseManager, patch: dict, id: Optional[int] = None, titleMatch: Optional[str] = None) -> List[Dict]:
    """
    Updates a journal entry, identified by ID or title.

    Args:
        db_manager: The database manager instance.
        patch: A dictionary of fields to update.
        id: The unique ID of the entry to update.
        titleMatch: The exact title of the entry to update.

    Returns:
        The updated journal entry.
    """
    if not id and not titleMatch:
        raise ValueError("You must provide either an 'id' or a 'titleMatch' to update an entry.")
    
    return db_manager.update_journal_entry_in_db(id=id, title_match=titleMatch, patch=patch)

@tool(name="delete_journal_entry", category="journal")
@db_tool_handler
def delete_journal_entry(db_manager: DatabaseManager, id: Optional[int] = None, titleMatch: Optional[str] = None) -> List[Dict]:
    """
    Deletes a journal entry, identified by ID or title.

    Args:
        db_manager: The database manager instance.
        id: The unique ID of the entry to delete.
        titleMatch: The exact title of the entry to delete.

    Returns:
        The deleted journal entry.
    """
    if not id and not titleMatch:
        raise ValueError("You must provide either an 'id' or a 'titleMatch' to delete an entry.")

    return db_manager.delete_journal_entry_in_db(id=id, title_match=titleMatch)

# ==================== AI BRAIN (MEMORY) TOOLS ====================

@tool(name="create_or_update_memory", description="Creates or updates an AI brain memory.", category="ai_brain")
@db_tool_handler
def create_or_update_memory(db_manager: DatabaseManager, memory_type: str, data: Dict, content: str, importance: int = 10):
    """
    Creates or updates an AI's internal memory.

    Args:
        db_manager: The database manager instance.
        memory_type: The type of memory to create/update.
        data: The structured data for the memory.
        content: A text representation of the memory.
        importance: The importance level of the memory.

    Returns:
        The created or updated memory object.
    """
    return db_manager.create_or_update_memory(memory_type=memory_type, data=data, content=content, importance=importance)

@tool(name="get_memories", description="Retrieves AI brain memories, optionally filtered by type.", category="ai_brain")
@db_tool_handler
def get_memories(db_manager: DatabaseManager, memory_type: Optional[str] = None, limit: int = 25):
    """
    Retrieves AI memories from the database.

    Args:
        db_manager: The database manager instance.
        memory_type: Filter memories by a specific type.
        limit: The maximum number of memories to return.

    Returns:
        A list of memory objects.
    """
    return db_manager.get_memories(memory_type=memory_type, limit=limit)

@tool(name="delete_memory", description="Deletes a specific memory entry by its ID.", category="ai_brain")
@db_tool_handler
def delete_memory(db_manager: DatabaseManager, memory_id: str):
    """
    Deletes an AI memory from the database.

    Args:
        db_manager: The database manager instance.
        memory_id: The unique ID of the memory to delete.

    Returns:
        A boolean indicating the success of the deletion.
    """
    return db_manager.delete_memory(memory_id)

# ==================== SCHEDULE TOOLS ====================

@tool(name="create_schedule", description="Saves a new scheduled action to the database.", category="scheduling")
@db_tool_handler
def create_schedule(db_manager: DatabaseManager, action_type: str, action_payload: Dict, schedule_type: str, schedule_value: str, timezone: str, next_run_at: str):
    """
    Creates a new scheduled action.

    Args:
        db_manager: The database manager instance.
        action_type: The type of action to schedule.
        action_payload: The payload for the scheduled action.
        schedule_type: The type of schedule (e.g., 'recurring').
        schedule_value: The value for the schedule (e.g., a cron string).
        timezone: The timezone for the schedule.
        next_run_at: The next execution time for the schedule.

    Returns:
        The newly created schedule object.
    """
    return db_manager.create_schedule(
        action_type=action_type, action_payload=action_payload,
        schedule_type=schedule_type, schedule_value=schedule_value,
        timezone=timezone, next_run_at=next_run_at
    )

@tool(name="get_schedules", description="Retrieves a list of the user's scheduled actions.", category="scheduling")
@db_tool_handler
def get_schedules(db_manager: DatabaseManager, status: str = 'active', limit: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieves a list of scheduled actions.

    Args:
        db_manager: The database manager instance.
        status: Filter schedules by status.
        limit: The maximum number of schedules to return.

    Returns:
        A list of schedule objects.
    """
    return db_manager.get_schedules(status=status, limit=limit)

@tool(name="update_schedule", description="Updates an existing schedule by its specific ID.", category="scheduling")
@db_tool_handler
def update_schedule(db_manager: DatabaseManager, schedule_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Updates a scheduled action.

    Args:
        db_manager: The database manager instance.
        schedule_id: The unique ID of the schedule to update.
        patch: A dictionary of fields to update.

    Returns:
        The updated schedule object.
    """
    return db_manager.update_schedule(schedule_id=schedule_id, patch=patch)

@tool(name="delete_schedule", description="Deletes/cancels an existing schedule by its specific ID.", category="scheduling")
@db_tool_handler
def delete_schedule(db_manager: DatabaseManager, schedule_id: str) -> bool:
    """
    Deletes a scheduled action.

    Args:
        db_manager: The database manager instance.
        schedule_id: The unique ID of the schedule to delete.

    Returns:
        A boolean indicating the success of the deletion.
    """
    return db_manager.delete_schedule(schedule_id=schedule_id)

# ==================== FINANCIAL TOOLS ====================

@tool(name="create_financial_transaction", description="Creates a new financial transaction (income or expense).", category="financial")
@db_tool_handler
def create_financial_transaction(db_manager: DatabaseManager, transaction_type: str, amount: float, currency: str, category: str, description: str):
    """
    Creates a new financial transaction.

    Args:
        db_manager: The database manager instance.
        transaction_type: The type of transaction (e.g., 'income').
        amount: The amount of the transaction.
        currency: The currency of the transaction.
        category: The category of the transaction.
        description: A description of the transaction.

    Returns:
        The newly created transaction object.
    """
    return db_manager.create_financial_transaction_in_db(
        transaction_type=transaction_type,
        amount=amount,
        currency=currency,
        category=category,
        description=description
    )

@tool(name="create_or_update_budget", description="Creates or updates a budget for a specific category.", category="financial")
@db_tool_handler
def create_or_update_budget(db_manager: DatabaseManager, category: str, amount: float, period: str):
    """
    Creates or updates a budget.

    Args:
        db_manager: The database manager instance.
        category: The category for the budget.
        amount: The amount for the budget.
        period: The period for the budget (e.g., 'monthly').

    Returns:
        The created or updated budget object.
    """
    return db_manager.create_or_update_budget_in_db(
        category=category,
        amount=amount,
        period=period
    )

# ==================== TECH SUPPORT TOOLS ====================

@tool(name="create_tech_support_ticket", description="Creates a new tech support ticket for a user.", category="tech_support")
@db_tool_handler
def create_tech_support_ticket(db_manager: DatabaseManager, message: str) -> Dict[str, Any]:
    """
    Creates a new tech support ticket.

    Args:
        db_manager: The database manager instance.
        message: The user's message for the ticket.

    Returns:
        The newly created tech support ticket object.
    """
    return db_manager.create_tech_support_ticket(message=message)
