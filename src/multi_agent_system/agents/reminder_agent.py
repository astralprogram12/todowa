from .base_agent import BaseAgent
import database_personal  # Fix #4: Proper database import
import os

class ReminderAgent(BaseAgent):
    """Agent for handling reminder-related operations."""
    
    def __init__(self, supabase, ai_model):  # Fix #1: Correct constructor
        super().__init__(supabase, ai_model, "ReminderAgent")
        self.comprehensive_prompts = {}
    
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
            self.load_comprehensive_prompts()
        
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
            
            # Create comprehensive system prompt for reminder agent
            self.comprehensive_prompts = {
                'core_system': self._build_reminder_system_prompt(prompts_dict),
                'core_identity': prompts_dict.get('00_core_identity', ''),
                'time_handling': prompts_dict.get('06_time_handling', ''),
                'templates': prompts_dict.get('08_templates', ''),
                'context_memory': prompts_dict.get('03_context_memory', ''),
                'requirements': prompts_dict.get('requirements', ''),
                'all_prompts': prompts_dict
            }
            
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}
    
    def _build_reminder_system_prompt(self, prompts_dict):
        """Build comprehensive system prompt for reminder agent."""
        core_identity = prompts_dict.get('00_core_identity', '')
        time_handling = prompts_dict.get('06_time_handling', '')
        templates = prompts_dict.get('08_templates', '')
        context_memory = prompts_dict.get('03_context_memory', '')
        requirements = prompts_dict.get('requirements', '')
        
        return f"""{core_identity}

## REMINDER AGENT SPECIALIZATION
You are specifically focused on reminder management:
- Creating time-based and event-based reminders
- Parsing natural language time expressions
- Managing reminder updates, deletions, and listings
- Understanding complex scheduling requirements
- Providing clear confirmation of reminder settings

{time_handling}

{templates}

{context_memory}

## REQUIREMENTS COMPLIANCE
{requirements}

## REMINDER AGENT BEHAVIOR
- ALWAYS apply time handling rules for accurate parsing
- Use structured templates for reminder confirmations
- Apply context memory for reminder history and patterns
- Follow comprehensive prompt system for enhanced reminder processing"""
    
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
        
        # Fix #2: Correct AI model call with array parameter
        response = await self.ai_model.generate_content([
            system_prompt, user_prompt
        ])
        response_text = response.text
        
        # Create the reminder
        reminder_id = await self._create_reminder_with_details(
            user_id, reminder_text, reminder_time, reminder_type
        )
        
        if reminder_id:
            return {
                "status": "success",
                "message": f"Reminder set: {reminder_text}",
                "reminder_id": reminder_id,
                "reminder_time": reminder_time,
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
            
            reminder_id = await self._create_reminder_with_details(
                user_id, reminder_text, reminder_time, reminder_type
            )
            
            if reminder_id:
                time_info = f" at {reminder_time}" if reminder_time else ""
                return {
                    "status": "success",
                    "message": f"Reminder set{time_info}: {reminder_text}",
                    "reminder_id": reminder_id
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to set reminder. Please try again."
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error setting reminder: {str(e)}"
            }
    
    async def _update_reminder(self, user_id, user_input, context):
        """Update an existing reminder"""
        return {
            "status": "info",
            "message": "Reminder update functionality would be implemented here."
        }
    
    async def _delete_reminder(self, user_id, user_input, context):
        """Delete a reminder"""
        try:
            reminder_text = self._extract_reminder_text(user_input)
            
            # Delete reminder using correct database function
            result = database_personal.delete_reminder(
                supabase=self.supabase,
                user_id=user_id,
                reminder_text=reminder_text
            )
            
            if result:
                return {
                    "status": "success",
                    "message": f"Reminder cancelled: {reminder_text}"
                }
            else:
                return {
                    "status": "error",
                    "message": "Couldn't find or cancel that reminder."
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error cancelling reminder: {str(e)}"
            }
    
    async def _list_reminders(self, user_id, user_input, context):
        """List user reminders"""
        try:
            # Get reminders using correct database function
            reminders = database_personal.get_user_reminders(
                supabase=self.supabase,
                user_id=user_id
            )
            
            if reminders:
                reminder_list = []
                for reminder in reminders:
                    reminder_info = {
                        'text': reminder.get('reminder_text', ''),
                        'time': reminder.get('reminder_time', ''),
                        'type': reminder.get('reminder_type', 'time_based')
                    }
                    reminder_list.append(reminder_info)
                
                return {
                    "status": "success",
                    "message": "Here are your upcoming reminders:",
                    "reminders": reminder_list
                }
            else:
                return {
                    "status": "success",
                    "message": "You don't have any active reminders."
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error retrieving reminders: {str(e)}"
            }
    
    async def _create_reminder_with_details(self, user_id, reminder_text, reminder_time, reminder_type):
        """Create a reminder with detailed information"""
        try:
            # Use the correct database function to create a reminder
            reminder_data = database_personal.add_reminder(
                supabase=self.supabase,
                user_id=user_id,
                reminder_text=reminder_text,
                reminder_time=reminder_time,
                reminder_type=reminder_type
            )
            
            # Log the reminder creation
            database_personal.log_action(
                supabase=self.supabase,
                user_id=user_id,
                action_type="reminder_created",
                entity_type="reminder",
                action_details={
                    "reminder_text": reminder_text,
                    "reminder_time": str(reminder_time) if reminder_time else None,
                    "reminder_type": reminder_type
                },
                success_status=True
            )
            
            return reminder_data.get('id') if reminder_data else None
            
        except Exception as e:
            print(f"Error creating reminder: {e}")
            return None
    
    def _extract_reminder_text(self, user_input):
        """Extract the reminder text from user input"""
        # Remove common reminder trigger phrases
        text = user_input.lower()
        remove_phrases = [
            'remind me to', 'remind me about', 'set reminder for', 
            'add reminder', 'create reminder', 'remember to'
        ]
        
        for phrase in remove_phrases:
            if phrase in text:
                text = text.replace(phrase, '', 1).strip()
                break
        
        return text or user_input
    
    def _extract_reminder_time(self, user_input):
        """Extract reminder time from user input"""
        import re
        from datetime import datetime, timedelta
        
        user_input_lower = user_input.lower()
        
        # Handle relative times
        if 'in' in user_input_lower:
            # "in 30 minutes", "in 2 hours", etc.
            time_match = re.search(r'in (\d+) (minute|hour|day)s?', user_input_lower)
            if time_match:
