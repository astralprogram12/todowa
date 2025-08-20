# Audit Agent - handles audit and activity logging operations

from .base_agent import BaseAgent

class AuditAgent(BaseAgent):
    """Agent for handling audit and activity logging operations."""
    
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model, "AuditAgent")
    
    async def process(self, user_input, context, routing_info=None):
        """Process audit-related user input and return a response.
        
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
            print(f"AuditAgent using AI assumptions: {routing_info['assumptions']}")
        
        # Parse the user input to determine the audit operation
        operation = self._determine_operation(user_input)
        
        if operation == 'view_activity':
            return await self._view_activity(user_id, user_input, context)
        elif operation == 'view_logs':
            return await self._view_logs(user_id, user_input, context)
        elif operation == 'filter_activity':
            return await self._filter_activity(user_id, user_input, context)
        else:
            return {
                "status": "error",
                "message": "I'm not sure what audit operation you want to perform. Please try again with a clearer request."
            }
    
    def _determine_operation(self, user_input):
        """Determine the audit operation from the user input."""
        user_input_lower = user_input.lower()
        
        if any(phrase in user_input_lower for phrase in ['show activity', 'view activity', 'recent activity', 'what have i done']):
            return 'view_activity'
        elif any(phrase in user_input_lower for phrase in ['show logs', 'view logs', 'system logs', 'error logs']):
            return 'view_logs'
        elif any(phrase in user_input_lower for phrase in ['filter activity', 'search activity', 'find activities']):
            return 'filter_activity'
        else:
            return None
    
    async def _view_activity(self, user_id, user_input, context):
        """View recent user activity."""
        try:
            # Query the user's recent activity from the database
            from database_personal import get_user_activity
            
            # Determine the time range from the user input
            days = self._extract_time_range(user_input)
            
            # Get the activity
            activity = get_user_activity(
                supabase=self.supabase,
                user_id=user_id,
                days=days or 7  # Default to 7 days
            )
            
            # Log the action
            self._log_action(
                user_id=user_id,
                action_type="view_activity",
                entity_type="audit",
                action_details={
                    "days": days or 7
                },
                success_status=True
            )
            
            if not activity:
                return {
                    "status": "ok",
                    "message": f"No activity found in the past {days or 7} days."
                }
            
            # Format the activity for display
            formatted_activity = self._format_activity(activity)
            
            return {
                "status": "ok",
                "message": f"Here's your activity from the past {days or 7} days:",
                "activity": formatted_activity
            }
            
        except Exception as e:
            error_msg = str(e)
            
            # Log the error
            self._log_action(
                user_id=user_id,
                action_type="view_activity",
                entity_type="audit",
                action_details={
                    "days": days or 7
                },
                success_status=False,
                error_details=error_msg
            )
            
            return {
                "status": "error",
                "message": f"Failed to retrieve activity: {error_msg}"
            }
    
    def _extract_time_range(self, user_input):
        """Extract the time range from the user input."""
        import re
        
        # Look for patterns like "past 7 days" or "last 30 days"
        time_patterns = [
            r'past (\d+) days',
            r'last (\d+) days',
            r'(\d+) days',
            r'past (\d+) day',
            r'last (\d+) day',
            r'(\d+) day'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, user_input.lower())
            if match:
                return int(match.group(1))
        
        return None
    
    def _format_activity(self, activity):
        """Format the activity data for display."""
        formatted = []
        
        for item in activity:
            # Convert timestamp to user's timezone
            timestamp = item.get('created_at')
            if timestamp:
                local_time = self.convert_utc_to_user_timezone(
                    user_id=item.get('user_id'),
                    utc_time_str=timestamp
                )
            else:
                local_time = "Unknown time"
            
            # Format the activity item
            formatted_item = {
                "time": local_time,
                "action": item.get('action_type', 'Unknown action'),
                "entity": item.get('entity_type', 'Unknown entity'),
                "status": "Successful" if item.get('success_status') else "Failed",
                "details": item.get('action_details', {})
            }
            
            formatted.append(formatted_item)
        
        return formatted
    
    # Placeholder methods for other audit operations
    async def _view_logs(self, user_id, user_input, context):
        """View system logs."""
        # TODO: Implement log viewing logic
        return {"status": "ok", "message": "Log viewing functionality not yet implemented."}
    
    async def _filter_activity(self, user_id, user_input, context):
        """Filter activity based on criteria."""
        # TODO: Implement activity filtering logic
        return {"status": "ok", "message": "Activity filtering functionality not yet implemented."}
