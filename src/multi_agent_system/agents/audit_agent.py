from .base_agent import BaseAgent
import database_personal  # Fix #4: Proper database import
import os

class AuditAgent(BaseAgent):
    """Agent for handling audit and activity logging operations."""
    
    def __init__(self, supabase, ai_model):  # Fix #1: Correct constructor
        super().__init__(supabase, ai_model, "AuditAgent")
        self.comprehensive_prompts = {}
    
    def load_comprehensive_prompts(self):
        """Load ALL prompts from the prompts/v1/ directory and requirements."""
        try:
            prompts_dict = {}
            
            # Load all prompts from v1 directory
            v1_dir = "/workspace/user_input_files/todowa/prompts/v1"
            if os.path.exists(v1_dir):
                for file_name in os.listdir(v1_dir):
                    if file_name.endswith('.md'):
                        prompt_name = file_name.replace('.md', '')
                        file_path = os.path.join(v1_dir, file_name)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            prompts_dict[prompt_name] = f.read()
            
            # Load requirements
            requirements_path = "/workspace/user_input_files/99_requirements.md"
            if os.path.exists(requirements_path):
                with open(requirements_path, 'r', encoding='utf-8') as f:
                    prompts_dict['requirements'] = f.read()
            
            # Create comprehensive system prompt for audit operations
            self.comprehensive_prompts = {
                'core_system': self._build_audit_system_prompt(prompts_dict),
                'action_schema': prompts_dict.get('01_action_schema', ''),
                'safety_validation': prompts_dict.get('07_safety_validation', ''),
                'templates': prompts_dict.get('08_templates', ''),
                'context_memory': prompts_dict.get('03_context_memory', ''),
                'requirements': prompts_dict.get('requirements', ''),
                'all_prompts': prompts_dict
            }
            
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}
    
    def _build_audit_system_prompt(self, prompts_dict):
        """Build comprehensive system prompt for audit agent."""
        core_identity = prompts_dict.get('00_core_identity', '')
        action_schema = prompts_dict.get('01_action_schema', '')
        safety_validation = prompts_dict.get('07_safety_validation', '')
        templates = prompts_dict.get('08_templates', '')
        context_memory = prompts_dict.get('03_context_memory', '')
        requirements = prompts_dict.get('requirements', '')
        
        return f"""{core_identity}

## AUDIT AGENT SPECIALIZATION
You are specifically focused on audit and activity monitoring including:
- Viewing and analyzing user activity logs
- Filtering and searching through historical data
- Providing activity summaries and insights
- Maintaining data privacy and security
- Generating audit reports and analytics

{action_schema}

{safety_validation}

{templates}

{context_memory}

## REQUIREMENTS COMPLIANCE
{requirements}

## AUDIT AGENT BEHAVIOR
- Apply structured templates for audit report formatting
- Follow safety validation protocols for data access
- Use comprehensive action schema for audit operations
- Maintain privacy and security in all audit activities
- Provide clear, organized activity summaries"""

    async def process(self, user_input, context, routing_info=None):
        """Process audit-related user input with comprehensive prompt system.
        
        Args:
            user_input: The input text from the user
            context: The context of the conversation
            routing_info: NEW - AI classification with smart assumptions
            
        Returns:
            A response to the user input
        """
        user_id = context.get('user_id')
        
        # Load comprehensive prompts
        if not self.comprehensive_prompts:
            self.load_comprehensive_prompts()
        
        # NEW: Apply AI assumptions to enhance processing
        enhanced_context = self._apply_ai_assumptions(context, routing_info)
        
        # NEW: Use AI assumptions if available
        if routing_info and routing_info.get('assumptions'):
            print(f"AuditAgent using AI assumptions: {routing_info['assumptions']}")
        
        # Parse the user input to determine the audit operation
        operation = self._determine_operation(user_input)
        
        if operation == 'view_activity':
            return await self._view_activity(user_id, user_input, enhanced_context)
        elif operation == 'view_logs':
            return await self._view_logs(user_id, user_input, enhanced_context)
        elif operation == 'filter_activity':
            return await self._filter_activity(user_id, user_input, enhanced_context)
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
