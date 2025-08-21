from .base_agent import BaseAgent
import database_personal as database
import os

class TaskAgent(BaseAgent):
    """Agent for handling task-related operations with AI-enhanced processing."""
    
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model, agent_name="TaskAgent")
        self.comprehensive_prompts = {}
    
    def load_comprehensive_prompts(self):
        """Loads all prompts relative to the project's structure."""
        try:
            prompts_dict = {}
            # Use relative pathing to avoid hardcoded paths
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
            v1_dir = os.path.join(project_root, "prompts", "v1")
            
            if os.path.exists(v1_dir):
                for file_name in os.listdir(v1_dir):
                    if file_name.endswith('.md'):
                        prompt_name = file_name.replace('.md', '')
                        file_path = os.path.join(v1_dir, file_name)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            prompts_dict[prompt_name] = f.read()
            else:
                print(f"WARNING: Prompts directory not found at {v1_dir}")

            self.comprehensive_prompts = {
                'core_system': self._build_task_system_prompt(prompts_dict)
            }
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}

    def _build_task_system_prompt(self, prompts_dict):
        """Builds the system prompt for the Task agent."""
        core_identity = prompts_dict.get('00_core_identity', 'You are a helpful task manager.')
        task_processing = prompts_dict.get('02_task_processing', '')
        return f"{core_identity}\n\n{task_processing}"

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
        
        user_prompt = f"""
User Input: {user_input}
Context: {context}
Routing Info: {routing_info}

Task Details Extracted:
- Title: {title}
- Category: {category}
- Priority: {priority}
- Due Date: {due_date}

Generate a comprehensive response following all prompt guidelines.
"""
        
        # FIXED: Remove await from synchronous AI call
        response = self.ai_model.generate_content([system_prompt, user_prompt])
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
        
        # CRITICAL: Always return a message
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
    
    def _is_task_creation(self, user_input):
        """Check if the input suggests task creation"""
        creation_indicators = ['need to', 'have to', 'must', 'should', 'remember to', 'don\'t forget']
        return any(indicator in user_input.lower() for indicator in creation_indicators)
    
    def _extract_title(self, user_input):
        """Extract task title from user input"""
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
            # FIXED: Use the correct database function to create a task
            task_data = database.add_task_entry(
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
