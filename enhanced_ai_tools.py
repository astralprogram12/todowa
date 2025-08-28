import os
import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from croniter import croniter
from enhanced_tools import tool, tool_registry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIToolsError(Exception):
    """Custom exception for AI Tools operations"""
    pass

# ==================== TASK MANAGEMENT ====================

try:
    import services
except ImportError:
    services = None

@tool(name="send_reply_message", description="Sends a final text message to the user.", category="communication", auto_inject=["user_id"])
def send_reply_message(phone_number: str, message: str, user_id: str = None) -> Dict[str, Any]:
    """
    Sends a final reply message to the user's phone number.
    
    Args:
        phone_number: The user's phone number to send the message to.
        message: The text content of the message.
        user_id: Auto-injected user identifier for logging.
    
    Returns:
        Dict indicating success or failure.
    """
    # Check if we're in CLI mode
    if phone_number == "CLI_TEST_USER":
        logger.info(f"CLI Mode: Message ready for user {user_id}: {message[:100]}...")
        return {"success": True, "message": "Message prepared for CLI display."}
    
    if not services:
        error_msg = "services.py module could not be loaded. Cannot send message."
        logger.error(error_msg)
        return {"success": False, "error": error_msg}
        
    try:
        logger.info(f"Sending reply via Fonnte to {phone_number} for user {user_id}")
        result = services.send_fonnte_message(phone_number, message)
        
        if result and result.get("status"):
            return {"success": True, "message": "Message sent successfully."}
        else:
            reason = result.get("reason", "Unknown Fonnte API error") if result else "No response from Fonnte API"
            raise AIToolsError(f"Failed to send message via Fonnte: {reason}")
            
    except Exception as e:
        logger.error(f"Error in send_reply_message tool: {str(e)}")
        return {"success": False, "error": str(e)}


