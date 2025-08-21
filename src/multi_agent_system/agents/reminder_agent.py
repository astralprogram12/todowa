from .base_agent import BaseAgent
import database_personal as database  # Step 1: Fix the imports
import os

class ReminderAgent(BaseAgent):
    """Agent for handling reminder-related operations."""
    
    def __init__(self, supabase, ai_model):  # Step 2: Fix constructor
        super().__init__(supabase, ai_model, agent_name="ReminderAgent")
        self.comprehensive_prompts = {}
    
    def load_comprehensive_prompts(self):  # Step 3: Fix prompt loading logic
        """Loads all prompts relative to the project's structure."""
        try:
            prompts_dict = {}
            # This code correctly finds your prompts folder
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

            # This part can be customized for each agent
            self.comprehensive_prompts = {
                'core_system': self._build_reminder_system_prompt(prompts_dict)
            }
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}
    
    def _build_reminder_system_prompt(self, prompts_dict):  # Customize this helper for each agent
        """Builds the system prompt for the Reminder agent."""
        core_identity = prompts_dict.get('00_core_identity', 'You are a helpful reminder manager.')
        time_handling = prompts_dict.get('06_time_handling', '')
        return f"{core_identity}\n\n{time_handling}"
    
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
        
        # Load comprehensive prompts
        if not self.comprehensive_prompts:
            self.load_comprehensive_prompts()  # NO 'await' here
        
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
    
    def _apply_ai_assumptions(self, context, routing_info):
        """Apply AI assumptions to enhance the context"""
        enhanced_context = context.copy()
        if routing_info:
            enhanced_context.update(routing_info.get('assumptions', {}))
        return enhanced_context
    
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
        reminder_text = assumptions.get('reminder_text') or self._extract_reminder_text(user_input)
        reminder_time = assumptions.get('reminder_time') or self._extract_reminder_time(user_input)
        reminder_type = assumptions.get('reminder_type', 'time_based')  # time_based or location_based
        
        # Get system prompt from comprehensive prompts
        system_prompt = self.comprehensive_prompts.get('core_system', "You are a helpful reminder agent.")
        
        user_prompt = f"""
User Input: {user_input}
Context: {context}

Set up a reminder based on this input. The AI has provided these assumptions:
- Reminder text: {reminder_text}
- Reminder time: {reminder_time}
- Reminder type: {reminder_type}

Generate an appropriate response and reminder creation plan.
"""
        
        # Step 4: Fix AI model call with await
        response = await self.ai_model.generate_content([system_prompt, user_prompt])
        response_text = response.text
        
        # Create the reminder (and auto-create task if needed)
        reminder_result = await self._create_reminder_with_details(
            user_id, reminder_text, reminder_time, reminder_type
        )
        
        if reminder_result and reminder_result.get('id'):
            message = f"Reminder set: {reminder_text}"
            
            # Add task creation info if a task was auto-created
            if reminder_result.get('task_auto_created'):
                task_info = reminder_result.get('auto_created_task', {})
                message += f"\n✅ I also created a task '{task_info.get('title')}' to help you track this."
            
            return {
                "status": "success",
                "message": message,
                "reminder_id": reminder_result.get('id'),
                "reminder_time": reminder_time,
                "task_auto_created": reminder_result.get('task_auto_created', False),
                "actions": [{"agent": self.agent_name, "action": "reminder_created"}]
            }
        else:
            return {
                "status": "error",
                "message": "Failed to create reminder. Please try again.",
                "actions": [{"agent": self.agent_name, "action": "reminder_failed"}]
            }
    
    async def _set_reminder(self, user_id, user_input, context):
        """Set a new reminder"""
        try:
            reminder_text = self._extract_reminder_text(user_input)
            reminder_time = self._extract_reminder_time(user_input)
            reminder_type = self._determine_reminder_type(user_input)
            
            if not reminder_text:
                return {
                    "status": "error",
                    "message": "I couldn't determine what to remind you about. Please be more specific."
                }
            
            # Create reminder (and auto-create task if needed)
            reminder_result = await self._create_reminder_with_details(
                user_id, reminder_text, reminder_time, reminder_type
            )
            
            if reminder_result and reminder_result.get('id'):
                time_info = f" at {reminder_time}" if reminder_time else ""
                return {
                    "status": "success",
                    "message": f"Reminder set: {reminder_text}{time_info}",
                    "reminder_id": reminder_result.get('id')
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to create reminder. Please try again."
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error creating reminder: {str(e)}"
            }
    
    async def _create_reminder_with_details(self, user_id, reminder_text, reminder_time, reminder_type):
        """Create a reminder with detailed information"""
        try:
            # Step 5: Use the correct database function to create a reminder
            reminder_data = database.add_reminder_entry(
                supabase=self.supabase,
                user_id=user_id,
                reminder_text=reminder_text,
                reminder_time=reminder_time,
                reminder_type=reminder_type
            )
            
            return reminder_data if reminder_data else None
            
        except Exception as e:
            print(f"Error creating reminder: {e}")
            return None
    
    def _extract_reminder_text(self, user_input):
        """Extract reminder text from user input"""
        # Simple extraction - remove common reminder phrases
        text = user_input.lower()
        for phrase in ['remind me to', 'remind me about', 'set reminder for', 'reminder to']:
            if phrase in text:
                return user_input[text.find(phrase) + len(phrase):].strip()
        return user_input.strip()
    
    def _extract_reminder_time(self, user_input):
        """Extract reminder time from user input"""
        # Simplified time extraction
        from datetime import datetime, timedelta
        
        user_input_lower = user_input.lower()
        
        if 'tomorrow' in user_input_lower:
            return (datetime.now() + timedelta(days=1)).isoformat()
        elif 'next week' in user_input_lower:
            return (datetime.now() + timedelta(days=7)).isoformat()
        
        return None
    
    def _determine_reminder_type(self, user_input):
        """Determine reminder type from user input"""
        return 'time_based'  # Default to time-based reminders
    
    async def _update_reminder(self, user_id, user_input, context):
        """Update an existing reminder"""
        return {
            "status": "info",
            "message": "Reminder update functionality would be implemented here."
        }
    
    async def _delete_reminder(self, user_id, user_input, context):
        """Delete a reminder"""
        return {
            "status": "info", 
            "message": "Reminder deletion functionality would be implemented here."
        }
    
    async def _list_reminders(self, user_id, user_input, context):
        """List user reminders"""
        return {
            "status": "info",
            "message": "Reminder listing functionality would be implemented here."
        }
