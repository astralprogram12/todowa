# tool_collections/time_tools.py
# Collection of time-related tools

import pytz
from datetime import datetime, timedelta
from ..tools import register_tool

@register_tool(
    name="get_current_time",
    category="time",
    description="Get the current time in UTC"
)
def get_current_time():
    """Get the current time in UTC.
    
    Returns:
        The current time in ISO 8601 format
    """
    return datetime.now(pytz.UTC).isoformat()

@register_tool(
    name="convert_time_to_utc",
    category="time",
    description="Convert a time string to UTC"
)
def convert_time_to_utc(time_str, source_timezone=None):
    """Convert a time string to UTC.
    
    Args:
        time_str: The time string to convert
        source_timezone: The source timezone (e.g., 'America/New_York')
        
    Returns:
        The time in UTC ISO 8601 format
    """
    # This is a simplified implementation
    # A real implementation would handle various time formats and relative times
    try:
        # If the time string is already in ISO 8601 format with timezone
        try:
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            return dt.astimezone(pytz.UTC).isoformat()
        except:
            pass
        
        # If source timezone is provided, use it
        if source_timezone:
            # Assume time_str is in a simple format like 'YYYY-MM-DD HH:MM:SS'
            dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            dt = pytz.timezone(source_timezone).localize(dt)
            return dt.astimezone(pytz.UTC).isoformat()
        
        # If no timezone info, assume UTC
        return time_str
    except Exception as e:
        return f"Error converting time: {str(e)}"

@register_tool(
    name="convert_utc_to_user_timezone",
    category="time",
    description="Convert a UTC time string to the user's timezone"
)
def convert_utc_to_user_timezone(supabase, user_id, utc_time_str):
    """Convert a UTC time string to the user's timezone.
    
    Args:
        supabase: The Supabase client
        user_id: The ID of the user
        utc_time_str: The UTC time string to convert
        
    Returns:
        The time in the user's timezone
    """
    try:
        # Get the user's timezone preference
        preferences = supabase.table("user_preferences").select("*").eq("user_id", user_id).execute()
        user_timezone = preferences.data[0].get("timezone", "UTC") if preferences.data else "UTC"
        
        # Convert the UTC time to the user's timezone
        utc_time = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
        user_timezone_obj = pytz.timezone(user_timezone)
        local_time = utc_time.astimezone(user_timezone_obj)
        
        # Format the time string
        formatted_time = local_time.strftime('%Y-%m-%d %H:%M:%S %Z')
        
        return formatted_time
    except Exception as e:
        return f"Error converting time: {str(e)}"

@register_tool(
    name="parse_relative_time",
    category="time",
    description="Parse a relative time string and convert to UTC"
)
def parse_relative_time(relative_time, user_id=None, supabase=None):
    """Parse a relative time string and convert to UTC.
    
    Args:
        relative_time: The relative time string (e.g., 'in 2 hours', 'tomorrow at 3pm')
        user_id: Optional user ID to get timezone preferences
        supabase: Optional Supabase client to get user preferences
        
    Returns:
        The time in UTC ISO 8601 format
    """
    # This is a simplified implementation
    # A real implementation would use a proper time parser like dateparser
    try:
        # Get user's timezone if provided
        user_timezone = "UTC"
        if user_id and supabase:
            preferences = supabase.table("user_preferences").select("*").eq("user_id", user_id).execute()
            user_timezone = preferences.data[0].get("timezone", "UTC") if preferences.data else "UTC"
        
        # Handle simple relative times
        now = datetime.now(pytz.timezone(user_timezone))
        
        relative_time_lower = relative_time.lower()
        
        if 'in' in relative_time_lower and 'hour' in relative_time_lower:
            # e.g., 'in 2 hours'
            import re
            hours_match = re.search(r'in (\d+) hours?', relative_time_lower)
            if hours_match:
                hours = int(hours_match.group(1))
                future_time = now + timedelta(hours=hours)
                return future_time.astimezone(pytz.UTC).isoformat()
        
        elif 'in' in relative_time_lower and 'minute' in relative_time_lower:
            # e.g., 'in 30 minutes'
            import re
            minutes_match = re.search(r'in (\d+) minutes?', relative_time_lower)
            if minutes_match:
                minutes = int(minutes_match.group(1))
                future_time = now + timedelta(minutes=minutes)
                return future_time.astimezone(pytz.UTC).isoformat()
        
        elif 'tomorrow' in relative_time_lower:
            # e.g., 'tomorrow at 3pm'
            tomorrow = now + timedelta(days=1)
            if 'at' in relative_time_lower:
                time_part = relative_time_lower.split('at')[1].strip()
                # This is a very simplified time parser
                if 'pm' in time_part:
                    hour = int(time_part.replace('pm', '').strip())
                    hour = hour if hour == 12 else hour + 12
                    tomorrow = tomorrow.replace(hour=hour, minute=0, second=0, microsecond=0)
                elif 'am' in time_part:
                    hour = int(time_part.replace('am', '').strip())
                    hour = 0 if hour == 12 else hour
                    tomorrow = tomorrow.replace(hour=hour, minute=0, second=0, microsecond=0)
            else:
                # Default to 9am tomorrow
                tomorrow = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
            return tomorrow.astimezone(pytz.UTC).isoformat()
        
        # Return the original string if we can't parse it
        return f"Could not parse: {relative_time}"
    except Exception as e:
        return f"Error parsing time: {str(e)}"