@tool(name="create_task", description="Create a new task", category="tasks", auto_inject=["supabase", "user_id"])
def create_task(title: str, description: str = "", priority: str = "medium", 
               due_date: str = None, category: str = "general", 
               supabase=None, user_id: str = None) -> Dict[str, Any]:
    """
    Create a new task with comprehensive details
    
    Args:
        title: Task title (required)
        description: Detailed description 
        priority: low, medium, high, urgent
        due_date: ISO format date string (YYYY-MM-DD)
        category: Task category for organization
        supabase: Auto-injected Supabase client
        user_id: Auto-injected user identifier
    
    Returns:
        Dict containing the created task data
    """
    try:
        if not supabase:
            raise AIToolsError("Database connection not available")
        
        # Auto-categorize based on keywords if category is 'general'
        if category == "general":
            category = _auto_categorize_task(title, description)
        
        task_data = {
            "user_id": user_id,
            "title": title,
            "description": description,
            "priority": priority,
            "status": "pending",
            "category": category,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        if due_date:
            task_data["due_date"] = due_date
        
        result = supabase.table("tasks").insert(task_data).execute()
        
        if result.data:
            logger.info(f"Task created: {title} (ID: {result.data[0]['id']})")
            return {"success": True, "data": result.data[0]}
        else:
            raise AIToolsError("Failed to create task")
            
    except Exception as e:
        logger.error(f"Error creating task: {str(e)}")
        return {"success": False, "error": str(e)}

@tool(name="get_tasks", description="Retrieve tasks with filtering options", category="tasks", auto_inject=["supabase", "user_id"])
def get_tasks(status: str = None, priority: str = None, category: str = None,
             due_before: str = None, limit: int = 50,
             supabase=None, user_id: str = None) -> Dict[str, Any]:
    """
    Retrieve tasks with comprehensive filtering
    
    Args:
        status: Filter by status (pending, in_progress, completed, cancelled)
        priority: Filter by priority (low, medium, high, urgent)
        category: Filter by category
        due_before: Filter tasks due before this date (ISO format)
        limit: Maximum number of tasks to return
        supabase: Auto-injected Supabase client
        user_id: Auto-injected user identifier
    
    Returns:
        Dict containing the filtered tasks
    """
    try:
        if not supabase:
            raise AIToolsError("Database connection not available")
        
        query = supabase.table("tasks").select("*").eq("user_id", user_id)
        
        if status:
            query = query.eq("status", status)
        if priority:
            query = query.eq("priority", priority)
        if category:
            query = query.eq("category", category)
        if due_before:
            query = query.lt("due_date", due_before)
            
        query = query.order("created_at", desc=True).limit(limit)
        result = query.execute()
        
        logger.info(f"Retrieved {len(result.data)} tasks")
        return {"success": True, "data": result.data, "count": len(result.data)}
        
    except Exception as e:
        logger.error(f"Error retrieving tasks: {str(e)}")
        return {"success": False, "error": str(e)}

@tool(name="update_task", description="Update an existing task", category="tasks", auto_inject=["supabase", "user_id"])
def update_task(task_id: int, title: str = None, description: str = None,
               status: str = None, priority: str = None, due_date: str = None,
               category: str = None, supabase=None, user_id: str = None) -> Dict[str, Any]:
    """
    Update an existing task with new information
    
    Args:
        task_id: ID of the task to update
        title: New title (optional)
        description: New description (optional)
        status: New status (pending, in_progress, completed, cancelled)
        priority: New priority (low, medium, high, urgent)
        due_date: New due date (ISO format)
        category: New category
        supabase: Auto-injected Supabase client
        user_id: Auto-injected user identifier
    
    Returns:
        Dict containing the updated task data
    """
    try:
        if not supabase:
            raise AIToolsError("Database connection not available")
        
        update_data = {"updated_at": datetime.now().isoformat()}
        
        if title is not None:
            update_data["title"] = title
        if description is not None:
            update_data["description"] = description
        if status is not None:
            update_data["status"] = status
        if priority is not None:
            update_data["priority"] = priority
        if due_date is not None:
            update_data["due_date"] = due_date
        if category is not None:
            update_data["category"] = category
        
        result = supabase.table("tasks").update(update_data).eq("id", task_id).eq("user_id", user_id).execute()
        
        if result.data:
            logger.info(f"Task updated: {task_id}")
            return {"success": True, "data": result.data[0]}
        else:
            raise AIToolsError(f"Task {task_id} not found or access denied")
            
    except Exception as e:
        logger.error(f"Error updating task {task_id}: {str(e)}")
        return {"success": False, "error": str(e)}

@tool(name="delete_task", description="Delete a task", category="tasks", auto_inject=["supabase", "user_id"])
def delete_task(task_id: int, supabase=None, user_id: str = None) -> Dict[str, Any]:
    """
    Delete a task permanently
    
    Args:
        task_id: ID of the task to delete
        supabase: Auto-injected Supabase client
        user_id: Auto-injected user identifier
    
    Returns:
        Dict indicating success or failure
    """
    try:
        if not supabase:
            raise AIToolsError("Database connection not available")
        
        result = supabase.table("tasks").delete().eq("id", task_id).eq("user_id", user_id).execute()
        
        if result.data:
            logger.info(f"Task deleted: {task_id}")
            return {"success": True, "message": f"Task {task_id} deleted successfully"}
        else:
            raise AIToolsError(f"Task {task_id} not found or access denied")
            
    except Exception as e:
        logger.error(f"Error deleting task {task_id}: {str(e)}")
        return {"success": False, "error": str(e)}

# ==================== REMINDER MANAGEMENT ====================

@tool(name="create_reminder", description="Create a reminder for a task or standalone", category="reminders", auto_inject=["supabase", "user_id"])
def create_reminder(title: str, remind_at: str, description: str = "",
                   task_id: int = None, supabase=None, user_id: str = None) -> Dict[str, Any]:
    """
    Create a reminder with smart task creation
    
    Args:
        title: Reminder title
        remind_at: When to remind (ISO format datetime)
        description: Additional details
        task_id: Link to existing task (optional)
        supabase: Auto-injected Supabase client
        user_id: Auto-injected user identifier
    
    Returns:
        Dict containing the created reminder data
    """
    try:
        if not supabase:
            raise AIToolsError("Database connection not available")
        
        # Smart feature: if no task_id provided, create a task automatically
        if task_id is None:
            task_result = create_task(
                title=title, 
                description=description or f"Auto-created for reminder: {title}",
                supabase=supabase,
                user_id=user_id
            )
            if task_result["success"]:
                task_id = task_result["data"]["id"]
            else:
                raise AIToolsError("Failed to create associated task")
        
        reminder_data = {
            "user_id": user_id,
            "task_id": task_id,
            "title": title,
            "description": description,
            "remind_at": remind_at,
            "is_sent": False,
            "created_at": datetime.now().isoformat()
        }
        
        result = supabase.table("reminders").insert(reminder_data).execute()
        
        if result.data:
            logger.info(f"Reminder created: {title} for {remind_at}")
            return {"success": True, "data": result.data[0]}
        else:
            raise AIToolsError("Failed to create reminder")
            
    except Exception as e:
        logger.error(f"Error creating reminder: {str(e)}")
        return {"success": False, "error": str(e)}

@tool(name="get_reminders", description="Get reminders with filtering", category="reminders", auto_inject=["supabase", "user_id"])
def get_reminders(is_sent: bool = None, task_id: int = None, 
                 remind_before: str = None, limit: int = 50,
                 supabase=None, user_id: str = None) -> Dict[str, Any]:
    """
    Retrieve reminders with filtering options
    
    Args:
        is_sent: Filter by sent status
        task_id: Filter by specific task
        remind_before: Filter reminders due before this datetime
        limit: Maximum number of reminders to return
        supabase: Auto-injected Supabase client
        user_id: Auto-injected user identifier
    
    Returns:
        Dict containing the filtered reminders
    """
    try:
        if not supabase:
            raise AIToolsError("Database connection not available")
        
        query = supabase.table("reminders").select("*, tasks(*)").eq("user_id", user_id)
        
        if is_sent is not None:
            query = query.eq("is_sent", is_sent)
        if task_id is not None:
            query = query.eq("task_id", task_id)
        if remind_before:
            query = query.lt("remind_at", remind_before)
            
        query = query.order("remind_at", desc=False).limit(limit)
        result = query.execute()
        
        logger.info(f"Retrieved {len(result.data)} reminders")
        return {"success": True, "data": result.data, "count": len(result.data)}
        
    except Exception as e:
        logger.error(f"Error retrieving reminders: {str(e)}")
        return {"success": False, "error": str(e)}

# ==================== CATEGORY MANAGEMENT ====================

@tool(name="create_category", description="Create a new category", category="categories", auto_inject=["supabase", "user_id"])
def create_category(name: str, description: str = "", color: str = "#3B82F6",
                   supabase=None, user_id: str = None) -> Dict[str, Any]:
    """
    Create a new category for organizing tasks
    
    Args:
        name: Category name
        description: Category description
        color: Hex color code for the category
        supabase: Auto-injected Supabase client
        user_id: Auto-injected user identifier
    
    Returns:
        Dict containing the created category data
    """
    try:
        if not supabase:
            raise AIToolsError("Database connection not available")
        
        category_data = {
            "user_id": user_id,
            "name": name,
            "description": description,
            "color": color,
            "created_at": datetime.now().isoformat()
        }
        
        result = supabase.table("categories").insert(category_data).execute()
        
        if result.data:
            logger.info(f"Category created: {name}")
            return {"success": True, "data": result.data[0]}
        else:
            raise AIToolsError("Failed to create category")
            
    except Exception as e:
        logger.error(f"Error creating category: {str(e)}")
        return {"success": False, "error": str(e)}

@tool(name="get_categories", description="Get all categories", category="categories", auto_inject=["supabase", "user_id"])
def get_categories(supabase=None, user_id: str = None) -> Dict[str, Any]:
    """
    Retrieve all categories for the user
    
    Args:
        supabase: Auto-injected Supabase client
        user_id: Auto-injected user identifier
    
    Returns:
        Dict containing all categories
    """
    try:
        if not supabase:
            raise AIToolsError("Database connection not available")
        
        result = supabase.table("categories").select("*").eq("user_id", user_id).order("name").execute()
        
        logger.info(f"Retrieved {len(result.data)} categories")
        return {"success": True, "data": result.data, "count": len(result.data)}
        
    except Exception as e:
        logger.error(f"Error retrieving categories: {str(e)}")
        return {"success": False, "error": str(e)}

# ==================== ANALYTICS & REPORTING ====================

@tool(name="get_task_analytics", description="Get comprehensive task analytics", category="analytics", auto_inject=["supabase", "user_id"])
def get_task_analytics(days: int = 30, supabase=None, user_id: str = None) -> Dict[str, Any]:
    """
    Generate comprehensive task analytics
    
    Args:
        days: Number of days to analyze (default: 30)
        supabase: Auto-injected Supabase client
        user_id: Auto-injected user identifier
    
    Returns:
        Dict containing detailed analytics
    """
    try:
        if not supabase:
            raise AIToolsError("Database connection not available")
        
        # Date range for analysis
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get all tasks in the date range
        tasks_result = supabase.table("tasks").select("*").eq("user_id", user_id)\
            .gte("created_at", start_date.isoformat()).execute()
        
        tasks = tasks_result.data
        
        # Calculate analytics
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.get("status") == "completed"])
        pending_tasks = len([t for t in tasks if t.get("status") == "pending"])
        in_progress_tasks = len([t for t in tasks if t.get("status") == "in_progress"])
        
        # Priority distribution
        priority_dist = {}
        for task in tasks:
            priority = task.get("priority", "medium")
            priority_dist[priority] = priority_dist.get(priority, 0) + 1
        
        # Category distribution
        category_dist = {}
        for task in tasks:
            category = task.get("category", "general")
            category_dist[category] = category_dist.get(category, 0) + 1
        
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        analytics = {
            "period": f"{days} days",
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "in_progress_tasks": in_progress_tasks,
            "completion_rate": round(completion_rate, 2),
            "priority_distribution": priority_dist,
            "category_distribution": category_dist,
            "generated_at": datetime.now().isoformat()
        }
        
        logger.info(f"Generated analytics for {days} days: {total_tasks} tasks, {completion_rate:.1f}% completion rate")
        return {"success": True, "data": analytics}
        
    except Exception as e:
        logger.error(f"Error generating analytics: {str(e)}")
        return {"success": False, "error": str(e)}

