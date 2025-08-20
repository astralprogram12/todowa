# Silent Mode Agent - handles silent mode operations

from .base_agent import BaseAgent

class SilentModeAgent(BaseAgent):
    """Agent for handling silent mode operations."""
    
    def __init__(self, supabase, ai_model):
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
        # Extract duration from user input
        duration_minutes = self._extract_duration(user_input)
        
        try:
            from database_silent import activate_silent_mode
            
            # Create a silent mode session
            session = activate_silent_mode(
                supabase=self.supabase,
                user_id=user_id,
                duration_minutes=duration_minutes or 60,  # Default to 60 minutes
                trigger_type='manual'
            )
            
            # Log the action
            self._log_action(
                user_id=user_id,
                action_type="activate_silent_mode",
                entity_type="silent_session",
                entity_id=session.get('id'),
                action_details={
                    "duration_minutes": duration_minutes or 60,
                    "trigger_type": 'manual'
                },
                success_status=True
            )
            
            duration_text = f"{duration_minutes} minutes" if duration_minutes else "60 minutes (default)"
            
            return {
                "status": "ok",
                "message": f"Silent mode activated for {duration_text}.",
                "session_details": session,
                "is_silent": True
            }
            
        except Exception as e:
            error_msg = str(e)
            
            # Log the error
            self._log_action(
                user_id=user_id,
                action_type="activate_silent_mode",
                entity_type="silent_session",
                action_details={
                    "duration_minutes": duration_minutes or 60,
                    "trigger_type": 'manual'
                },
                success_status=False,
                error_details=error_msg
            )
            
            return {
                "status": "error",
                "message": f"Failed to activate silent mode: {error_msg}",
                "is_silent": False
            }
    
    async def _deactivate_silent_mode(self, user_id, context):
        """Deactivate silent mode."""
        try:
            from database_silent import deactivate_silent_mode
            
            # Deactivate silent mode
            result = deactivate_silent_mode(
                supabase=self.supabase,
                user_id=user_id
            )
            
            # Log the action
            self._log_action(
                user_id=user_id,
                action_type="deactivate_silent_mode",
                entity_type="silent_session",
                action_details={},
                success_status=True
            )
            
            return {
                "status": "ok",
                "message": "Silent mode deactivated.",
                "session_summary": result,
                "is_silent": False
            }
            
        except Exception as e:
            error_msg = str(e)
            
            # Log the error
            self._log_action(
                user_id=user_id,
                action_type="deactivate_silent_mode",
                entity_type="silent_session",
                action_details={},
                success_status=False,
                error_details=error_msg
            )
            
            return {
                "status": "error",
                "message": f"Failed to deactivate silent mode: {error_msg}"
            }
    
    async def _get_silent_status(self, user_id, context):
        """Get the current silent mode status."""
        try:
            from database_silent import get_silent_status
            
            # Get the current silent mode status
            status = get_silent_status(
                supabase=self.supabase,
                user_id=user_id
            )
            
            # Log the action
            self._log_action(
                user_id=user_id,
                action_type="get_silent_status",
                entity_type="silent_session",
                action_details={},
                success_status=True
            )
            
            if status.get('is_silent'):
                return {
                    "status": "ok",
                    "message": "You are currently in silent mode.",
                    "is_silent": True,
                    "session_details": status
                }
            else:
                return {
                    "status": "ok",
                    "message": "You are not in silent mode.",
                    "is_silent": False
                }
            
        except Exception as e:
            error_msg = str(e)
            
            # Log the error
            self._log_action(
                user_id=user_id,
                action_type="get_silent_status",
                entity_type="silent_session",
                action_details={},
                success_status=False,
                error_details=error_msg
            )
            
            return {
                "status": "error",
                "message": f"Failed to get silent mode status: {error_msg}"
            }
    
    def _extract_duration(self, user_input):
        """Extract the duration from the user input."""
        import re
        
        # Look for patterns like "for 30 minutes" or "1 hour"
        duration_patterns = [
            r'for (\d+) minutes',
            r'for (\d+) minute',
            r'(\d+) minutes',
            r'(\d+) minute',
            r'for (\d+) hours',
            r'for (\d+) hour',
            r'(\d+) hours',
            r'(\d+) hour'
        ]
        
        for pattern in duration_patterns:
            match = re.search(pattern, user_input.lower())
            if match:
                value = int(match.group(1))
                if 'hour' in pattern:
                    # Convert hours to minutes
                    return value * 60
                return value
        
        return None
