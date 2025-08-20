from .base_agent import BaseAgent
import database_personal  # Fix #4: Proper database import
import os

class TaskAgent(BaseAgent):
    """Agent for handling task-related operations with AI-enhanced processing."""
    
    def __init__(self, supabase, ai_model):  # Fix #1: Correct constructor
        super().__init__(supabase, ai_model, "TaskAgent")
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
            
            # Create comprehensive system prompt for task management
            self.comprehensive_prompts = {
                'core_system': self._build_task_system_prompt(prompts_dict),
                'action_schema': prompts_dict.get('01_action_schema', ''),
                'task_processing': prompts_dict.get('02_task_processing', ''),
                'context_memory': prompts_dict.get('03_context_memory', ''),
                'templates': prompts_dict.get('08_templates', ''),
                'requirements': prompts_dict.get('requirements', ''),
                'all_prompts': prompts_dict
            }
            
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}
    
    def _build_task_system_prompt(self, prompts_dict):
        """Build comprehensive system prompt for task agent."""
        core_identity = prompts_dict.get('00_core_identity', '')
        action_schema = prompts_dict.get('01_action_schema', '')
        task_processing = prompts_dict.get('02_task_processing', '')
        context_memory = prompts_dict.get('03_context_memory', '')
        templates = prompts_dict.get('08_templates', '')
        requirements = prompts_dict.get('requirements', '')
        
        return f"""{core_identity}

## TASK AGENT SPECIALIZATION
You are specifically focused on task management operations including:
- Creating, updating, deleting, and completing tasks
- Managing task categories, priorities, and due dates
- Auto-enhancement of task details
- Task conflict resolution
- Category management and smart assignment

{action_schema}

{task_processing}

{context_memory}

{templates}

## REQUIREMENTS COMPLIANCE
{requirements}

## TASK AGENT BEHAVIOR
- ALWAYS load and use multiple relevant prompts for comprehensive decision making
- Apply auto-enhancement rules for missing task details
- Use structured response templates for task confirmations
- Integrate category management with every task operation
- Follow the complete action schema for all task operations"""

    async def process(self, user_input, context, routing_info=None):
        """Process task-related user input with comprehensive AI prompts.
        
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
        
        # NEW: Use comprehensive AI processing with multiple prompts
        return await self._process_with_comprehensive_prompts(user_input, enhanced_context, routing_info)
    
    async def _process_with_comprehensive_prompts(self, user_input, context, routing_info):
        """Process task with comprehensive prompt system."""
        user_id = context.get('user_id')
        assumptions = routing_info.get('assumptions', {}) if routing_info else {}
        
        # Extract task details with AI enhancement
        title = self._extract_title(user_input) or user_input.strip()
        category = assumptions.get('category') or self._extract_category(user_input) or 'general'
        priority = assumptions.get('priority') or self._extract_priority(user_input) or 'medium'
        due_date = self._extract_due_date(user_input)
        
        # Build comprehensive prompt using all relevant prompts
        system_prompt = self.comprehensive_prompts.get('core_system', 'You are a helpful task management agent.')
        
        # Include specific prompt sections for enhanced processing
        action_schema = self.comprehensive_prompts.get('action_schema', '')
        task_processing = self.comprehensive_prompts.get('task_processing', '')
        templates = self.comprehensive_prompts.get('templates', '')
        
        user_prompt = f"""
User Input: {user_input}
Context: {context}
Routing Info: {routing_info}

Task Details Extracted:
- Title: {title}
- Category: {category}
- Priority: {priority}
- Due Date: {due_date}

USING COMPREHENSIVE PROMPTS:
1. Follow the action schema for proper JSON response format
2. Apply task processing rules for auto-enhancement
3. Use structured templates for response formatting
4. Ensure category management compliance
5. Include all required actions in JSON format

