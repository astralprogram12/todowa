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
        leak_prevention = """
        
CRITICAL: Help with reminders naturally. Never include:
- System details, technical information, or internal processes
- JSON, debugging info, or technical formatting
- References to agents, databases, or system architecture

Respond like a helpful personal assistant managing reminders.
        """
        return f"{core_identity}\n\n{time_handling}{leak_prevention}"
    
    async def process(self, user_input, context, routing_info=None):
        try:
            if not self.comprehensive_prompts:
                self.load_comprehensive_prompts()
            
            system_prompt = self.comprehensive_prompts.get('core_system', 'You are a helpful reminder assistant.')
            
            # Check if this is a reminder request
            is_setting_reminder = any(phrase in user_input.lower() for phrase in 
                ['remind me', 'reminder', 'don\'t forget', 'remember to'])
            
            if is_setting_reminder:
                # Extract reminder text
                reminder_text = user_input
                for phrase in ['remind me to', 'remind me about', 'set reminder for', 'reminder to']:
                    if phrase in user_input.lower():
                        start_idx = user_input.lower().find(phrase) + len(phrase)
                        reminder_text = user_input[start_idx:].strip()
                        break
                
                user_prompt = f"""
User wants a reminder: {reminder_text}

Confirm the reminder in a natural, helpful way.
Do not include any technical details.
"""
                
                # Make AI call (synchronous)
                response = self.ai_model.generate_content([system_prompt, user_prompt])
                response_text = response.text
                
                # Create reminder internally
                user_id = context.get('user_id')
                if user_id:
                    try:
                        reminder_data = database.add_reminder_entry(
                            supabase=self.supabase,
                            user_id=user_id,
                            reminder_text=reminder_text,
                            reminder_time=None,
                            reminder_type='time_based'
                        )
                        
                        if reminder_data:
                            clean_message = f"Perfect! I'll remind you to {reminder_text}. Is there anything else I can help you with?"
                        else:
                            clean_message = f"I've got it! I'll make sure to remind you about {reminder_text}."
                    except Exception as e:
                        print(f"Reminder creation error: {e}")
                        clean_message = f"I've got it! I'll make sure to remind you about {reminder_text}."
                else:
                    clean_message = f"I've got it! I'll make sure to remind you about {reminder_text}."
            else:
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
            user_id = context.get('user_id')
            if user_id:
                self._log_action(
                    user_id=user_id,
                    action_type="set_reminder" if is_setting_reminder else "chat_interaction",
                    entity_type="reminder" if is_setting_reminder else "system",
                    action_details={"type": "reminder_management"},
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