# ==================== V4.0 JOURNAL MANAGEMENT ====================

@tool(name="create_journal_entry", description="Create a new journal entry with mood tracking", category="journal", auto_inject=["supabase", "user_id"])
def create_journal_entry(title: str, content: str, mood_score: float = None, 
                        emotional_tone: str = "neutral", themes: str = None,
                        entry_type: str = "free_form", supabase=None, user_id: str = None) -> Dict[str, Any]:
    """
    Create a new journal entry with v4.0 enhanced features
    
    Args:
        title: Journal entry title
        content: Journal entry content
        mood_score: Mood score from 1.0 to 10.0
        emotional_tone: Emotional tone (very_positive, positive, neutral, negative, very_negative, mixed)
        themes: Comma-separated themes (will be converted to list)
        entry_type: Entry type (free_form, structured, prompted)
        supabase: Auto-injected Supabase client
        user_id: Auto-injected user identifier
    
    Returns:
        Dict containing the created journal entry
    """
    try:
        if not supabase:
            raise AIToolsError("Database connection not available")
        
        # Import database functions
        from database_personal import add_journal_entry
        
        # Convert themes string to list
        themes_list = [theme.strip() for theme in themes.split(",")] if themes else None
        
        result = add_journal_entry(
            supabase=supabase,
            user_id=user_id,
            title=title,
            content=content,
            mood_score=mood_score,
            emotional_tone=emotional_tone,
            themes=themes_list,
            entry_type=entry_type
        )
        
        logger.info(f"Journal entry created: {title}")
        return {"success": True, "data": result}
        
    except Exception as e:
        logger.error(f"Error creating journal entry: {str(e)}")
        return {"success": False, "error": str(e)}

