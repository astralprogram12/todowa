from .base_agent import BaseAgent
import database_personal as database
import os
from datetime import datetime, timezone

class EnhancedReminderAgent(BaseAgent):
    """Enhanced AI-powered reminder agent with multilingual support and advanced time parsing."""
    
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model, agent_name="EnhancedReminderAgent")
        self.comprehensive_prompts = {}
        self._initialize_ai_processors()
    
    def _initialize_ai_processors(self):
        """Initialize AI processors for translation and time parsing."""
        try:
            # Import AI processors
            import sys
            current_dir = os.path.dirname(os.path.abspath(__file__))
            processors_path = os.path.join(current_dir, '..', '..', 'ai_text_processors')
            sys.path.insert(0, processors_path)
            
            from translation_agent import get_translation_agent, translate_to_english
            from ai_time_parser import get_ai_time_parser, parse_time_with_ai
            
            self.translation_agent = get_translation_agent()
            self.time_parser = get_ai_time_parser()
            self.translate_to_english = translate_to_english
            self.parse_time_with_ai = parse_time_with_ai
            
            print("AI processors initialized successfully")
        except Exception as e:
            print(f"Warning: Could not initialize AI processors: {e}")
            # Fallback to None - will be handled gracefully
            self.translation_agent = None
            self.time_parser = None
            self.translate_to_english = None
            self.parse_time_with_ai = None
    
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
                return await self._handle_reminder_action(user_input, user_id, current_time, user_timezone)
                
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
    
    async def _handle_reminder_action(self, user_input, user_id, current_time, user_timezone):
        """Handle reminder creation/update/delete operations using AI parsing."""
        if not user_id:
            return {"message": "I'd need to set up your account first to create reminders."}
        
        try:
            # Step 1: Translate to English if needed
            translation_result = self._translate_input(user_input)
            text_to_parse = translation_result.get('translated_text', user_input)
            original_language = translation_result.get('detected_language', 'English')
            
            # Step 2: Parse time expression using AI
            time_parsing_result = self._parse_time_with_ai_fallback(text_to_parse, current_time, user_timezone)
            
            # Step 3: Extract task description
            task_description = time_parsing_result.get('task_description', '').strip()
            if not task_description:
                task_description = self._extract_task_description(user_input, text_to_parse)
            
            # Step 4: Get parsed datetime
            reminder_time = time_parsing_result.get('parsed_datetime', current_time)
            confidence = time_parsing_result.get('confidence', 0.5)
            
            # Step 5: Create the reminder
            reminder_time_iso = reminder_time.isoformat().replace('+00:00', 'Z')
            
            task_data = database.add_task_entry(
                supabase=self.supabase,
                user_id=user_id,
                title=task_description,
                category='reminder_based',
                reminder_at=reminder_time_iso
            )
            
            # Step 6: Generate user-friendly confirmation
            if task_data:
                time_description = time_parsing_result.get('user_friendly_time', 'at the specified time')
                
                if confidence > 0.7:
                    clean_message = f"Perfect! I've set a reminder for '{task_description}' {time_description}. I'll make sure to remind you!"
                else:
                    clean_message = f"I've created a reminder for '{task_description}' {time_description}. If this time isn't quite right, just let me know and I can adjust it!"
                    
                # Add language detection context if non-English
                if original_language != 'English' and translation_result.get('needs_translation', False):
                    clean_message += f" (I understood your request in {original_language})"
            else:
                clean_message = f"I've got it! I'll make sure to remind you about {task_description}."
            
            return {"message": clean_message}
            
        except Exception as e:
            print(f"Reminder creation error: {e}")
            return {"message": "I'm having trouble setting up that reminder right now. Please try again."}
    
    async def _handle_reminder_conversation(self, user_input, system_prompt):
        """Handle general reminder-related conversation."""
        user_prompt = f"""
User said: {user_input}

This is about reminders. Respond naturally and helpfully.
Do not include any technical details.
"""
        
        try:
            response = self.ai_model.generate_content([system_prompt, user_prompt])
            response_text = response.text
            clean_message = self._clean_response(response_text)
            return {"message": clean_message}
        except Exception as e:
            print(f"AI response error: {e}")
            return {"message": "I'd be happy to help you with reminders! What would you like me to remind you about?"}
    
    def _translate_input(self, text):
        """Translate input text to English if needed."""
        if self.translate_to_english:
            try:
                return self.translate_to_english(text)
            except Exception as e:
                print(f"Translation error: {e}")
        
        # Fallback: assume English
        return {
            'original_text': text,
            'translated_text': text,
            'detected_language': 'English',
            'needs_translation': False
        }
    
    def _parse_time_with_ai_fallback(self, text, current_time, user_timezone):
        """Parse time using AI with fallback to basic parsing."""
        if self.parse_time_with_ai:
            try:
                return self.parse_time_with_ai(text, current_time, user_timezone)
            except Exception as e:
                print(f"AI time parsing error: {e}")
        
        # Fallback: basic relative time detection
        return self._basic_time_fallback(text, current_time)
    
    def _basic_time_fallback(self, text, current_time):
        """Basic fallback time parsing for when AI fails."""
        from datetime import timedelta
        import re
        
        text_lower = text.lower()
        
        # Try to extract minutes
        minute_patterns = [r'(\d+)\s*menit', r'(\d+)\s*minutes?', r'(\d+)\s*mins?']
        for pattern in minute_patterns:
            match = re.search(pattern, text_lower)
            if match:
                minutes = int(match.group(1))
                new_time = current_time + timedelta(minutes=minutes)
                return {
                    'parsed_datetime': new_time,
                    'confidence': 0.8,
                    'user_friendly_time': f'in {minutes} minutes',
                    'time_type': 'relative',
                    'task_description': re.sub(pattern, '', text_lower).strip()
                }
        
        # Default: tomorrow at 15:00
        tomorrow = current_time + timedelta(days=1)
        default_time = tomorrow.replace(hour=15, minute=0, second=0, microsecond=0)
        
        return {
            'parsed_datetime': default_time,
            'confidence': 0.3,
            'user_friendly_time': 'tomorrow afternoon',
            'time_type': 'absolute',
            'task_description': text
        }
    
    def _extract_task_description(self, original_text, translated_text):
        """Extract task description from the input text."""
        # Remove common reminder keywords
        text = translated_text or original_text
        
        # Remove reminder triggers
        for phrase in ['remind me to', 'remind me about', 'set reminder for', 'reminder to', 'ingetin']:
            text = text.replace(phrase, '').strip()
        
        # Remove time expressions (basic cleanup)
        import re
        text = re.sub(r'\d+\s*(menit|minutes?|mins?|hours?|hrs?)\s*(lagi|later|from now)?', '', text, flags=re.IGNORECASE)
        text = re.sub(r'(in|dalam)\s*\d+\s*(menit|minutes?|mins?)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'(tomorrow|besok|mañana|demain)', '', text, flags=re.IGNORECASE)
        
        # Clean up extra spaces
        text = ' '.join(text.split())
        
        return text.strip() or original_text
