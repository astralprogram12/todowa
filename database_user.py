# database_user.py
from supabase import Client
from datetime import date

def get_or_create_user(supabase: Client, phone_number: str):
    """
    Finds a user by phone number from the 'user_whatsapp' table.
    If they don't exist, this function WILL NOT create them.
    Creation is handled during the invitation/signup flow.
    Returns the full user record dict or None if not found.
    """
    print(f"DB: Looking up user with phone: {phone_number}")
    response = supabase.table('user_whatsapp').select('*').eq('phone_number', phone_number).limit(1).execute()
    if response.data:
        return response.data[0]
    return None

def check_and_update_usage(supabase: Client, user_id: str):
    """
    Checks if the user is within their daily message limits.
    If it's a new day, it resets their count.
    Returns (is_allowed: bool, message: str).
    """
    print(f"DB: Checking usage for user_id: {user_id}")
    today = date.today().isoformat()
    
    # In a real implementation, you would use an RPC function for this
    # to make it an atomic transaction (prevent race conditions).
    # For now, this logic demonstrates the principle.
    
    user_settings = supabase.table('user_whatsapp').select('daily_message_count, last_message_date').eq('user_id', user_id).limit(1).execute().data[0]

    if str(user_settings['last_message_date']) != today:
        # It's a new day, reset the count and update the date
        supabase.table('user_whatsapp').update({
            'daily_message_count': 1,
            'last_message_date': today
        }).eq('user_id', user_id).execute()
        return True, ""
    
    # It's the same day, check the limit
    # This limit should eventually come from the user's plan/settings
    daily_limit = 100 
    if user_settings['daily_message_count'] >= daily_limit:
        return False, "You have reached your daily message limit."
    
    # Increment the count
    supabase.table('user_whatsapp').update({
        'daily_message_count': user_settings['daily_message_count'] + 1
    }).eq('user_id', user_id).execute()
    
    return True, ""