@tool(name="get_journal_entries", description="Retrieve journal entries with filtering", category="journal", auto_inject=["supabase", "user_id"])
def get_journal_entries(title_like: str = None, content_like: str = None,
                       emotional_tone: str = None, mood_min: float = None, 
                       mood_max: float = None, date_from: str = None, 
                       date_to: str = None, limit: int = 20,
                       supabase=None, user_id: str = None) -> Dict[str, Any]:
    """
    Retrieve journal entries with comprehensive filtering
    
    Args:
        title_like: Filter by title containing this text
        content_like: Filter by content containing this text
        emotional_tone: Filter by emotional tone
        mood_min: Minimum mood score filter
        mood_max: Maximum mood score filter
        date_from: Filter entries from this date (ISO format)
        date_to: Filter entries to this date (ISO format)
        limit: Maximum number of entries to return
        supabase: Auto-injected Supabase client
        user_id: Auto-injected user identifier
    
    Returns:
        Dict containing the filtered journal entries
    """
    try:
        if not supabase:
            raise AIToolsError("Database connection not available")
        
        from database_personal import query_journal_entries
        
        filters = {}
        if title_like: filters['title_like'] = title_like
        if content_like: filters['content_like'] = content_like
        if emotional_tone: filters['emotional_tone'] = emotional_tone
        if mood_min: filters['mood_min'] = mood_min
        if mood_max: filters['mood_max'] = mood_max
        if date_from: filters['date_from'] = date_from
        if date_to: filters['date_to'] = date_to
        if limit: filters['limit'] = limit
        
        result = query_journal_entries(
            supabase=supabase,
            user_id=user_id,
            **filters
        )
        
        logger.info(f"Retrieved {len(result)} journal entries")
        return {"success": True, "data": result, "count": len(result)}
        
    except Exception as e:
        logger.error(f"Error retrieving journal entries: {str(e)}")
        return {"success": False, "error": str(e)}

