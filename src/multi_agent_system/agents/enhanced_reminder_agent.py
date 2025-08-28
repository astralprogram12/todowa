from .base_agent import BaseAgent
import database_personal as database
import os
from datetime import datetime, timezone, timedelta

class EnhancedReminderAgent(BaseAgent):
    """Enhanced AI-powered reminder agent with multilingual support and advanced time parsing."""
    
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model, agent_name="EnhancedReminderAgent")
        self.comprehensive_prompts = {}
        self._initialize_ai_processors()
    
    def _initialize_ai_processors(self):
        """Initialize AI processors for translation and time parsing."""
        try:
            # Import AI processors with correct class names
            import sys
            current_dir = os.path.dirname(os.path.abspath(__file__))
            processors_path = os.path.join(current_dir, '..', '..', 'ai_text_processors')
            sys.path.insert(0, processors_path)
            
            from translation_agent import TranslationAgent
            from ai_time_parser import AITimeParser
            
            self.translation_agent = TranslationAgent()
            self.time_parser = AITimeParser()
            
            print("✅ Enhanced Reminder Agent: AI processors initialized successfully")
        except Exception as e:
            print(f"⚠️ Enhanced Reminder Agent: Could not initialize AI processors: {e}")
            # Fallback to None - will be handled gracefully
            self.translation_agent = None
            self.time_parser = None
    
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
                'core_system': self._build_enhanced_reminder_system_prompt(prompts_dict)
            }
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}
    
    def _build_enhanced_reminder_system_prompt(self, prompts_dict):
        core_identity = prompts_dict.get('00_core_identity', 'You are a helpful multilingual reminder assistant.')
        time_handling = prompts_dict.get('06_time_handling', '')
        reminder_specialized = prompts_dict.get('16_reminder_specialized', '')
        
        enhanced_prompt = f"""{core_identity}

{time_handling}

{reminder_specialized}

## ENHANCED AI-POWERED MULTILINGUAL CAPABILITIES

You are now equipped with advanced AI capabilities:

### Multilingual Understanding
- Automatically detect and understand text in Indonesian, Spanish, French, English, and other languages
- Parse time expressions naturally in any language:
  - Indonesian: "ingetin 5 menit lagi buang sampah" = "remind me in 5 minutes to take out trash"
  - Spanish: "recuérdame en 10 minutos" = "remind me in 10 minutes"
  - French: "rappelle-moi dans une heure" = "remind me in 1 hour"
  - English: "remind me in 5 mins to eat" = "remind me in 5 minutes to eat"

### Advanced Time Parsing
- Use AI natural language understanding instead of regex patterns
- Handle relative times accurately: "5 menit lagi" = exactly 5 minutes from current time
- Parse absolute times: "tomorrow at 3pm", "Friday morning"
- Handle informal expressions: "in a few mins", "later today"
- Provide confidence scores for time interpretation

### Context-Aware Task Extraction
- Extract meaningful task descriptions from multilingual input
- Preserve user intent and context during translation
- Handle typos and colloquialisms naturally

### Response Guidelines
- Always confirm the parsed time in user-friendly language
- Show confidence in your understanding
- Ask for clarification only when truly ambiguous
- Respond naturally without technical jargon

CRITICAL: Never include system details, technical information, or debugging output.
Respond like a helpful personal assistant managing reminders.
"""
        
        return enhanced_prompt
    
    async def process(self, user_input, context, routing_info=None):
        try:
            if not self.comprehensive_prompts:
                self.load_comprehensive_prompts()
            
            system_prompt = self.comprehensive_prompts.get('core_system', 'You are a helpful reminder assistant.')
            
            # Get user context
            user_id = context.get('user_id')
            current_time = datetime.now(timezone.utc)
            user_timezone = context.get('timezone', 'UTC')
            
            # Determine operation type based on routing info
            primary_intent = routing_info.get('primary_intent', '') if routing_info else ''
            operation = routing_info.get('operation', '') if routing_info else ''
            
            is_query_operation = (primary_intent == 'query_reminder' or operation == 'read')
            is_action_operation = (primary_intent == 'action_reminder' or operation in ['create', 'update', 'delete'])
            
            if is_query_operation:
                # Handle query operations (show existing reminders)
                return await self._handle_reminder_query(user_input, user_id)
                
            elif is_action_operation:
                # Handle action operations (create/update/delete reminders)
                return await self._handle_reminder_action(user_input, user_id, current_time, user_timezone, context)
                
            else:
                # General reminder conversation
                return await self._handle_reminder_conversation(user_input, system_prompt)
                
        except Exception as e:
            print(f"ERROR in EnhancedReminderAgent: {e}")
            return {
                "message": "I'd be happy to help you with reminders! What would you like me to remind you about?"
            }
    
    async def _handle_reminder_query(self, user_input, user_id):
        """Handle reminder query operations."""
        if user_id:
            try:
                reminders = database.get_all_reminders(self.supabase, user_id)
                
                if reminders:
                    reminder_list = "\n".join([
                        f"• {reminder.get('title', 'Untitled reminder')} (Reminder: {reminder.get('reminder_at', 'No time set')})"
                        for reminder in reminders
                    ])
                    clean_message = f"Here are your current reminders:\n{reminder_list}\n\nAnything else I can help you with?"
                else:
                    clean_message = "You don't have any reminders right now. Would you like to create one?"
                    
            except Exception as e:
                print(f"Reminder retrieval error: {e}")
                clean_message = "I'm having trouble accessing your reminders right now. Please try again."
        else:
            clean_message = "I'd need to set up your account first to show your reminders."
            
        return {"message": clean_message}
    
    async def _handle_reminder_action(self, user_input, user_id, current_time, user_timezone, context):
        """Handle reminder creation/update/delete operations using AI parsing."""
        if not user_id:
            return {"message": "I'd need to set up your account first to create reminders."}
        
        # ✅ CRITICAL FIX: Use the AI-parsed time analysis from orchestrator context
        time_analysis = context.get('time_analysis', {})
        
        print(f"🔍 Enhanced Reminder Agent: Using time analysis from context: {time_analysis}")
        
        # Extract time and task from AI analysis
        has_time = time_analysis.get('has_time_expression', False)
        parsed_datetime = None
        task_description = time_analysis.get('task_description', '')
        confidence = time_analysis.get('confidence', 0.0)
        
        if has_time and confidence > 0.5:
            # Use the AI-parsed datetime
            parsed_datetime_str = time_analysis.get('parsed_datetime_utc')
            if parsed_datetime_str:
                try:
                    # Parse the ISO format datetime from AI
                    parsed_datetime = datetime.fromisoformat(parsed_datetime_str.replace('Z', '+00:00'))
                    print(f"✅ Enhanced Reminder Agent: Using AI-parsed time: {parsed_datetime}")
                except Exception as e:
                    print(f"⚠️ Enhanced Reminder Agent: Error parsing AI datetime: {e}")
                    parsed_datetime = None
        
        # Fallback: Extract task description from user input if not found in AI analysis
        if not task_description:
            task_description = self._extract_task_description(user_input)
        
        # Fallback: Use our own AI time parser if orchestrator analysis failed
        if not parsed_datetime and self.time_parser:
            try:
                print(f"🔄 Enhanced Reminder Agent: Fallback to own AI time parser")
                fallback_analysis = self.time_parser.parse_time_expression(user_input, current_time)
                if fallback_analysis.get('has_time_expression') and fallback_analysis.get('confidence', 0) > 0.5:
                    parsed_datetime_str = fallback_analysis.get('parsed_datetime_utc')
                    if parsed_datetime_str:
                        parsed_datetime = datetime.fromisoformat(parsed_datetime_str.replace('Z', '+00:00'))
                        task_description = fallback_analysis.get('task_description', task_description)
                        print(f"✅ Enhanced Reminder Agent: Fallback AI parsing successful: {parsed_datetime}")
            except Exception as e:
                print(f"⚠️ Enhanced Reminder Agent: Fallback AI parsing error: {e}")
        
        # Final fallback: Default time if no parsing worked
        if not parsed_datetime:
            print(f"⚠️ Enhanced Reminder Agent: No valid time parsed, using default (15 minutes)")
            parsed_datetime = current_time + timedelta(minutes=15)
            task_description = user_input.strip()
        
        # Ensure we have a task description
        if not task_description:
            task_description = "Reminder"
        
        try:
            # Create the reminder in database
            task_data = {
                'title': task_description,
                'reminder_at': parsed_datetime.isoformat(),
                'description': f"Reminder: {task_description}",
                'priority': 'medium',
                'status': 'pending'
            }
            
            result = database.create_task_with_reminder(self.supabase, user_id, task_data)
            
            if result:
                # Format user-friendly time
                time_diff = parsed_datetime - current_time
                if time_diff.total_seconds() < 3600:  # Less than 1 hour
                    minutes = int(time_diff.total_seconds() / 60)
                    time_description = f"in {minutes} minute{'s' if minutes != 1 else ''}"
                elif time_diff.total_seconds() < 86400:  # Less than 1 day
                    hours = int(time_diff.total_seconds() / 3600)
                    time_description = f"in {hours} hour{'s' if hours != 1 else ''}"
                else:
                    time_description = f"on {parsed_datetime.strftime('%B %d at %I:%M %p')}"
                
                success_message = f"Perfect! I'll remind you about '{task_description}' {time_description}."
                print(f"✅ Enhanced Reminder Agent: Created reminder - {success_message}")
                
                return {
                    "message": success_message,
                    "status": "success",
                    "actions": [{
                        "type": "reminder_created",
                        "task": task_description,
                        "reminder_time": parsed_datetime.isoformat(),
                        "user_friendly_time": time_description
                    }]
                }
            else:
                return {"message": "I had trouble creating that reminder. Please try again."}
                
        except Exception as e:
            print(f"⚠️ Enhanced Reminder Agent: Database error: {e}")
            return {"message": "I had trouble saving that reminder. Please try again."}
    
    def _extract_task_description(self, user_input):
        """Extract task description from user input."""
        # Remove common reminder phrases
        task = user_input.lower()
        
        # Indonesian patterns
        for pattern in ['ingetin saya untuk', 'ingetin saya', 'ingetin', 'ingatin']:
            if pattern in task:
                task = task.split(pattern, 1)[1].strip()
                break
        
        # English patterns
        for pattern in ['remind me to', 'remind me about', 'remind me that', 'set reminder for']:
            if pattern in task:
                task = task.split(pattern, 1)[1].strip()
                break
        
        # Remove time expressions (simple cleanup)
        time_patterns = ['dalam', 'menit', 'jam', 'lagi', 'in', 'minutes', 'hours', 'mins', 'hrs']
        words = task.split()
        cleaned_words = []
        skip_next = False
        
        for i, word in enumerate(words):
            if skip_next:
                skip_next = False
                continue
            
            # Skip numbers followed by time units
            if word.isdigit() and i + 1 < len(words) and words[i + 1] in time_patterns:
                skip_next = True
                continue
            
            if word not in time_patterns:
                cleaned_words.append(word)
        
        result = ' '.join(cleaned_words).strip()
        return result if result else "Reminder"
    
    async def _handle_reminder_conversation(self, user_input, system_prompt):
        """Handle general reminder conversation."""
        try:
            conversation_prompt = f"""{system_prompt}

User message: {user_input}

Respond naturally as a helpful reminder assistant. Be conversational and offer to help create reminders."""
            
            response = await self.ai_model.generate_content_async(conversation_prompt)
            return {"message": response.text.strip()}
            
        except Exception as e:
            print(f"Enhanced Reminder Agent conversation error: {e}")
            return {"message": "I'd be happy to help you with reminders! What would you like me to remind you about?"}
