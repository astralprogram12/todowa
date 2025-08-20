from .base_agent import BaseAgent
import database_personal  # Fix #4: Proper database import

class SilentModeAgent(BaseAgent):
    """Agent for handling silent mode operations."""
    
    def __init__(self, supabase, ai_model):  # Fix #1: Correct constructor
        super().__init__(supabase, ai_model, "SilentModeAgent")
    
    async def process(self, user_input, context, routing_info=None):
        """Process silent mode-related user input and return a response.
        
        Args:
            user_input: The input text from the user
            context: The context of the conversation
            routing_info: NEW - AI classification with smart assumptions
            
        Returns:
            A response to the user input
        """
        user_id = context.get('user_id')
        
        # NEW: Apply AI assumptions to enhance processing
        enhanced_context = self._apply_ai_assumptions(context, routing_info)
        
        # NEW: Use AI assumptions if available
        duration_minutes = None
        if routing_info and routing_info.get('assumptions'):
            print(f"SilentModeAgent using AI assumptions: {routing_info['assumptions']}")
            # Use AI-suggested duration if available
            duration_minutes = routing_info['assumptions'].get('duration_minutes')
        
        # Parse the user input to determine the silent mode operation
        operation = self._determine_operation(user_input)
        
        if operation == 'activate':
            return await self._activate_silent_mode(user_id, user_input, context)
        elif operation == 'deactivate':
            return await self._deactivate_silent_mode(user_id, context)
        elif operation == 'status':
            return await self._get_silent_status(user_id, context)
        else:
            return {
                "status": "error",
                "message": "I'm not sure what silent mode operation you want to perform. Please try again with a clearer request."
            }
    
    def _apply_ai_assumptions(self, context, routing_info):
        """Apply AI assumptions to enhance the context"""
        enhanced_context = context.copy()
        if routing_info:
            enhanced_context.update(routing_info.get('assumptions', {}))
        return enhanced_context
    
    def _determine_operation(self, user_input):
        """Determine the silent mode operation from the user input."""
        user_input_lower = user_input.lower()
        
        if any(phrase in user_input_lower for phrase in [
            'go silent', 'activate silent', 'turn on silent', 'silent mode',
            'quiet mode', "don't reply", 'stop replying', 'no replies'
        ]):
            return 'activate'
        elif any(phrase in user_input_lower for phrase in [
            'exit silent', 'end silent', 'stop silent', 'back online', 'resume replies'
        ]):
            return 'deactivate'
        elif any(phrase in user_input_lower for phrase in [
            'silent status', 'am i silent', 'in silent mode'
        ]):
            return 'status'
        else:
            return None
    
    async def _activate_silent_mode(self, user_id, user_input, context):
        """Activate silent mode based on user input."""
        try:
            # Extract duration from user input
            duration_minutes = self._extract_duration(user_input)
            
            if not duration_minutes:
                duration_minutes = 60  # Default to 1 hour
            
            # Activate silent mode using correct database function
            result = database_personal.activate_silent_mode(
                supabase=self.supabase,
                user_id=user_id,
                duration_minutes=duration_minutes
            )
            
            if result:
                # Log the action
                database_personal.log_action(
                    supabase=self.supabase,
                    user_id=user_id,
                    action_type="silent_mode_activated",
                    entity_type="silent_mode",
                    action_details={
                        "duration_minutes": duration_minutes
                    },
                    success_status=True
                )
                
                hours = duration_minutes // 60
                minutes = duration_minutes % 60
                time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
                
                return {
                    "status": "success",
                    "message": f"Silent mode activated for {time_str}. I won't send any notifications during this time.",
                    "duration_minutes": duration_minutes,
                    "actions": ["silent_mode_activated"]
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to activate silent mode. Please try again."
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error activating silent mode: {str(e)}"
            }
    
    async def _deactivate_silent_mode(self, user_id, context):
        """Deactivate silent mode."""
        try:
            # Deactivate silent mode using correct database function
            result = database_personal.deactivate_silent_mode(
                supabase=self.supabase,
                user_id=user_id
            )
            
            if result:
                # Log the action
                database_personal.log_action(
                    supabase=self.supabase,
                    user_id=user_id,
                    action_type="silent_mode_deactivated",
                    entity_type="silent_mode",
                    action_details={},
                    success_status=True
                )
                
                return {
                    "status": "success",
                    "message": "Silent mode deactivated. I'm back online and will send notifications normally.",
                    "actions": ["silent_mode_deactivated"]
                }
            else:
                return {
                    "status": "error",
                    "message": "Silent mode was not active or failed to deactivate."
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error deactivating silent mode: {str(e)}"
            }
    
    async def _get_silent_status(self, user_id, context):
        """Get current silent mode status."""
        try:
            # Get silent mode status using correct database function
            status = database_personal.get_silent_mode_status(
                supabase=self.supabase,
                user_id=user_id
            )
            
            if status and status.get('is_active'):
                remaining_minutes = status.get('remaining_minutes', 0)
                hours = remaining_minutes // 60
                minutes = remaining_minutes % 60
                time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
                
                return {
                    "status": "success",
                    "message": f"Silent mode is active. {time_str} remaining.",
                    "is_silent": True,
                    "remaining_minutes": remaining_minutes,
                    "actions": ["silent_status_checked"]
                }
            else:
                return {
                    "status": "success",
                    "message": "Silent mode is not active. All notifications are enabled.",
                    "is_silent": False,
                    "actions": ["silent_status_checked"]
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error checking silent mode status: {str(e)}"
            }
    
    def _extract_duration(self, user_input):
        """Extract duration in minutes from user input."""
        import re
        
        user_input_lower = user_input.lower()
        
        # Look for patterns like "for 2 hours", "for 30 minutes"
        duration_patterns = [
            r'for (\d+) hours?',
            r'for (\d+) hrs?',
            r'for (\d+) h',
            r'for (\d+) minutes?',
            r'for (\d+) mins?',
            r'for (\d+) m'
        ]
        
        for pattern in duration_patterns:
            match = re.search(pattern, user_input_lower)
            if match:
                number = int(match.group(1))
                if 'hour' in pattern or 'hr' in pattern or pattern.endswith('h'):
                    return number * 60  # Convert hours to minutes
                else:
                    return number  # Already in minutes
        
        # Look for standalone numbers with context
        if 'hour' in user_input_lower:
            numbers = re.findall(r'\d+', user_input)
            if numbers:
                return int(numbers[0]) * 60
        elif 'minute' in user_input_lower:
            numbers = re.findall(r'\d+', user_input)
            if numbers:
                return int(numbers[0])
        
        return None
