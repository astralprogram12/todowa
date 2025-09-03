#!/usr/bin/env python3
"""
AI Tools Library - The Execution Layer (V4 - Resilient Tools)
"""

import logging
from typing import Dict, Any, Optional, List
from functools import wraps
from datetime import datetime

# Imports the @tool decorator from your registry file
from tools import tool 
from database import DatabaseManager


# pip install -U duckduckgo-search
from ddgs.ddgs import DDGS


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global context for dependency injection
_context = {"supabase": None, "user_id": None}

def set_context(supabase_client, user_id: str):
    """Sets the global context for Supabase and user ID."""
    _context["supabase"] = supabase_client
    _context["user_id"] = user_id



@tool(name="internet_search", description="Searches the web using DuckDuckGo for up-to-date information.", category="web")
def internet_search(query: str, num_results: int = 5) -> Dict[str, Any]:
    """
    Performs an internet search using the ddgs library. This version includes
    a dedicated safety net and uses the correct 'query' argument.
    """
    logger.info(f"Performing internet search for: '{query}'")
    
    try:
        with DDGS() as ddgs:
            # --- THE CRITICAL FIX: Changed 'keywords' to 'query' ---
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

    snippets = []
    for result in results:
        if result.get("body"):
            snippets.append({
                "title": result.get("title"),
                "link": result.get("href"),
                "snippet": result.get("body")
            })

    return {
        "success": True, 
        "data": {
            "summary": f"Found {len(snippets)} relevant results for '{query}'.",
            "results": snippets
        }
    }

# ==================== DECORATOR FOR ABSTRACTION ====================