@tool(name="analyze_mood_patterns", description="Analyze mood patterns from journal entries", category="journal", auto_inject=["supabase", "user_id"])
def analyze_mood_patterns(days: int = 30, supabase=None, user_id: str = None) -> Dict[str, Any]:
    """
    Analyze mood patterns from journal entries over a specified period
    
    Args:
        days: Number of days to analyze (default: 30)
        supabase: Auto-injected Supabase client
        user_id: Auto-injected user identifier
    
    Returns:
        Dict containing mood pattern analysis
    """
    try:
        if not supabase:
            raise AIToolsError("Database connection not available")
        
        from database_personal import analyze_mood_patterns
        
        result = analyze_mood_patterns(
            supabase=supabase,
            user_id=user_id,
            days=days
        )
        
        logger.info(f"Analyzed mood patterns for {days} days")
        return {"success": True, "data": result}
        
    except Exception as e:
        logger.error(f"Error analyzing mood patterns: {str(e)}")
        return {"success": False, "error": str(e)}

# ==================== V4.0 MEMORY MANAGEMENT ====================

@tool(name="create_memory", description="Create a new memory entry", category="memory", auto_inject=["supabase", "user_id"])
def create_memory(title: str, content: str, memory_type: str = "general",
                 importance_score: float = 0.5, emotional_tone: str = "neutral",
                 tags: str = None, relationships: str = None, locations: str = None,
                 supabase=None, user_id: str = None) -> Dict[str, Any]:
    """
    Create a new memory entry with v4.0 enhanced features
    
    Args:
        title: Memory title
        content: Memory content
        memory_type: Type of memory (milestone, achievement, relationship, experience, learning, general)
        importance_score: Importance score from 0.0 to 1.0
        emotional_tone: Emotional tone (positive, negative, neutral, mixed)
        tags: Comma-separated tags (will be converted to list)
        relationships: Comma-separated people involved (will be converted to list)
        locations: Comma-separated locations (will be converted to list)
        supabase: Auto-injected Supabase client
        user_id: Auto-injected user identifier
    
    Returns:
        Dict containing the created memory
    """
    try:
        if not supabase:
            raise AIToolsError("Database connection not available")
        
        from database_personal import add_memory_entry
        
        # Convert comma-separated strings to lists
        tags_list = [tag.strip() for tag in tags.split(",")] if tags else None
        relationships_list = [rel.strip() for rel in relationships.split(",")] if relationships else None
        locations_list = [loc.strip() for loc in locations.split(",")] if locations else None
        
        result = add_memory_entry(
            supabase=supabase,
            user_id=user_id,
            title=title,
            content=content,
            memory_type=memory_type,
            importance_score=importance_score,
            emotional_tone=emotional_tone,
            tags=tags_list,
            relationships=relationships_list,
            locations=locations_list
        )
        
        logger.info(f"Memory created: {title}")
        return {"success": True, "data": result}
        
    except Exception as e:
        logger.error(f"Error creating memory: {str(e)}")
        return {"success": False, "error": str(e)}