Generate a comprehensive response following all prompt guidelines.
"""
        
        # Enhanced AI model call with comprehensive prompts
        full_prompt = f"{system_prompt}\n\nSPECIFIC GUIDANCE:\n{action_schema}\n{task_processing}\n{templates}\n\nUSER REQUEST:\n{user_prompt}"
        
        response = await self.ai_model.generate_content([
            full_prompt
        ])
        response_text = response.text
        
        # Create the task if this is a creation request
        if assumptions.get('operation') == 'create' or self._is_task_creation(user_input):
            task_id = await self._create_task_with_details(
                user_id, title, category, priority, due_date
            )
            
            return {
                "status": "success",
                "message": f"Task created successfully: {title}",
                "task_id": task_id,
                "actions": [{"agent": self.agent_name, "action": "task_created"}]
            }
        
        return {
            "status": "success", 
            "message": response_text,
            "actions": [{"agent": self.agent_name, "action": "task_processed"}]
        }
    
    def _apply_ai_assumptions(self, context, routing_info):
        """Apply AI assumptions to enhance the context"""
        enhanced_context = context.copy()
        if routing_info:
            enhanced_context.update(routing_info.get('assumptions', {}))
        return enhanced_context
    
    def _determine_operation(self, user_input):
        """Determine the task operation from the user input."""
        user_input_lower = user_input.lower()
        
        if any(phrase in user_input_lower for phrase in ['add task', 'create task', 'new task', 'remind me to']):
            return 'add'
        elif any(phrase in user_input_lower for phrase in ['update task', 'modify task', 'change task']):
            return 'update'
        elif any(phrase in user_input_lower for phrase in ['delete task', 'remove task', 'cancel task']):
            return 'delete'
        elif any(phrase in user_input_lower for phrase in ['complete task', 'finish task', 'done task']):
            return 'complete'
        elif any(phrase in user_input_lower for phrase in ['list tasks', 'show tasks', 'my tasks']):
            return 'list'
        else:
            return None
    
    def _is_task_creation(self, user_input):
        """Check if the input suggests task creation"""
        creation_indicators = ['need to', 'have to', 'must', 'should', 'remember to', 'don\'t forget']
        return any(indicator in user_input.lower() for indicator in creation_indicators)
    
    def _extract_title(self, user_input):
        """Extract task title from user input"""
        # Simple extraction - in real implementation would be more sophisticated
        return user_input.strip()
    
    def _extract_category(self, user_input):
        """Extract task category from user input"""
        categories = {
            'work': ['work', 'office', 'meeting', 'project', 'business'],
            'personal': ['personal', 'home', 'family', 'self'],
            'health': ['doctor', 'exercise', 'gym', 'health', 'medical'],
            'shopping': ['buy', 'purchase', 'shop', 'get', 'pick up']
        }
        
        user_input_lower = user_input.lower()
        for category, keywords in categories.items():
            if any(keyword in user_input_lower for keyword in keywords):
                return category
        return 'general'
    
    def _extract_priority(self, user_input):
        """Extract task priority from user input"""
        user_input_lower = user_input.lower()
        if any(word in user_input_lower for word in ['urgent', 'asap', 'immediately', 'critical']):
            return 'high'
        elif any(word in user_input_lower for word in ['low priority', 'sometime', 'eventually']):
            return 'low'
        return 'medium'
    
    def _extract_due_date(self, user_input):
        """Extract due date from user input"""
        # Simplified - would use more sophisticated date parsing in real implementation
        import re
        from datetime import datetime, timedelta
        
        user_input_lower = user_input.lower()
        
        if 'today' in user_input_lower:
            return datetime.now().date()
        elif 'tomorrow' in user_input_lower:
            return (datetime.now() + timedelta(days=1)).date()
        elif 'next week' in user_input_lower:
            return (datetime.now() + timedelta(days=7)).date()
        
        return None
    
    async def _create_task_with_details(self, user_id, title, category, priority, due_date):
        """Create a task with detailed information"""
        try:
            # Use the correct database function to create a task
            task_data = database_personal.add_task_entry(
                supabase=self.supabase,
                user_id=user_id,
                title=title,
                category=category,
                priority=priority,
                due_date=due_date.isoformat() if due_date else None
            )
            
            return task_data.get('id') if task_data else None
            
        except Exception as e:
            print(f"Error creating task: {e}")
            return None
    
    async def _add_task(self, user_id, user_input, context):
        """Add a new task"""
        title = self._extract_title(user_input)
        category = self._extract_category(user_input)
        priority = self._extract_priority(user_input)
        due_date = self._extract_due_date(user_input)
        
        task_id = await self._create_task_with_details(user_id, title, category, priority, due_date)
        
        if task_id:
            return {
                "status": "success",
                "message": f"Task added: {title}",
                "task_id": task_id
            }
        else:
            return {
                "status": "error",
                "message": "Failed to add task. Please try again."
            }
    
    async def _update_task(self, user_id, user_input, context):
        """Update an existing task"""
        return {
            "status": "info",
            "message": "Task update functionality would be implemented here."
        }
    
    async def _delete_task(self, user_id, user_input, context):
        """Delete a task"""
        return {
            "status": "info", 
            "message": "Task deletion functionality would be implemented here."
        }
    
    async def _complete_task(self, user_id, user_input, context):
        """Mark a task as complete"""
        return {
            "status": "info",
            "message": "Task completion functionality would be implemented here."
        }
    
    async def _list_tasks(self, user_id, user_input, context):
        """List user tasks"""
        return {
            "status": "info",
            "message": "Task listing functionality would be implemented here."
        }
    
    async def _smart_task_creation(self, user_id, user_input, context, assumptions):
        """Create task using AI assumptions"""
        return await self._add_task(user_id, user_input, context)
