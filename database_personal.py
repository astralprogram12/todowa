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
        res = supabase.table('memories').select('title, content, memory_type, created_at').eq('user_id', user_id).order('created_at', desc=True).limit(25).execute()
        return {"memories": res.data or []}
    except Exception as e:
        print(f"!!! DATABASE ERROR in get_memory_context_for_ai: {e}")
        return {"memories": []}

def get_journal_context_for_ai(supabase: Client, user_id: str) -> dict:
    """Fetches recent journal entries for context."""
    try:
        res = supabase.table('journal_entries').select('title, content, emotional_tone, created_at').eq('user_id', user_id).order('created_at', desc=True).limit(10).execute()
        return {"journal_entries": res.data or []}
    except Exception as e:
        print(f"!!! DATABASE ERROR in get_journal_context_for_ai: {e}")
        return {"journal_entries": []}

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
# Note: Enhanced v4.0 functions are defined below - these are legacy placeholders

# --- V4.0 Journal Functions ---

def add_journal_entry(supabase: Client, user_id: str, title: str, content: str, 
                     mood_score: float = None, emotional_tone: str = 'neutral',
                     themes: list = None, entry_type: str = 'free_form') -> dict:
    """Add a new journal entry with v4.0 enhanced features"""
    if not title or len(title.strip()) == 0: 
        raise ValueError("Journal title cannot be empty.")
    if not content or len(content.strip()) == 0:
        raise ValueError("Journal content cannot be empty.")
    
    # Apply typo correction
    title = apply_typo_correction(title.strip())
    content = apply_typo_correction(content.strip())
    
    # Calculate word count and reading time
    word_count = len(content.split())
    reading_time_minutes = max(1, word_count // 200)  # Assume 200 words per minute
    
    entry_data = {
        "user_id": user_id,
        "title": title,
        "content": content,
        "mood_score": mood_score,
        "emotional_tone": emotional_tone,
        "themes": themes or [],
        "word_count": word_count,
        "reading_time_minutes": reading_time_minutes,
        "entry_type": entry_type
    }
    
    try:
        res = supabase.table("journal_entries").insert(entry_data).execute()
        if getattr(res, "error", None): 
            raise Exception(str(res.error))
        return (res.data or [None])[0]
    except Exception as e:
        print(f"Journal entry creation error: {e}")
        raise e

def query_journal_entries(supabase: Client, user_id: str, **filters) -> list:
    """Query journal entries with advanced filtering"""
    try:
        q = supabase.table("journal_entries").select("*").eq("user_id", user_id)
        
        if filters.get('title_like'): 
            q = q.ilike('title', f"%{filters['title_like']}%")
        if filters.get('content_like'): 
            q = q.ilike('content', f"%{filters['content_like']}%")
        if filters.get('emotional_tone'): 
            q = q.eq('emotional_tone', filters['emotional_tone'])
        if filters.get('mood_min'): 
            q = q.gte('mood_score', filters['mood_min'])
        if filters.get('mood_max'): 
            q = q.lte('mood_score', filters['mood_max'])
        if filters.get('date_from'): 
            q = q.gte('created_at', filters['date_from'])
        if filters.get('date_to'): 
            q = q.lte('created_at', filters['date_to'])
        if filters.get('limit'): 
            q = q.limit(filters['limit'])
            
        q = q.order('created_at', desc=True)
        res = q.execute()
        
        if getattr(res, "error", None): 
            raise Exception(str(res.error))
        return res.data or []
    except Exception as e:
        print(f"Journal query error: {e}")
        return []

def update_journal_entry(supabase: Client, user_id: str, entry_id: str, patch: dict) -> dict:
    """Update a journal entry"""
    try:
        # Apply typo correction to title and content if being updated
        if 'title' in patch and patch['title']:
            patch['title'] = apply_typo_correction(patch['title'])
        if 'content' in patch and patch['content']:
            patch['content'] = apply_typo_correction(patch['content'])
            # Recalculate word count and reading time
            word_count = len(patch['content'].split())
            patch['word_count'] = word_count
            patch['reading_time_minutes'] = max(1, word_count // 200)
        
        res = supabase.table("journal_entries").update(patch).eq("id", entry_id).eq("user_id", user_id).execute()
        if getattr(res, "error", None): 
            raise Exception(str(res.error))
        return (res.data or [None])[0]
    except Exception as e:
        print(f"Journal update error: {e}")
        raise e

def delete_journal_entry(supabase: Client, user_id: str, entry_id: str):
    """Delete a journal entry"""
    try:
        supabase.table('journal_entries').delete().eq('id', entry_id).eq('user_id', user_id).execute()
    except Exception as e:
        print(f"Journal delete error: {e}")
        raise e

def analyze_mood_patterns(supabase: Client, user_id: str, days: int = 30) -> dict:
    """Analyze mood patterns from journal entries"""
    try:
        from datetime import datetime, timedelta
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        res = supabase.table("journal_entries").select(
            "mood_score, emotional_tone, created_at"
        ).eq("user_id", user_id).gte(
            "created_at", start_date
        ).not_.is_("mood_score", "null").execute()
        
        entries = res.data or []
        if not entries:
            return {"message": "No mood data found for the specified period"}
        
        # Calculate statistics
        mood_scores = [float(entry['mood_score']) for entry in entries]
        avg_mood = sum(mood_scores) / len(mood_scores)
        
        # Count emotional tones
        tone_counts = {}
        for entry in entries:
            tone = entry.get('emotional_tone', 'neutral')
            tone_counts[tone] = tone_counts.get(tone, 0) + 1
        
        return {
            "period_days": days,
            "entry_count": len(entries),
            "average_mood": round(avg_mood, 2),
            "mood_range": {
                "min": min(mood_scores),
                "max": max(mood_scores)
            },
            "emotional_tone_distribution": tone_counts,
            "dominant_tone": max(tone_counts.items(), key=lambda x: x[1])[0] if tone_counts else 'neutral'
        }
    except Exception as e:
        print(f"Mood analysis error: {e}")
        return {"error": str(e)}

# --- V4.0 Memory Functions ---

def add_memory_entry(supabase: Client, user_id: str, title: str, content: str,
                    memory_type: str = 'general', importance_score: float = 0.5,
                    emotional_tone: str = 'neutral', tags: list = None,
                    relationships: list = None, locations: list = None) -> dict:
    """Add a new memory with v4.0 enhanced features"""
    if not title or len(title.strip()) == 0: 
        raise ValueError("Memory title cannot be empty.")
    if not content or len(content.strip()) == 0:
        raise ValueError("Memory content cannot be empty.")
    
    # Apply typo correction
    title = apply_typo_correction(title.strip())
    content = apply_typo_correction(content.strip())
    
    memory_data = {
        "user_id": user_id,
        "title": title,
        "content": content,
        "memory_type": memory_type,
        "importance_score": max(0.0, min(1.0, importance_score)),  # Ensure 0-1 range
        "emotional_tone": emotional_tone,
        "tags": tags or [],
        "relationships": relationships or [],
        "locations": locations or []
    }
    
    try:
        res = supabase.table("memories").insert(memory_data).execute()
        if getattr(res, "error", None): 
            raise Exception(str(res.error))
        return (res.data or [None])[0]
    except Exception as e:
        print(f"Memory creation error: {e}")
        raise e

def search_memories(supabase: Client, user_id: str, query: str, limit: int = 10) -> list:
    """Search memories with enhanced filtering"""
    try:
        sanitized_query = query.replace("'", "''")
        res = supabase.table("memories").select(
            "id, title, content, memory_type, importance_score, emotional_tone, tags, created_at"
        ).eq("user_id", user_id).or_(
            f"title.ilike.%{sanitized_query}%,content.ilike.%{sanitized_query}%"
        ).order("importance_score", desc=True).order(
            "created_at", desc=True
        ).limit(limit).execute()
        
        # Update search frequency for found memories
        if res.data:
            memory_ids = [memory['id'] for memory in res.data]
            supabase.table("memories").update({
                "search_frequency": supabase.table("memories").select("search_frequency").eq("id", memory_ids[0]).execute().data[0]['search_frequency'] + 1,
                "last_accessed": datetime.now().isoformat()
            }).in_("id", memory_ids).execute()
        
        return res.data or []
    except Exception as e:
        print(f"Memory search error: {e}")
        return []

def get_memory_timeline(supabase: Client, user_id: str, **filters) -> list:
    """Get memories organized by timeline"""
    try:
        q = supabase.table("memories").select(
            "id, title, content, memory_type, importance_score, emotional_tone, tags, relationships, locations, created_at"
        ).eq("user_id", user_id)
        
        if filters.get('memory_type'): 
            q = q.eq('memory_type', filters['memory_type'])
        if filters.get('importance_min'): 
            q = q.gte('importance_score', filters['importance_min'])
        if filters.get('date_from'): 
            q = q.gte('created_at', filters['date_from'])
        if filters.get('date_to'): 
            q = q.lte('created_at', filters['date_to'])
        if filters.get('emotional_tone'): 
            q = q.eq('emotional_tone', filters['emotional_tone'])
        
        q = q.order('created_at', desc=False)  # Chronological order for timeline
        if filters.get('limit'): 
            q = q.limit(filters['limit'])
            
        res = q.execute()
        return res.data or []
    except Exception as e:
        print(f"Memory timeline error: {e}")
        return []

def update_memory_entry(supabase: Client, user_id: str, memory_id: str, patch: dict) -> dict:
    """Update a memory entry"""
    try:
        # Apply typo correction to title and content if being updated
        if 'title' in patch and patch['title']:
            patch['title'] = apply_typo_correction(patch['title'])
        if 'content' in patch and patch['content']:
            patch['content'] = apply_typo_correction(patch['content'])
        
        res = supabase.table("memories").update(patch).eq("id", memory_id).eq("user_id", user_id).execute()
        if getattr(res, "error", None): 
            raise Exception(str(res.error))
        return (res.data or [None])[0]
    except Exception as e:
        print(f"Memory update error: {e}")
        raise e

def delete_memory_entry(supabase: Client, user_id: str, memory_id: str):
    """Delete a memory entry"""
    try:
        supabase.table('memories').delete().eq('id', memory_id).eq('user_id', user_id).execute()
    except Exception as e:
        print(f"Memory delete error: {e}")
        raise e

def analyze_memory_relationships(supabase: Client, user_id: str) -> dict:
    """Analyze relationships mentioned in memories"""
    try:
        res = supabase.table("memories").select(
            "relationships, emotional_tone, memory_type, importance_score"
        ).eq("user_id", user_id).not_.is_("relationships", "null").execute()
        
        memories = res.data or []
        if not memories:
            return {"message": "No relationship data found in memories"}
        
        # Analyze relationships
        relationship_stats = {}
        for memory in memories:
            relationships = memory.get('relationships', [])
            for rel in relationships:
                if rel not in relationship_stats:
                    relationship_stats[rel] = {
                        'mentions': 0,
                        'emotional_tones': [],
                        'memory_types': [],
                        'avg_importance': 0
                    }
                
                relationship_stats[rel]['mentions'] += 1
                relationship_stats[rel]['emotional_tones'].append(memory.get('emotional_tone', 'neutral'))
                relationship_stats[rel]['memory_types'].append(memory.get('memory_type', 'general'))
                relationship_stats[rel]['avg_importance'] += float(memory.get('importance_score', 0.5))
        
        # Calculate averages and dominant patterns
        for rel, stats in relationship_stats.items():
            stats['avg_importance'] = round(stats['avg_importance'] / stats['mentions'], 2)
            # Find dominant emotional tone
            tone_counts = {}
            for tone in stats['emotional_tones']:
                tone_counts[tone] = tone_counts.get(tone, 0) + 1
            stats['dominant_emotional_tone'] = max(tone_counts.items(), key=lambda x: x[1])[0]
            
            # Clean up raw lists
            del stats['emotional_tones']
            del stats['memory_types']
        
        return {
            "total_relationships": len(relationship_stats),
            "relationship_analysis": relationship_stats
        }
    except Exception as e:
        print(f"Relationship analysis error: {e}")
        return {"error": str(e)}

# --- V4.0 Content Classification Functions ---

def classify_and_store_content(supabase: Client, user_id: str, content_text: str,
                              detected_language: str = 'en', original_text: str = None) -> dict:
    """Classify content using AI and store results"""
    try:
        # Simple rule-based classification for now (can be enhanced with AI later)
        classification_result = _classify_content_simple(content_text)
        
        classification_data = {
            "user_id": user_id,
            "content_text": content_text,
            "original_text": original_text,
            "detected_language": detected_language,
            "primary_category": classification_result['primary_category'],
            "confidence_journal": classification_result['confidence_journal'],
            "confidence_memory": classification_result['confidence_memory'],
            "confidence_temporary": classification_result['confidence_temporary'],
            "confidence_knowledge": classification_result['confidence_knowledge'],
            "emotional_tone": classification_result['emotional_tone'],
            "importance_score": classification_result['importance_score'],
            "suggested_tags": classification_result['suggested_tags'],
            "classification_reasoning": classification_result['reasoning']
        }
        
        res = supabase.table("content_classifications").insert(classification_data).execute()
        if getattr(res, "error", None): 
            raise Exception(str(res.error))
        return (res.data or [None])[0]
    except Exception as e:
        print(f"Content classification error: {e}")
        raise e

def get_classification_history(supabase: Client, user_id: str, **filters) -> list:
    """Get classification history with filtering"""
    try:
        q = supabase.table("content_classifications").select("*").eq("user_id", user_id)
        
        if filters.get('primary_category'): 
            q = q.eq('primary_category', filters['primary_category'])
        if filters.get('emotional_tone'): 
            q = q.eq('emotional_tone', filters['emotional_tone'])
        if filters.get('date_from'): 
            q = q.gte('processing_timestamp', filters['date_from'])
        if filters.get('date_to'): 
            q = q.lte('processing_timestamp', filters['date_to'])
        if filters.get('limit'): 
            q = q.limit(filters['limit'])
            
        q = q.order('processing_timestamp', desc=True)
        res = q.execute()
        return res.data or []
    except Exception as e:
        print(f"Classification history error: {e}")
        return []

def _classify_content_simple(content_text: str) -> dict:
    """Simple rule-based content classification (placeholder for AI classification)"""
    content_lower = content_text.lower()
    
    # Keywords for different categories
    journal_keywords = ['today', 'feel', 'felt', 'mood', 'emotion', 'diary', 'personal', 'reflection']
    memory_keywords = ['remember', 'recall', 'memory', 'happened', 'experience', 'milestone', 'achievement']
    knowledge_keywords = ['learn', 'learned', 'fact', 'information', 'knowledge', 'understand', 'concept']
    
    # Count matches
    journal_score = sum(1 for word in journal_keywords if word in content_lower)
    memory_score = sum(1 for word in memory_keywords if word in content_lower)
    knowledge_score = sum(1 for word in knowledge_keywords if word in content_lower)
    
    # Determine primary category
    scores = {
        'JOURNAL_ENTRY': journal_score,
        'MEMORY': memory_score,
        'KNOWLEDGE': knowledge_score,
        'TEMPORARY_INFO': 1  # Default fallback
    }
    
    primary_category = max(scores.items(), key=lambda x: x[1])[0]
    
    # Simple emotional tone detection
    positive_words = ['happy', 'joy', 'good', 'great', 'amazing', 'wonderful', 'love']
    negative_words = ['sad', 'angry', 'bad', 'terrible', 'hate', 'awful', 'difficult']
    
    positive_count = sum(1 for word in positive_words if word in content_lower)
    negative_count = sum(1 for word in negative_words if word in content_lower)
    
    if positive_count > negative_count:
        emotional_tone = 'positive'
    elif negative_count > positive_count:
        emotional_tone = 'negative'
    else:
        emotional_tone = 'neutral'
    
    return {
        'primary_category': primary_category,
        'confidence_journal': min(1.0, journal_score * 0.2),
        'confidence_memory': min(1.0, memory_score * 0.2),
        'confidence_temporary': 0.3,  # Default
        'confidence_knowledge': min(1.0, knowledge_score * 0.2),
        'emotional_tone': emotional_tone,
        'importance_score': 0.5,  # Default
        'suggested_tags': [],
        'reasoning': f'Classified as {primary_category} based on keyword analysis'
    }

# --- Backward Compatibility Functions ---

def search_memory_entries(supabase: Client, user_id: str, query: str, limit: int = 5):
    """Legacy function - redirects to new v4.0 search_memories"""
    return search_memories(supabase, user_id, query, limit)

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