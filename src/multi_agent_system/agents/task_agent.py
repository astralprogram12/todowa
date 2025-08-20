# Task Agent - handles task-related operations

from .base_agent import BaseAgent

class TaskAgent(BaseAgent):
    """Agent for handling task-related operations."""
    
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model, "TaskAgent")
    
    async def process(self, user_input, context):
        """Process task-related user input and return a response.
        
        Args:
            user_input: The input text from the user
            context: The context of the conversation
            
        Returns:
            A response to the user input
        """
        user_id = context.get('user_id')
        
        # Parse the user input to determine the task operation
        operation = self._determine_operation(user_input)
        
        if operation == 'add':
            return await self._add_task(user_id, user_input, context)
        elif operation == 'update':
            return await self._update_task(user_id, user_input, context)
        elif operation == 'delete':
            return await self._delete_task(user_id, user_input, context)
        elif operation == 'complete':
            return await self._complete_task(user_id, user_input, context)
        elif operation == 'list':
            return await self._list_tasks(user_id, user_input, context)
        else:
            return {
                "status": "error",
                "message": "I'm not sure what task operation you want to perform. Please try again with a clearer request."
            }
    
    def _determine_operation(self, user_input):
        """Determine the task operation from the user input."""
        user_input_lower = user_input.lower()
        
        if any(phrase in user_input_lower for phrase in ['add task', 'create task', 'new task']):
            return 'add'
        elif any(phrase in user_input_lower for phrase in ['update task', 'edit task', 'change task', 'modify task']):
            return 'update'
        elif any(phrase in user_input_lower for phrase in ['delete task', 'remove task']):
            return 'delete'
        elif any(phrase in user_input_lower for phrase in ['complete task', 'finish task', 'mark task', 'done']):
            return 'complete'
        elif any(phrase in user_input_lower for phrase in ['list tasks', 'show tasks', 'get tasks']):
            return 'list'
        else:
            # Default to add if unclear but contains 'task'
            return 'add' if 'task' in user_input_lower else None
    
    async def _add_task(self, user_id, user_input, context):
        """Add a new task based on user input."""
        # Extract task details from the user input
        title = self._extract_title(user_input)
        category = self._extract_category(user_input)
        due_date = self._extract_due_date(user_input)
        notes = self._extract_notes(user_input)
        
        if not title:
            return {
                "status": "error",
                "message": "I couldn't determine the task title. Please specify a clear task title."
            }
        
        # Add the task using the database function
        from database_personal import add_task_entry
        
        try:
            task = add_task_entry(
                supabase=self.supabase,
                user_id=user_id,
                title=title,
                category=category,
                due_date=due_date,
                notes=notes
            )
            
            # Log the action
            self._log_action(
                user_id=user_id,
                action_type="add_task",
                entity_type="task",
                entity_id=task.get('id'),
                action_details={
                    "title": title,
                    "category": category,
                    "due_date": due_date
                },
                success_status=True
            )
            
            # Prepare a user-friendly response
            response = f"I've added the task: '{title}'"
            if category:
                response += f" in category '{category}'"
            if due_date:
                # Convert UTC to user's timezone for display
                local_due_date = self.convert_utc_to_user_timezone(user_id, due_date)
                response += f" due on {local_due_date}"
            
            return {
                "status": "ok",
                "message": response,
                "task": task
            }
            
        except Exception as e:
            error_msg = str(e)
            
            # Log the error
            self._log_action(
                user_id=user_id,
                action_type="add_task",
                entity_type="task",
                action_details={
                    "title": title,
                    "category": category,
                    "due_date": due_date
                },
                success_status=False,
                error_details=error_msg
            )
            
            return {
                "status": "error",
                "message": f"Failed to add task: {error_msg}"
            }
    
    # Helper methods for extracting task details from user input
    def _extract_title(self, user_input):
        """Extract the task title from the user input."""
        # Remove action keywords
        cleaned_input = user_input.lower()
        for phrase in ['add task', 'create task', 'new task', 'task:']:
            cleaned_input = cleaned_input.replace(phrase, '')
        
        # Remove category indicators
        category_indicators = ['in category', 'category:', 'category']
        for indicator in category_indicators:
            if indicator in cleaned_input:
                parts = cleaned_input.split(indicator, 1)
                cleaned_input = parts[0]
        
        # Remove due date indicators
        date_indicators = ['due on', 'due date', 'due:', 'due']
        for indicator in date_indicators:
            if indicator in cleaned_input:
                parts = cleaned_input.split(indicator, 1)
                cleaned_input = parts[0]
        
        # Remove note indicators
        note_indicators = ['with notes', 'notes:', 'note:']
        for indicator in note_indicators:
            if indicator in cleaned_input:
                parts = cleaned_input.split(indicator, 1)
                cleaned_input = parts[0]
        
        # Clean up and return the title
        title = cleaned_input.strip()
        if title.startswith('"') and title.endswith('"'):
            title = title[1:-1].strip()
        if title.startswith("'") and title.endswith("'"):
            title = title[1:-1].strip()
        
        return title
    
    def _extract_category(self, user_input):
        """Extract the task category from the user input."""
        user_input_lower = user_input.lower()
        
        # Look for category indicators
        category_indicators = ['in category', 'category:', 'category']
        for indicator in category_indicators:
            if indicator in user_input_lower:
                parts = user_input_lower.split(indicator, 1)
                if len(parts) > 1:
                    category_part = parts[1].strip()
                    
                    # Extract the category before the next indicator
                    end_indicators = ['due on', 'due date', 'due:', 'due', 'with notes', 'notes:', 'note:']
                    for end_indicator in end_indicators:
                        if end_indicator in category_part:
                            category_part = category_part.split(end_indicator, 1)[0]
                    
                    # Clean up and return the category
                    category = category_part.strip()
                    if category.startswith('"') and category.endswith('"'):
                        category = category[1:-1].strip()
                    if category.startswith("'") and category.endswith("'"):
                        category = category[1:-1].strip()
                    
                    return category
        
        return None
    
    def _extract_due_date(self, user_input):
        """Extract the due date from the user input."""
        # This is a simplified version - in a real implementation, this would use
        # a date parser to handle various date formats and relative dates
        user_input_lower = user_input.lower()
        
        # Look for due date indicators
        date_indicators = ['due on', 'due date', 'due:', 'due']
        for indicator in date_indicators:
            if indicator in user_input_lower:
                parts = user_input_lower.split(indicator, 1)
                if len(parts) > 1:
                    date_part = parts[1].strip()
                    
                    # Extract the date before the next indicator
                    end_indicators = ['with notes', 'notes:', 'note:', 'category']
                    for end_indicator in end_indicators:
                        if end_indicator in date_part:
                            date_part = date_part.split(end_indicator, 1)[0]
                    
                    # In a real implementation, this would parse and validate the date
                    # For now, just return the extracted text
                    return date_part.strip()
        
        return None
    
    def _extract_notes(self, user_input):
        """Extract notes from the user input."""
        user_input_lower = user_input.lower()
        
        # Look for note indicators
        note_indicators = ['with notes', 'notes:', 'note:']
        for indicator in note_indicators:
            if indicator in user_input_lower:
                parts = user_input_lower.split(indicator, 1)
                if len(parts) > 1:
                    notes = parts[1].strip()
                    return notes
        
        return None
    
    # Placeholder methods for other task operations
    async def _update_task(self, user_id, user_input, context):
        """Update an existing task based on user input."""
        # TODO: Implement task update logic
        return {"status": "ok", "message": "Task update functionality not yet implemented."}
    
    async def _delete_task(self, user_id, user_input, context):
        """Delete a task based on user input."""
        # TODO: Implement task deletion logic
        return {"status": "ok", "message": "Task deletion functionality not yet implemented."}
    
    async def _complete_task(self, user_id, user_input, context):
        """Mark a task as completed based on user input."""
        # TODO: Implement task completion logic
        return {"status": "ok", "message": "Task completion functionality not yet implemented."}
    
    async def _list_tasks(self, user_id, user_input, context):
        """List tasks based on user input."""
        # TODO: Implement task listing logic
        return {"status": "ok", "message": "Task listing functionality not yet implemented."}
