# Reminder Agent - handles reminder-related operations

from .base_agent import BaseAgent

class ReminderAgent(BaseAgent):
    """Agent for handling reminder-related operations."""
    
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model, "ReminderAgent")
    
    async def process(self, user_input, context, routing_info=None):
        """Process reminder-related user input and return a response.
        
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
            print(f"ReminderAgent using AI assumptions: {routing_info['assumptions']}")
            return await self._process_with_ai_assumptions(user_input, enhanced_context, routing_info)
        
        # Parse the user input to determine the reminder operation
        operation = self._determine_operation(user_input)
        
        if operation == 'set':
            return await self._set_reminder(user_id, user_input, context)
        elif operation == 'update':
            return await self._update_reminder(user_id, user_input, context)
        elif operation == 'delete':
            return await self._delete_reminder(user_id, user_input, context)
        elif operation == 'list':
            return await self._list_reminders(user_id, user_input, context)
        else:
            return {
                "status": "error",
                "message": "I'm not sure what reminder operation you want to perform. Please try again with a clearer request."
            }
    
    def _determine_operation(self, user_input):
        """Determine the reminder operation from the user input."""
        user_input_lower = user_input.lower()
        
        if any(phrase in user_input_lower for phrase in ['set reminder', 'add reminder', 'create reminder', 'remind me']):
            return 'set'
        elif any(phrase in user_input_lower for phrase in ['update reminder', 'change reminder', 'reschedule']):
            return 'update'
        elif any(phrase in user_input_lower for phrase in ['delete reminder', 'remove reminder', 'cancel reminder']):
            return 'delete'
        elif any(phrase in user_input_lower for phrase in ['list reminders', 'show reminders', 'get reminders']):
            return 'list'
        else:
            # Default to set if unclear but contains 'remind'
            return 'set' if 'remind' in user_input_lower else None
    
    async def _process_with_ai_assumptions(self, user_input, context, routing_info):
        """Process reminder with AI-provided assumptions"""
        user_id = context.get('user_id')
        assumptions = routing_info.get('assumptions', {})
        
        # Extract reminder details with AI enhancement
        task_title = self._extract_task_title(user_input) or assumptions.get('task_title') or user_input.strip()
        reminder_time = self._extract_reminder_time(user_input) or assumptions.get('reminder_time')
        
        if not reminder_time:
            # Make a confident guess about timing
            default_time = assumptions.get('default_time', 'tomorrow at 9am')
            return {
                "status": "ok", 
                "message": f"I'll set a reminder for '{task_title}' {default_time}. Is that correct?",
                "confident_guess": True
            }
        
        # Continue with setting the reminder using enhanced details
        return await self._set_reminder(user_id, user_input, context)
    
    async def _set_reminder(self, user_id, user_input, context):
        """Set a reminder based on user input."""
        # Extract reminder details from the user input
        task_title = self._extract_task_title(user_input)
        reminder_time = self._extract_reminder_time(user_input)
        
        if not task_title:
            return {
                "status": "error",
                "message": "I couldn't determine which task to set a reminder for. Please specify a task title."
            }
        
        if not reminder_time:
            return {
                "status": "error",
                "message": "I couldn't determine when to remind you. Please specify a reminder time."
            }
        
        # Set the reminder using the database function
        try:
            # Try to find existing task first
            task = self._find_task(user_id, task_title)
            
            # If task doesn't exist, create it
            if not task:
                from database_personal import add_task_entry
                
                task = add_task_entry(
                    supabase=self.supabase,
                    user_id=user_id,
                    title=task_title
                )
            
            # Update the task with the reminder
            from database_personal import update_task_entry
            
            update_task_entry(
                supabase=self.supabase,
                user_id=user_id,
                task_id=task['id'],
                patch={
                    "reminder_at": reminder_time,
                    "reminder_sent": False
                }
            )
            
            # Log the action
            self._log_action(
                user_id=user_id,
                action_type="set_reminder",
                entity_type="reminder",
                entity_id=task['id'],
                action_details={
                    "task_title": task['title'],
                    "reminder_time": reminder_time
                },
                success_status=True
            )
            
            # Convert UTC to user's timezone for display
            local_reminder_time = self.convert_utc_to_user_timezone(user_id, reminder_time)
            
            return {
                "status": "ok",
                "message": f"I've set a reminder for '{task['title']}' at {local_reminder_time}.",
                "task": task
            }
            
        except Exception as e:
            error_msg = str(e)
            
            # Log the error
            self._log_action(
                user_id=user_id,
                action_type="set_reminder",
                entity_type="reminder",
                action_details={
                    "task_title": task_title,
                    "reminder_time": reminder_time
                },
                success_status=False,
                error_details=error_msg
            )
            
            return {
                "status": "error",
                "message": f"Failed to set reminder: {error_msg}"
            }
    
    def _find_task(self, user_id, task_title):
        """Find a task by title."""
        from database_personal import query_tasks
        
        tasks = query_tasks(
            supabase=self.supabase,
            user_id=user_id,
            title_like=task_title
        )
        
        if tasks:
            return tasks[0]
        return None
    
    # Helper methods for extracting reminder details from user input
    def _extract_task_title(self, user_input):
        """Extract the task title from the user input."""
        user_input_lower = user_input.lower()
        
        # Look for task title indicators
        title_indicators = ['remind me about', 'remind me to', 'set reminder for', 'reminder for']
        for indicator in title_indicators:
            if indicator in user_input_lower:
                parts = user_input_lower.split(indicator, 1)
                if len(parts) > 1:
                    title_part = parts[1].strip()
                    
                    # Extract the title before the time indicator
                    time_indicators = ['at', 'on', 'by', 'in']
                    for time_indicator in time_indicators:
                        if f" {time_indicator} " in title_part:
                            title_part = title_part.split(f" {time_indicator} ", 1)[0]
                    
                    return title_part.strip()
        
        return None
    
    def _extract_reminder_time(self, user_input):
        """Extract the reminder time from the user input."""
        # This is a simplified version - in a real implementation, this would use
        # a date parser to handle various time formats and relative times
        user_input_lower = user_input.lower()
        
        # Look for time indicators
        time_indicators = ['at', 'on', 'by', 'in']
        for indicator in time_indicators:
            if f" {indicator} " in user_input_lower:
                parts = user_input_lower.split(f" {indicator} ", 1)
                if len(parts) > 1:
                    time_part = parts[1].strip()
                    
                    # In a real implementation, this would parse and validate the time
                    # For now, just return the extracted text
                    # We would also convert this to ISO 8601 format in UTC
                    return time_part
        
        return None
    
    # Placeholder methods for other reminder operations
    async def _update_reminder(self, user_id, user_input, context):
        """Update an existing reminder based on user input."""
        # TODO: Implement reminder update logic
        return {"status": "ok", "message": "Reminder update functionality not yet implemented."}
    
    async def _delete_reminder(self, user_id, user_input, context):
        """Delete a reminder based on user input."""
        # TODO: Implement reminder deletion logic
        return {"status": "ok", "message": "Reminder deletion functionality not yet implemented."}
    
    async def _list_reminders(self, user_id, user_input, context):
        """List reminders based on user input."""
        # TODO: Implement reminder listing logic
        return {"status": "ok", "message": "Reminder listing functionality not yet implemented."}