def db_tool_handler(func):
    """Decorator to handle database connection, execution, and response formatting."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            supabase = _context.get("supabase")
            user_id = _context.get("user_id")
            if not supabase or not user_id:
                raise ConnectionError("Database context not set.")

            db_manager = DatabaseManager(supabase, user_id)
            
            result_data = func(db_manager, *args, **kwargs)
            
            return {"success": True, "data": result_data}
        except Exception as e:
            # Log the full traceback for debugging
            logger.exception(f"Error in tool '{func.__name__}': {e}")
            return {"success": False, "error": str(e)}
    return wrapper

# ==================== TASK & REMINDER TOOLS ====================
# These are already robust and need no changes.
@tool(name="create_task", description="Creates a new task with a title, a short description, and detailed notes.", category="tasks")
@db_tool_handler
def create_task(db_manager: DatabaseManager, title: str, description: Optional[str] = None, notes: Optional[str] = None, priority: str = "medium", due_date: Optional[str] = None, category: str = "general"):
    """
    UPDATED: This tool now accepts a 'description' parameter, which is passed to the database layer.
    """
    return db_manager.create_task(
        title=title,
        description=description, # <-- NEWLY ADDED
        notes=notes,
        priority=priority,
        due_date=due_date,
        category=category
    )

@tool(name="update_task", description="Updates an existing task by its specific ID.", category="tasks")
@db_tool_handler
def update_task(db_manager: DatabaseManager, task_id: str, patch: Dict[str, Any]):
    """
    NO CHANGE NEEDED: This is correct. The smart agent now finds and provides the 'task_id'.
    """
    return db_manager.update_task(task_id, patch)

@tool(name="delete_task", description="Deletes an existing task by its specific ID.", category="tasks")
@db_tool_handler
def delete_task(db_manager: DatabaseManager, task_id: str):
    """
    NO CHANGE NEEDED: This is correct. The smart agent now finds and provides the 'task_id'.
    """
    return db_manager.delete_task(task_id)

@tool(name="get_tasks", description="Retrieves a list of tasks, either by specific IDs or with filters.", category="tasks")
@db_tool_handler
def get_tasks(
    db_manager: DatabaseManager, 
    status: Optional[str] = None, 
    priority: Optional[str] = None, 
    category: Optional[str] = None, 
    limit: int = 25, 
    order_by: str = 'created_at', 
    ascending: bool = False,
    task_ids: Optional[List[str]] = None  # <-- ADD THIS NEW PARAMETER
):
    """
    Retrieves tasks. 
    If a list of task_ids is provided, it fetches those specific tasks.
    Otherwise, it uses the filter arguments (status, priority, etc.).
    """
    # ADD THIS LOGIC
    if task_ids:
        # If we have specific IDs, use a new dedicated database method.
        # The other filters are ignored in this case.
        return db_manager.get_tasks_by_ids(task_ids, order_by=order_by, ascending=ascending)
    else:
        # This is the original behavior for simple filtering.
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
    return db_manager.get_task_stats()
# ==================== JOURNAL TOOLS (NOW RESILIENT) ====================

### <<< THIS IS THE CRITICAL FIX >>> ###

@tool(name="create_journal_entry", category="journal")
@db_tool_handler
def create_journal_entry(db_manager: DatabaseManager, content: Optional[str] = None, title: Optional[str] = None, category: str = "general", entry_type: str = 'free_form') -> Dict:
    """Creates a new journal entry. Handles missing title or content by creating defaults."""
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
    return db_manager.search_journal_entries_by_titles(titles=titles, limit=limit)

@tool(name="update_journal_entry", category="journal")
@db_tool_handler
def update_journal_entry(db_manager: DatabaseManager, patch: dict, id: Optional[int] = None, titleMatch: Optional[str] = None) -> List[Dict]:
    """
    Updates a journal entry. Prefers using the unique 'id' if provided. 
    Falls back to using 'titleMatch' if 'id' is not available.
    """
    if not id and not titleMatch:
        raise ValueError("You must provide either an 'id' or a 'titleMatch' to update an entry.")
    
    return db_manager.update_journal_entry_in_db(id=id, title_match=titleMatch, patch=patch)

@tool(name="delete_journal_entry", category="journal")
@db_tool_handler
def delete_journal_entry(db_manager: DatabaseManager, id: Optional[int] = None, titleMatch: Optional[str] = None) -> List[Dict]:
    """
    Deletes a journal entry. Prefers using the unique 'id' if provided.
    Falls back to using 'titleMatch' if 'id' is not available.
    """
    if not id and not titleMatch:
        raise ValueError("You must provide either an 'id' or a 'titleMatch' to delete an entry.")

    return db_manager.delete_journal_entry_in_db(id=id, title_match=titleMatch)

# ==================== AI BRAIN (MEMORY) TOOLS ====================
# These are already robust and need no changes.



@tool(name="create_or_update_memory", description="Creates or updates an AI brain memory.", category="ai_brain")
@db_tool_handler
def create_or_update_memory(db_manager: DatabaseManager, memory_type: str, data: Dict, content: str, importance: int = 10):
    return db_manager.create_or_update_memory(memory_type=memory_type, data=data, content=content, importance=importance)

@tool(name="get_memories", description="Retrieves AI brain memories, optionally filtered by type.", category="ai_brain")
@db_tool_handler
def get_memories(db_manager: DatabaseManager, memory_type: Optional[str] = None, limit: int = 25):
    return db_manager.get_memories(memory_type=memory_type, limit=limit)

@tool(name="delete_memory", description="Deletes a specific memory entry by its ID.", category="ai_brain")
@db_tool_handler
def delete_memory(db_manager: DatabaseManager, memory_id: str):
    return db_manager.delete_memory(memory_id)

####################################################################################################3

# ==================== SCHEDULE TOOLS ====================

@tool(name="create_schedule", description="Saves a new scheduled action to the database.", category="scheduling")
@db_tool_handler
def create_schedule(db_manager: DatabaseManager, action_type: str, action_payload: Dict, schedule_type: str, schedule_value: str, timezone: str, next_run_at: str):
    """Creates a new schedule record."""
    return db_manager.create_schedule(
        action_type=action_type, action_payload=action_payload,
        schedule_type=schedule_type, schedule_value=schedule_value,
        timezone=timezone, next_run_at=next_run_at
    )

@tool(name="get_schedules", description="Retrieves a list of the user's scheduled actions.", category="scheduling")
@db_tool_handler
def get_schedules(db_manager: DatabaseManager, status: str = 'active', limit: int = 50) -> List[Dict[str, Any]]:
    """
    NEW: Fetches a list of schedules. The agent will use this to find candidates for updating or deleting.
    """
    return db_manager.get_schedules(status=status, limit=limit)

@tool(name="update_schedule", description="Updates an existing schedule by its specific ID.", category="scheduling")
@db_tool_handler
def update_schedule(db_manager: DatabaseManager, schedule_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    NEW: Updates a schedule. The agent must provide the unique ID.
    """
    return db_manager.update_schedule(schedule_id=schedule_id, patch=patch)

@tool(name="delete_schedule", description="Deletes/cancels an existing schedule by its specific ID.", category="scheduling")
@db_tool_handler
def delete_schedule(db_manager: DatabaseManager, schedule_id: str) -> bool:
    """
    NEW: Deletes a schedule. The agent must provide the unique ID.
    """
    return db_manager.delete_schedule(schedule_id=schedule_id)

# ==================== FINANCIAL TOOLS ====================

@tool(name="create_financial_transaction", description="Creates a new financial transaction (income or expense).", category="financial")
@db_tool_handler
def create_financial_transaction(db_manager: DatabaseManager, transaction_type: str, amount: float, currency: str, category: str, description: str):
    """Creates a new financial transaction record."""
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
    """Creates or updates a budget record."""
    return db_manager.create_or_update_budget_in_db(
        category=category,
        amount=amount,
        period=period
    )