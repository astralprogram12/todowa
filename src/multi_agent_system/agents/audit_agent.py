from .base_agent import BaseAgent
import database_personal  # Fix #4: Proper database import

class AuditAgent(BaseAgent):
    """Agent for handling audit and activity logging operations."""
    
    def __init__(self, supabase, ai_model):  # Fix #1: Correct constructor
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
    
    def _apply_ai_assumptions(self, context, routing_info):
        """Apply AI assumptions to enhance the context"""
        enhanced_context = context.copy()
        if routing_info:
            enhanced_context.update(routing_info.get('assumptions', {}))
        return enhanced_context
    
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
            # Determine the time range from the user input
            days = self._extract_time_range(user_input)
            
            # Get the activity using correct database function
            activity = database_personal.get_user_activity(
                supabase=self.supabase,
                user_id=user_id,
                days=days or 7  # Default to 7 days
            )
            
            # Log the action
            database_personal.log_action(
                supabase=self.supabase,
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
            return {
                "status": "error",
                "message": f"Error retrieving activity: {str(e)}"
            }
    
    async def _view_logs(self, user_id, user_input, context):
        """View system logs."""
        try:
            # Get system logs using correct database function
            logs = database_personal.get_system_logs(
                supabase=self.supabase,
                user_id=user_id,
                limit=50
            )
            
            if not logs:
                return {
                    "status": "ok",
                    "message": "No recent logs found."
                }
            
            formatted_logs = self._format_logs(logs)
            
            return {
                "status": "ok",
                "message": "Here are your recent system logs:",
                "logs": formatted_logs
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error retrieving logs: {str(e)}"
            }
    
    async def _filter_activity(self, user_id, user_input, context):
        """Filter user activity based on criteria."""
        try:
            # Extract filter criteria from user input
            filters = self._extract_filters(user_input)
            
            # Get filtered activity
            activity = database_personal.get_filtered_activity(
                supabase=self.supabase,
                user_id=user_id,
                **filters
            )
            
            if not activity:
                return {
                    "status": "ok",
                    "message": "No activity found matching your criteria."
                }
            
            formatted_activity = self._format_activity(activity)
            
            return {
                "status": "ok",
                "message": "Here's the filtered activity:",
                "activity": formatted_activity
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error filtering activity: {str(e)}"
            }
    
    def _extract_time_range(self, user_input):
        """Extract time range in days from user input."""
        user_input_lower = user_input.lower()
        
        if 'today' in user_input_lower:
            return 1
        elif 'week' in user_input_lower:
            return 7
        elif 'month' in user_input_lower:
            return 30
        else:
            # Try to extract number of days
            import re
            days_match = re.search(r'(\d+)\s*days?', user_input_lower)
            if days_match:
                return int(days_match.group(1))
        
        return None
    
    def _extract_filters(self, user_input):
        """Extract filter criteria from user input."""
        filters = {}
        user_input_lower = user_input.lower()
        
        # Extract action type filter
        if 'tasks' in user_input_lower:
            filters['action_type'] = 'task'
        elif 'conversations' in user_input_lower:
            filters['action_type'] = 'conversation'
        
        # Extract date filter
        days = self._extract_time_range(user_input)
        if days:
            filters['days'] = days
        
        return filters
    
    def _format_activity(self, activity):
        """Format activity data for display."""
        if not activity:
            return []
        
        formatted = []
        for item in activity:
            formatted.append({
                'time': item.get('created_at', ''),
                'action': item.get('action_type', 'Unknown'),
                'entity': item.get('entity_type', ''),
                'details': item.get('action_details', {})
            })
        
        return formatted
    
    def _format_logs(self, logs):
        """Format log data for display."""
        if not logs:
            return []
        
        formatted = []
        for log in logs:
            formatted.append({
                'time': log.get('created_at', ''),
                'level': log.get('level', 'INFO'),
                'message': log.get('message', ''),
                'details': log.get('details', {})
            })
        
        return formatted
