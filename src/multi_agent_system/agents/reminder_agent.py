from .base_agent import BaseAgent
import database_personal as database
import os
import re
from datetime import datetime, timedelta, timezone

class ReminderAgent(BaseAgent):
    """Enhanced Agent for reminder management with accurate time parsing for version 3.5."""
    
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
    
    async def extract_task_description(self, user_input):
        """
        Use AI to extract only the essential task description from user input.
        For example, from "remind me to eat in 5 minutes", extract just "eat"
        """
        system_prompt = """You are a task extraction expert. Extract ONLY the core task from the user's input.
        DO NOT include time expressions, prepositions, or unnecessary context.
        Return ONLY the core task/action phrase - nothing else.
        
        Examples:
        "remind me to buy groceries tomorrow" → "buy groceries"
        "I need to call mom at 5pm" → "call mom"
        "Please create a task to finish report by Friday" → "finish report"
        "Add a reminder to eat in 10 minutes" → "eat"
        """
        
        user_prompt = f"Extract the core task from: {user_input}"
        
        try:
            response = self.ai_model.generate_content([system_prompt, user_prompt])
            return response.text.strip()
        except Exception as e:
            print(f"Error extracting task: {e}")
            # Fallback to simple extraction if AI fails
            for phrase in ['remind me to', 'remind me about', 'set reminder for', 'reminder to', 'task to']:
                if phrase in user_input.lower():
                    return user_input[user_input.lower().find(phrase) + len(phrase):].strip()
            return user_input
    
    def parse_reminder_time(self, user_input):
        """
        Parse time expressions from user input like "in 5 minutes", "tomorrow at 3pm", etc.
        Enhanced for v3.5 to handle abbreviations like "10m" for 10 minutes.
        Returns a datetime object and a description of the time.
        """
        now = datetime.now(timezone.utc)
        user_input_lower = user_input.lower()
        
        # Check for "in X minutes/m/min" - enhanced to catch abbreviations
        minute_match = re.search(r'in\s*(\d+)\s*m(in(ute)?s?)?\b', user_input_lower)
        if minute_match:
            minutes = int(minute_match.group(1))
            reminder_time = now + timedelta(minutes=minutes)
            time_description = f"in {minutes} minute{'s' if minutes > 1 else ''}"
            return reminder_time, time_description
            
        # Check for "in X hours/h/hr" - enhanced to catch abbreviations
        hour_match = re.search(r'in\s*(\d+)\s*h(our)?s?\b', user_input_lower)
        if hour_match:
            hours = int(hour_match.group(1))
            reminder_time = now + timedelta(hours=hours)
            time_description = f"in {hours} hour{'s' if hours > 1 else ''}"
            return reminder_time, time_description
        
        # Check for "in X days/d" - enhanced to catch abbreviations
        day_match = re.search(r'in\s*(\d+)\s*d(ay)?s?\b', user_input_lower)
        if day_match:
            days = int(day_match.group(1))
            reminder_time = now + timedelta(days=days)
            time_description = f"in {days} day{'s' if days > 1 else ''}"
            return reminder_time, time_description
        
        # Check for "today at X" (assume PM for ambiguous times 1-7)
        today_match = re.search(r'today\s+at\s+(\d+)(:\d+)?\s*(am|pm)?', user_input_lower)
        if today_match:
            hour = int(today_match.group(1))
            minute_str = today_match.group(2)
            am_pm = today_match.group(3)
            
            # Handle AM/PM
            if am_pm == 'pm' and hour < 12:
                hour += 12
            elif am_pm != 'am' and 1 <= hour <= 7:  # Assume PM for ambiguous times 1-7
                hour += 12
                
            minute = 0
            if minute_str:
                minute = int(minute_str.replace(':', ''))
                
            reminder_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            # If the time has already passed today, use tomorrow
            if reminder_time < now:
                reminder_time = reminder_time + timedelta(days=1)
                
            time_description = f"at {hour % 12 or 12}:{minute:02d} {'PM' if hour >= 12 else 'AM'}"
            return reminder_time, time_description
        
        # Check for "tomorrow at X"
        tomorrow_match = re.search(r'tomorrow\s+at\s+(\d+)(:\d+)?\s*(am|pm)?', user_input_lower)
        if tomorrow_match:
            hour = int(tomorrow_match.group(1))
            minute_str = tomorrow_match.group(2)
            am_pm = tomorrow_match.group(3)
            
            # Handle AM/PM
            if am_pm == 'pm' and hour < 12:
                hour += 12
            elif am_pm != 'am' and 1 <= hour <= 7:  # Assume PM for ambiguous times 1-7
                hour += 12
                
            minute = 0
            if minute_str:
                minute = int(minute_str.replace(':', ''))
                
            tomorrow = now + timedelta(days=1)
            reminder_time = tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
            time_description = f"tomorrow at {hour % 12 or 12}:{minute:02d} {'PM' if hour >= 12 else 'AM'}"
            return reminder_time, time_description
        
        # Check for standalone time (10m, 30m, 1h)
        standalone_time_match = re.search(r'\b(\d+)\s*([mh])\b', user_input_lower)
        if standalone_time_match:
            value = int(standalone_time_match.group(1))
            unit = standalone_time_match.group(2)
            
            if unit == 'm':
                reminder_time = now + timedelta(minutes=value)
                time_description = f"in {value} minute{'s' if value > 1 else ''}"
            elif unit == 'h':
                reminder_time = now + timedelta(hours=value)
                time_description = f"in {value} hour{'s' if value > 1 else ''}"
            
            return reminder_time, time_description
        
        # Default: Set for tomorrow morning at 9 AM
        tomorrow = now + timedelta(days=1)
        reminder_time = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
        time_description = "tomorrow at 9:00 AM"
        return reminder_time, time_description
        
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
{self._get_conversation_history(context)}

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
                # Extract clean task description using AI
                task_description = await self.extract_task_description(user_input)
                
                # Parse the reminder time using the enhanced time parsing
                reminder_time, time_description = self.parse_reminder_time(user_input)
                reminder_time_iso = reminder_time.isoformat()
                
                # Create task with reminder_at field
                if user_id:
                    try:
                        # Create the task with reminder_at field
                        task_data = database.add_task_entry(
                            supabase=self.supabase,
                            user_id=user_id,
                            title=task_description,  # Use the clean task description
                            category='reminder_based',
                            reminder_at=reminder_time_iso
                        )
                        
                        # Determine if this is an important task that needs follow-up
                        task_importance_system = """You are a task importance analyzer. Determine if the given task is important enough to offer additional assistance.
                        Rate the task from 1-5, where 1 is routine (eating, drinking water) and 5 is critical (urgent meeting, important deadline).
                        Return ONLY the number."""
                        
                        task_importance_prompt = f"Rate the importance of this task: {task_description}"
                        
                        try:
                            importance_response = self.ai_model.generate_content([task_importance_system, task_importance_prompt])
                            importance_rating = int(importance_response.text.strip())
                        except:
                            importance_rating = 3  # Default to medium importance
                        
                        # For important tasks (4-5), provide a different response style
                        if importance_rating >= 4:
                            clean_message = f"I've set a reminder for '{task_description}' {time_description}. Would you like me to help you prepare for this or set any additional reminders?"
                        else:
                            # For routine tasks, keep it simple
                            clean_message = f"Got it! I'll remind you about '{task_description}' {time_description}."
                            
                    except Exception as e:
                        print(f"Reminder creation error: {e}")
                        clean_message = f"I'm having trouble setting up that reminder right now. Please try again."
                else:
                    clean_message = f"I'd need to set up your account first to create reminders."
            else:
                # General reminder-related conversation
                user_prompt = f"""
{self._get_conversation_history(context)}

User said: {user_input}

This is about reminders. Respond naturally and helpfully.
Do not include any technical details.
"""
                
                # Make AI call (synchronous)
                response = self.ai_model.generate_content([system_prompt, user_prompt])
                response_text = response.text
                clean_message = self._clean_response(response_text)
            
            # Update conversation memory
            self._update_conversation_memory(context, user_input, clean_message)
            
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
