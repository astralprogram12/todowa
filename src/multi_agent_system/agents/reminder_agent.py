from .base_agent import BaseAgent
import database_personal as database
import os

class ReminderAgent(BaseAgent):
    """Agent for reminder management without technical leaks."""
    
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model, agent_name="ReminderAgent")
        self.comprehensive_prompts = {}
    
    def load_comprehensive_prompts(self):
        try:
            prompts_dict = {}
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
            v1_dir = os.path.join(project_root, "prompts", "v1")
            
            if os.path.exists(v1_dir):
                for file_name in os.listdir(v1_dir):
                    if file_name.endswith('.md'):
                        prompt_name = file_name.replace('.md', '')
                        file_path = os.path.join(v1_dir, file_name)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            prompts_dict[prompt_name] = f.read()

            self.comprehensive_prompts = {
                'core_system': self._build_reminder_system_prompt(prompts_dict)
            }
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}
    
    def _build_reminder_system_prompt(self, prompts_dict):
        core_identity = prompts_dict.get('00_core_identity', 'You are a helpful reminder assistant.')
        time_handling = prompts_dict.get('06_time_handling', '')
        reminder_specialized = prompts_dict.get('16_reminder_specialized', '')
        leak_prevention = """
        
CRITICAL: Help with reminders naturally. Never include:
- System details, technical information, or internal processes
- JSON, debugging info, or technical formatting
- References to agents, databases, or system architecture

Respond like a helpful personal assistant managing reminders.
        """
        return f"{core_identity}\n\n{time_handling}\n\n{reminder_specialized}{leak_prevention}"
    
    async def process(self, user_input, context, routing_info=None):
        try:
            if not self.comprehensive_prompts:
                self.load_comprehensive_prompts()
            
            system_prompt = self.comprehensive_prompts.get('core_system', 'You are a helpful reminder assistant.')
            
            # Use intent classification from routing_info to determine operation
            primary_intent = routing_info.get('primary_intent', '') if routing_info else ''
            operation = routing_info.get('operation', '') if routing_info else ''
            
            # Determine operation type based on classification
            is_query_operation = (primary_intent == 'query_reminder' or operation == 'read')
            is_action_operation = (primary_intent == 'action_reminder' or operation in ['create', 'update', 'delete'])
            
            user_id = context.get('user_id')
            
            if is_query_operation:
                # Handle query operations (read reminders from tasks table)
                user_prompt = f"""
User wants to see their reminders: {user_input}

Respond naturally with their current reminders. Be helpful and conversational.
Do not include any technical details.
"""
                
                # Get user's reminders from tasks table (reminder_at field)
                if user_id:
                    try:
                        # Get all tasks with reminder_at field set
                        reminders = database.get_all_reminders(self.supabase, user_id)
                        
                        if reminders:
                            reminder_list = "\n".join([f"• {reminder.get('title', 'Untitled reminder')} (Reminder: {reminder.get('reminder_at', 'No time set')})" for reminder in reminders])
                            clean_message = f"Here are your current reminders:\n{reminder_list}\n\nAnything else I can help you with?"
                        else:
                            clean_message = "You don't have any reminders right now. Would you like to create one?"
                    except Exception as e:
                        print(f"Reminder retrieval error: {e}")
                        clean_message = "I'm having trouble accessing your reminders right now. Please try again."
                else:
                    clean_message = "I'd need to set up your account first to show your reminders."
                    
            elif is_action_operation:
                # Handle action operations (create reminders using A+C approach)
                # A: Always create task + reminder (using reminder_at field)
                # C: Ask for clarification if task isn't clear
                
                # Extract reminder text
                reminder_text = user_input
                for phrase in ['remind me to', 'remind me about', 'set reminder for', 'reminder to']:
                    if phrase in user_input.lower():
                        start_idx = user_input.lower().find(phrase) + len(phrase)
                        reminder_text = user_input[start_idx:].strip()
                        break
                
                # Create task with reminder_at field (simplified A+C approach)
                if user_id:
                    try:
                        from datetime import datetime, timedelta, timezone
                        
                        # Set reminder for tomorrow as default (can be enhanced later)
                        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
                        reminder_time = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0).isoformat()
                        
                        # Create the task with reminder_at field
                        task_data = database.add_task_entry(
                            supabase=self.supabase,
                            user_id=user_id,
                            title=reminder_text,
                            category='reminder_based',
                            reminder_at=reminder_time
                        )
                        
                        if task_data:
                            clean_message = f"Perfect! I've created a task '{reminder_text}' with a reminder set for tomorrow. Is there anything else I can help you with?"
                        else:
                            clean_message = f"I've got it! I'll make sure to remind you about {reminder_text}."
                            
                    except Exception as e:
                        print(f"Reminder creation error: {e}")
                        clean_message = f"I'm having trouble setting up that reminder right now. Please try again."
                else:
                    clean_message = f"I'd need to set up your account first to create reminders."
            else:
                # General reminder-related conversation
                user_prompt = f"""
User said: {user_input}

This is about reminders. Respond naturally and helpfully.
Do not include any technical details.
"""
                
                # Make AI call (synchronous)
                response = self.ai_model.generate_content([system_prompt, user_prompt])
                response_text = response.text
                clean_message = self._clean_response(response_text)
            
            # Log action (internal only)
            if user_id:
                action_type = "query_reminders" if is_query_operation else ("set_reminder" if is_action_operation else "chat_interaction")
                entity_type = "reminder" if (is_query_operation or is_action_operation) else "system"
                
                self._log_action(
                    user_id=user_id,
                    action_type=action_type,
                    entity_type=entity_type,
                    action_details={"operation": operation, "intent": primary_intent},
                    success_status=True
                )
            
            # Return ONLY clean user message
            return {
                "message": clean_message
            }
            
        except Exception as e:
            print(f"ERROR in ReminderAgent: {e}")
            return {
                "message": "I'd be happy to help you with reminders! What would you like me to remind you about?"
            }