@tool(name="search_memories", description="Search memories with intelligent filtering", category="memory", auto_inject=["supabase", "user_id"])
def search_memories(query: str, limit: int = 10, supabase=None, user_id: str = None) -> Dict[str, Any]:
    """
    Search memories using text matching with importance-based ranking
    
    Args:
        query: Search query text
        limit: Maximum number of memories to return
        supabase: Auto-injected Supabase client
        user_id: Auto-injected user identifier
    
    Returns:
        Dict containing the matching memories
    """
    try:
        if not supabase:
            raise AIToolsError("Database connection not available")
        
        from database_personal import search_memories
        
        result = search_memories(
            supabase=supabase,
            user_id=user_id,
            query=query,
            limit=limit
        )
        
        logger.info(f"Found {len(result)} memories for query: {query}")
        return {"success": True, "data": result, "count": len(result)}
        
    except Exception as e:
        logger.error(f"Error searching memories: {str(e)}")
        return {"success": False, "error": str(e)}

@tool(name="get_memory_timeline", description="Get memories organized chronologically", category="memory", auto_inject=["supabase", "user_id"])
def get_memory_timeline(memory_type: str = None, importance_min: float = None,
                       emotional_tone: str = None, date_from: str = None,
                       date_to: str = None, limit: int = 50,
                       supabase=None, user_id: str = None) -> Dict[str, Any]:
    """
    Get memories organized in chronological timeline format
    
    Args:
        memory_type: Filter by memory type
        importance_min: Minimum importance score filter
        emotional_tone: Filter by emotional tone
        date_from: Filter memories from this date
        date_to: Filter memories to this date
        limit: Maximum number of memories to return
        supabase: Auto-injected Supabase client
        user_id: Auto-injected user identifier
    
    Returns:
        Dict containing the chronologically ordered memories
    """
    try:
        if not supabase:
            raise AIToolsError("Database connection not available")
        
        from database_personal import get_memory_timeline
        
        filters = {}
        if memory_type: filters['memory_type'] = memory_type
        if importance_min: filters['importance_min'] = importance_min
        if emotional_tone: filters['emotional_tone'] = emotional_tone
        if date_from: filters['date_from'] = date_from
        if date_to: filters['date_to'] = date_to
        if limit: filters['limit'] = limit
        
        result = get_memory_timeline(
            supabase=supabase,
            user_id=user_id,
            **filters
        )
        
        logger.info(f"Retrieved {len(result)} memories in timeline format")
        return {"success": True, "data": result, "count": len(result)}
        
    except Exception as e:
        logger.error(f"Error getting memory timeline: {str(e)}")
        return {"success": False, "error": str(e)}

@tool(name="analyze_memory_relationships", description="Analyze relationships mentioned in memories", category="memory", auto_inject=["supabase", "user_id"])
def analyze_memory_relationships(supabase=None, user_id: str = None) -> Dict[str, Any]:
    """
    Analyze relationships and people mentioned across memories
    
    Args:
        supabase: Auto-injected Supabase client
        user_id: Auto-injected user identifier
    
    Returns:
        Dict containing relationship analysis data
    """
    try:
        if not supabase:
            raise AIToolsError("Database connection not available")
        
        from database_personal import analyze_memory_relationships
        
        result = analyze_memory_relationships(
            supabase=supabase,
            user_id=user_id
        )
        
        logger.info("Completed memory relationship analysis")
        return {"success": True, "data": result}
        
    except Exception as e:
        logger.error(f"Error analyzing memory relationships: {str(e)}")
        return {"success": False, "error": str(e)}

# ==================== V4.0 CONTENT CLASSIFICATION ====================

@tool(name="classify_content", description="Classify content using AI analysis", category="classification", auto_inject=["supabase", "user_id"])
def classify_content(content_text: str, detected_language: str = "en", 
                   original_text: str = None, supabase=None, user_id: str = None) -> Dict[str, Any]:
    """
    Classify content automatically using AI-powered analysis
    
    Args:
        content_text: The text content to classify
        detected_language: The detected language of the content
        original_text: Original text before translation (if applicable)
        supabase: Auto-injected Supabase client
        user_id: Auto-injected user identifier
    
    Returns:
        Dict containing the classification results
    """
    try:
        if not supabase:
            raise AIToolsError("Database connection not available")
        
        from database_personal import classify_and_store_content
        
        result = classify_and_store_content(
            supabase=supabase,
            user_id=user_id,
            content_text=content_text,
            detected_language=detected_language,
            original_text=original_text
        )
        
        logger.info(f"Content classified as: {result.get('primary_category')}")
        return {"success": True, "data": result}
        
    except Exception as e:
        logger.error(f"Error classifying content: {str(e)}")
        return {"success": False, "error": str(e)}

@tool(name="get_classification_history", description="Get content classification history", category="classification", auto_inject=["supabase", "user_id"])
def get_classification_history(primary_category: str = None, emotional_tone: str = None,
                             date_from: str = None, date_to: str = None, 
                             limit: int = 50, supabase=None, user_id: str = None) -> Dict[str, Any]:
    """
    Get historical content classification results with filtering
    
    Args:
        primary_category: Filter by primary category (JOURNAL_ENTRY, MEMORY, TEMPORARY_INFO, KNOWLEDGE)
        emotional_tone: Filter by emotional tone
        date_from: Filter classifications from this date
        date_to: Filter classifications to this date
        limit: Maximum number of classifications to return
        supabase: Auto-injected Supabase client
        user_id: Auto-injected user identifier
    
    Returns:
        Dict containing the classification history
    """
    try:
        if not supabase:
            raise AIToolsError("Database connection not available")
        
        from database_personal import get_classification_history
        
        filters = {}
        if primary_category: filters['primary_category'] = primary_category
        if emotional_tone: filters['emotional_tone'] = emotional_tone
        if date_from: filters['date_from'] = date_from
        if date_to: filters['date_to'] = date_to
        if limit: filters['limit'] = limit
        
        result = get_classification_history(
            supabase=supabase,
            user_id=user_id,
            **filters
        )
        
        logger.info(f"Retrieved {len(result)} classification records")
        return {"success": True, "data": result, "count": len(result)}
        
    except Exception as e:
        logger.error(f"Error retrieving classification history: {str(e)}")
        return {"success": False, "error": str(e)}



# ==================== UTILITY FUNCTIONS ====================

def _auto_categorize_task(title: str, description: str) -> str:
    """
    Automatically categorize a task based on keywords in title and description
    """
    content = (title + " " + description).lower()
    
    # Define category keywords
    categories = {
        "work": ["meeting", "project", "deadline", "report", "presentation", "client", "team", "office"],
        "personal": ["shopping", "grocery", "family", "friend", "birthday", "anniversary", "vacation"],
        "health": ["doctor", "appointment", "exercise", "gym", "medication", "checkup", "health"],
        "finance": ["bank", "payment", "bill", "tax", "budget", "money", "invoice", "insurance"],
        "home": ["clean", "repair", "maintenance", "garden", "organize", "decorate"],
        "learning": ["study", "course", "book", "tutorial", "lesson", "practice", "exam"]
    }
    
    for category, keywords in categories.items():
        if any(keyword in content for keyword in keywords):
            return category
    
    return "general"

@tool(name="validate_cron_expression", description="Validate a cron expression", category="utilities")
def validate_cron_expression(cron_expr: str) -> Dict[str, Any]:
    """
    Validate a cron expression and provide next execution times
    
    Args:
        cron_expr: Cron expression to validate (e.g., "0 9 * * MON-FRI")
    
    Returns:
        Dict containing validation result and next execution times
    """
    try:
        cron = croniter(cron_expr, datetime.now())
        
        # Get next 5 execution times
        next_times = []
        for i in range(5):
            next_times.append(cron.get_next(datetime).isoformat())
        
        return {
            "success": True, 
            "valid": True,
            "next_executions": next_times,
            "message": "Cron expression is valid"
        }
        
    except Exception as e:
        return {
            "success": True,
            "valid": False,
            "error": str(e),
            "message": "Invalid cron expression"
        }

# ==================== TOOL REGISTRY SETUP ====================

def initialize_ai_tools():
    """
    Initialize the AI tools system with dependency injection context
    """
    logger.info("AI Tools system initialized with enhanced features")
    logger.info(f"Total registered tools: {len(tool_registry.tools)}")
    
    # Log categories
    categories = {}
    for name, metadata in tool_registry.tool_metadata.items():
        cat = metadata['category']
        categories[cat] = categories.get(cat, 0) + 1
    
    logger.info(f"Tool categories: {categories}")
    
def set_context(supabase_client, user_id: str):
    """
    Set the dependency injection context for auto-parameter injection
    
    Args:
        supabase_client: Supabase client instance
        user_id: Current user identifier
    """
    tool_registry.set_injection_context({
        "supabase": supabase_client,
        "user_id": user_id
    })
    logger.info(f"Context set for user: {user_id}")

# Initialize the system when module is imported
if __name__ != "__main__":
    initialize_ai_tools()
