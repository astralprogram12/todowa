# task_agent.py
# UPDATED VERSION - Example of how to update individual agent files
# Location: src/multi_agent_system/agents/task_agent.py

from .base_agent import BaseAgent

class TaskAgent(BaseAgent):
    """Agent for handling task-related operations with AI-enhanced processing."""
    
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model, "TaskAgent")
    
    # UPDATED METHOD SIGNATURE - Added routing_info=None parameter
    async def process(self, user_input, context, routing_info=None):
        """Process task-related user input with AI assumptions.
        
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
            print(f"TaskAgent using AI assumptions: {routing_info['assumptions']}")
            return await self._process_with_ai_assumptions(user_input, enhanced_context, routing_info)
        
        # Keep existing logic as fallback
        operation = self._determine_operation(user_input)
        
        if operation == 'add':
            return await self._add_task(user_id, user_input, enhanced_context)
        elif operation == 'update':
            return await self._update_task(user_id, user_input, enhanced_context)
        elif operation == 'delete':
            return await self._delete_task(user_id, user_input, enhanced_context)
        elif operation == 'complete':
            return await self._complete_task(user_id, user_input, enhanced_context)
        elif operation == 'list':
            return await self._list_tasks(user_id, user_input, enhanced_context)
        else:
            # Use AI assumptions to make a confident guess
            ai_assumptions = routing_info.get('assumptions', {}) if routing_info else {}
            return await self._smart_task_creation(user_id, user_input, enhanced_context, ai_assumptions)
    
    async def _process_with_ai_assumptions(self, user_input, context, routing_info):
        """Process task with AI-provided assumptions"""
        user_id = context.get('user_id')
        assumptions = routing_info.get('assumptions', {})
        
        # Extract task details with AI enhancement
        title = self._extract_title(user_input) or user_input.strip()
        category = assumptions.get('category') or self._extract_category(user_input) or 'general'
        priority = assumptions.get('priority') or self._extract_priority(user_input) or 'medium'
        due_date = self._extract_due_date(user_input)
        notes = self._extract_notes(user_input)
        
        # Add the task using enhanced details
        from database_personal import add_task_entry
        
        try:
            task = add_task_entry(
                supabase=self.supabase,
                user_id=user_id,
                title=title,
                category=category,
                priority=priority,
                due_date=due_date,
                notes=notes
            )
            
            # Log the action with AI confidence
            self._log_action(
                user_id=user_id,
                action_type="add_task",
                entity_type="task",
                entity_id=task.get('id'),
                action_details={
                    "title": title,
                    "category": category,
                    "priority": priority,
                    "ai_enhanced": True,
                    "ai_confidence": routing_info.get('confidence', 0.6)
                },
                success_status=True
            )
            
            # Prepare enhanced response
            response = f"✅ I've created your task with smart enhancements:\n\n"
            response += f"**Task:** {title}\n"
            response += f"**Category:** {category}"
            if assumptions.get('category'):
                response += " (AI suggested)"
            response += f"\n**Priority:** {priority}"
            if assumptions.get('priority'):
                response += " (AI suggested)"
            if due_date:
                response += f"\n**Due:** {due_date}"
            response += "\n\nAnything you'd like to adjust?"
            
            return {
                "status": "success",
                "message": response,
                "actions": [{
                    "type": "add_task",
                    "task_id": task.get('id'),
                    "ai_enhanced": True
                }]
            }
            
        except Exception as e:
            print(f"Error adding task: {e}")
            return {
                "status": "error",
                "message": "I had trouble creating that task. Please try again."
            }
    
    async def _smart_task_creation(self, user_id, user_input, context, ai_assumptions):
        """Create task with smart defaults when operation is unclear"""
        # Default to adding a task with AI assumptions
        title = user_input.strip()
        category = ai_assumptions.get('category', 'general')
        priority = ai_assumptions.get('priority', 'medium')
        
        from database_personal import add_task_entry
        
        try:
            task = add_task_entry(
                supabase=self.supabase,
                user_id=user_id,
                title=title,
                category=category,
                priority=priority
            )
            
            return {
                "status": "success",
                "message": f"I've added '{title}' as a {priority} priority {category} task. Is that what you wanted?",
                "actions": [{
                    "type": "add_task",
                    "task_id": task.get('id'),
                    "confident_guess": True
                }]
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": "I'll help you with that task. Could you provide a bit more detail?"
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
            # Default to add if unclear but contains 'task' or seems task-related
            return 'add' if 'task' in user_input_lower else None
    
    # Keep all existing helper methods unchanged
    def _extract_title(self, user_input):
        """Extract task title from user input"""
        # Simple extraction logic - improve as needed
        for prefix in ['add task:', 'create task:', 'new task:', 'task:']:
            if prefix in user_input.lower():
                return user_input.lower().split(prefix, 1)[1].strip()
        return user_input.strip()
    
    def _extract_category(self, user_input):
        """Extract category from user input"""
        user_lower = user_input.lower()
        
        # Category mapping
        categories = {
            'work': ['work', 'job', 'office', 'meeting', 'project'],
            'personal': ['personal', 'home', 'family', 'health'],
            'finance': ['pay', 'bill', 'money', 'budget', 'expense'],
            'shopping': ['buy', 'shop', 'grocery', 'store', 'purchase'],
            'health': ['doctor', 'gym', 'exercise', 'medical', 'appointment']
        }
        
        for category, keywords in categories.items():
            if any(keyword in user_lower for keyword in keywords):
                return category
        
        return None
    
    def _extract_priority(self, user_input):
        """Extract priority from user input"""
        user_lower = user_input.lower()
        
        if any(word in user_lower for word in ['urgent', 'asap', 'critical', 'important']):
            return 'high'
        elif any(word in user_lower for word in ['low', 'minor', 'sometime', 'eventually']):
            return 'low'
        
        return None
    
    def _extract_due_date(self, user_input):
        """Extract due date from user input"""
        # Implement date extraction logic
        # For now, return None
        return None
    
    def _extract_notes(self, user_input):
        """Extract additional notes from user input"""
        # Implement notes extraction logic
        # For now, return None
        return None
    
    # Implement other existing methods (_add_task, _update_task, etc.)
    # Keep all existing implementations - just update the method signatures
    # to use the enhanced_context instead of context
    
    async def _add_task(self, user_id, user_input, context):
        """Add a new task - existing implementation"""
        # Your existing _add_task implementation here
        pass
    
    async def _update_task(self, user_id, user_input, context):
        """Update existing task - existing implementation"""
        # Your existing _update_task implementation here
        pass
    
    async def _delete_task(self, user_id, user_input, context):
        """Delete a task - existing implementation"""
        # Your existing _delete_task implementation here
        pass
    
    async def _complete_task(self, user_id, user_input, context):
        """Complete a task - existing implementation"""
        # Your existing _complete_task implementation here
        pass
    
    async def _list_tasks(self, user_id, user_input, context):
        """List tasks - existing implementation"""
        # Your existing _list_tasks implementation here
        pass