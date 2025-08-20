# tool_collections/memory_tools.py
# Collection of memory-related tools

from ..tools import register_tool

@register_tool(
    name="get_user_memory",
    category="memory",
    description="Get a memory from the user's memory store"
)
def get_user_memory(supabase, user_id, key=None):
    """Get a memory from the user's memory store.
    
    Args:
        supabase: The Supabase client
        user_id: The ID of the user
        key: Optional specific memory key to retrieve
        
    Returns:
        The memory value or all memories if no key is provided
    """
    try:
        # Query the memories table
        query = supabase.table("memories").select("*").eq("user_id", user_id)
        
        if key:
            # Filter by key if provided
            query = query.eq("key", key)
        
        result = query.execute()
        
        if not result.data:
            return None if key else {}
        
        if key:
            # Return the single memory value
            return result.data[0].get("value")
        else:
            # Return all memories as a dictionary
            return {item.get("key"): item.get("value") for item in result.data}
    except Exception as e:
        print(f"ERROR in get_user_memory: {str(e)}")
        return None if key else {}

@register_tool(
    name="set_user_memory",
    category="memory",
    description="Set a memory in the user's memory store"
)
def set_user_memory(supabase, user_id, key, value):
    """Set a memory in the user's memory store.
    
    Args:
        supabase: The Supabase client
        user_id: The ID of the user
        key: The memory key
        value: The memory value
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if the memory already exists
        existing = supabase.table("memories").select("*").eq("user_id", user_id).eq("key", key).execute()
        
        if existing.data:
            # Update existing memory
            supabase.table("memories").update({"value": value, "updated_at": "now()"}).eq("id", existing.data[0].get("id")).execute()
        else:
            # Insert new memory
            supabase.table("memories").insert({
                "user_id": user_id,
                "key": key,
                "value": value
            }).execute()
        
        return True
    except Exception as e:
        print(f"ERROR in set_user_memory: {str(e)}")
        return False

@register_tool(
    name="delete_user_memory",
    category="memory",
    description="Delete a memory from the user's memory store"
)
def delete_user_memory(supabase, user_id, key):
    """Delete a memory from the user's memory store.
    
    Args:
        supabase: The Supabase client
        user_id: The ID of the user
        key: The memory key
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Delete the memory
        supabase.table("memories").delete().eq("user_id", user_id).eq("key", key).execute()
        return True
    except Exception as e:
        print(f"ERROR in delete_user_memory: {str(e)}")
        return False
