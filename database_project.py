# database_project.py
from supabase import Client

def get_project_context_for_ai(supabase: Client, user_id: str):
    """
    Gathers all necessary context for the PROJECT bot from the new project tables.
    """
    print(f"DB: Getting PROJECT context for {user_id}...")
    
    # This will become a complex function that queries multiple tables:
    # 1. Get user details from 'user_whatsapp'.
    # 2. Find the user's *active* project.
    # 3. Find the user's role and permissions in that project.
    # 4. Get tasks assigned to the user in that project.
    # 5. Get recent project members or activity logs.
    
    return {
        "user_context": {"name": "Budi", "username": "Budi#1234"},
        "active_project": {"name": "Website Redesign", "id": "proj-uuid-abcde"},
        "user_role_in_project": {"name": "Admin", "permissions": ["can_add_task", "can_confirm_tasks"]},
        "project_tasks": [{"title": "Draft homepage mockups", "assignees": ["Andi#5567"]}],
    }