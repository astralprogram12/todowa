from .base_agent import BaseAgent
import database_personal  # Fix #4: Proper database import
import os

class PreferenceAgent(BaseAgent):
    def __init__(self, supabase, ai_model):  # Fix #1: Correct constructor
        super().__init__(supabase, ai_model, agent_name="PreferenceAgent")
        self.agent_type = "preference"
        self.comprehensive_prompts = {}

    async def process(self, user_input, context, routing_info=None):
        """
        Process user preference and settings requests.
        routing_info contains assumptions and confidence from IntentClassifierAgent.
        """
        try:
            # Use routing_info assumptions if available
            assumptions = routing_info.get('assumptions', {}) if routing_info else {}
            
            # Load comprehensive prompts
            if not self.comprehensive_prompts:
                self.load_comprehensive_prompts()
            
            system_prompt = self.comprehensive_prompts.get('core_system', "You are a helpful preferences agent.")
            
            # Add routing info to context if available
            enhanced_context = context.copy()
            if routing_info:
                enhanced_context['routing_info'] = routing_info
                enhanced_context['intent_assumptions'] = assumptions
            
            # Analyze preference request
            user_prompt = f"""
User Input: {user_input}
Context: {enhanced_context}

This is a preference or settings request. Determine what the user wants to:
- Set/change preferences
- View current settings
- Configure notification preferences
- Update personal information
- Manage communication preferences

If routing assumptions suggest specific:
- Preference type (notifications, language, timezone, etc.)
- Action (set, get, update, delete)
- Values or settings

Incorporate these assumptions confidently.

Provide appropriate response and indicate what actions should be taken.
"""

            # Fix #2: Correct AI model call with array parameter
            response = self.ai_model.generate_content([
                system_prompt, user_prompt
            ])
            response_text = response.text
            
            # Parse and handle the preference request
            preference_result = await self._handle_preference_request(
                response_text, user_input, enhanced_context, assumptions
            )
            
            return preference_result
            
        except Exception as e:
            return {
                "message": f"I encountered an error while handling your preferences: {str(e)}",
                "actions": ["preference_error"],
                "error": str(e)
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
            
            # Create comprehensive system prompt for preference agent
            self.comprehensive_prompts = {
                'core_system': self._build_preference_system_prompt(prompts_dict),
                'core_identity': prompts_dict.get('00_core_identity', ''),
                'templates': prompts_dict.get('08_templates', ''),
                'context_memory': prompts_dict.get('03_context_memory', ''),
                'requirements': prompts_dict.get('requirements', ''),
                'all_prompts': prompts_dict
            }
            
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}
    
    def _build_preference_system_prompt(self, prompts_dict):
        """Build comprehensive system prompt for preference agent."""
        core_identity = prompts_dict.get('00_core_identity', '')
        templates = prompts_dict.get('08_templates', '')
        context_memory = prompts_dict.get('03_context_memory', '')
        requirements = prompts_dict.get('requirements', '')
        
        return f"""{core_identity}

## PREFERENCE AGENT SPECIALIZATION
You are specifically focused on user preference management:
- Setting and updating user preferences and settings
- Managing notification preferences and communication settings
- Handling personal information and configuration updates
- Providing preference status and current settings information
- Ensuring user preferences are properly stored and applied

{templates}

{context_memory}

## REQUIREMENTS COMPLIANCE
{requirements}

## PREFERENCE AGENT BEHAVIOR
- ALWAYS respect user privacy and preference choices
- Use structured templates for preference confirmations
- Apply context memory for preference history tracking
- Follow comprehensive prompt system for enhanced preference management"""

    async def _handle_preference_request(self, ai_response, original_input, context, assumptions):
        """Handle the specific preference request based on AI analysis"""
        try:
            preference_type = assumptions.get('preference_type', self._determine_preference_type(original_input))
            action = assumptions.get('action', self._determine_action(original_input))
            user_id = context.get('user_id')
            
            if action == 'get':
                return await self._get_preferences(user_id, preference_type, context)
            elif action == 'set':
                return await self._set_preferences(user_id, preference_type, original_input, context)
            elif action == 'update':
                return await self._update_preferences(user_id, preference_type, original_input, context)
            else:
                return {
                    "message": ai_response,
                    "actions": ["preference_analyzed"],
                    "data": {
                        "preference_type": preference_type,
                        "action": action
                    }
                }
                
        except Exception as e:
            return {
                "message": f"Error handling preference request: {str(e)}",
                "actions": ["preference_error"],
                "error": str(e)
            }

    def _determine_preference_type(self, user_input):
        """Determine the preference type from user input"""
        user_input_lower = user_input.lower()
        
        if any(word in user_input_lower for word in ['notification', 'notify', 'alert']):
            return 'notifications'
        elif any(word in user_input_lower for word in ['timezone', 'time zone', 'time']):
            return 'timezone'
        elif any(word in user_input_lower for word in ['language', 'lang']):
            return 'language'
        elif any(word in user_input_lower for word in ['location', 'address']):
            return 'location'
        else:
            return 'general'

    def _determine_action(self, user_input):
        """Determine the action from user input"""
        user_input_lower = user_input.lower()
        
        if any(word in user_input_lower for word in ['show', 'get', 'view', 'what']):
            return 'get'
        elif any(word in user_input_lower for word in ['set', 'change', 'update', 'modify']):
            return 'set'
        else:
            return 'get'

    async def _get_preferences(self, user_id, preference_type, context):
        """Get user preferences"""
        try:
            # Get preferences using correct database function
            preferences = database_personal.get_user_preferences(
                supabase=self.supabase,
                user_id=user_id,
                preference_type=preference_type
            )
            
            if preferences:
                return {
                    "message": f"Here are your {preference_type} preferences:",
                    "preferences": preferences,
                    "actions": ["preferences_retrieved"]
                }
            else:
                return {
                    "message": f"No {preference_type} preferences found. Would you like to set some?",
                    "actions": ["no_preferences_found"]
                }
                
        except Exception as e:
            return {
                "message": f"Error retrieving preferences: {str(e)}",
                "error": str(e)
            }

    async def _set_preferences(self, user_id, preference_type, user_input, context):
        """Set user preferences"""
        try:
            # Extract preference values from user input
            preference_values = self._extract_preference_values(user_input, preference_type)
            
            # Set preferences using correct database function
            result = database_personal.set_user_preferences(
                supabase=self.supabase,
                user_id=user_id,
                preference_type=preference_type,
                values=preference_values
            )
            
            if result:
                # Log the preference change
                database_personal.log_action(
                    supabase=self.supabase,
                    user_id=user_id,
                    action_type="preferences_updated",
                    entity_type="preferences",
                    action_details={
                        "preference_type": preference_type,
                        "values": preference_values
                    },
                    success_status=True
                )
                
                return {
                    "message": f"Your {preference_type} preferences have been updated successfully!",
                    "updated_preferences": preference_values,
                    "actions": ["preferences_updated"]
                }
            else:
                return {
                    "message": "Failed to update preferences. Please try again.",
                    "actions": ["preferences_update_failed"]
                }
                
        except Exception as e:
            return {
                "message": f"Error setting preferences: {str(e)}",
                "error": str(e)
            }

    async def _update_preferences(self, user_id, preference_type, user_input, context):
        """Update existing preferences"""
        # For now, treat update the same as set
        return await self._set_preferences(user_id, preference_type, user_input, context)

    def _extract_preference_values(self, user_input, preference_type):
        """Extract preference values from user input"""
        if preference_type == 'notifications':
            return self._extract_notification_preferences(user_input)
        elif preference_type == 'timezone':
            return self._extract_timezone_preference(user_input)
        elif preference_type == 'language':
            return self._extract_language_preference(user_input)
        elif preference_type == 'location':
            return self._extract_location_preference(user_input)
        else:
            return {"raw_input": user_input}

    def _extract_notification_preferences(self, user_input):
        """Extract notification preferences"""
        preferences = {}
        user_input_lower = user_input.lower()
        
        if 'enable' in user_input_lower or 'on' in user_input_lower:
            preferences['enabled'] = True
        elif 'disable' in user_input_lower or 'off' in user_input_lower:
            preferences['enabled'] = False
            
        if 'morning' in user_input_lower:
            preferences['morning_notifications'] = True
        if 'evening' in user_input_lower:
            preferences['evening_notifications'] = True
            
        return preferences

    def _extract_timezone_preference(self, user_input):
        """Extract timezone preference"""
        import re
        # Simple timezone extraction
        timezone_match = re.search(r'(UTC[+-]\d{1,2}|[A-Z]{3,4})', user_input.upper())
        if timezone_match:
            return {"timezone": timezone_match.group(1)}
        else:
            return {"timezone": "UTC"}

    def _extract_language_preference(self, user_input):
        """Extract language preference"""
        languages = {
            'english': 'en',
            'spanish': 'es',
            'french': 'fr',
            'german': 'de',
            'italian': 'it',
            'portuguese': 'pt'
        }
        
        user_input_lower = user_input.lower()
        for lang_name, lang_code in languages.items():
            if lang_name in user_input_lower:
                return {"language": lang_code}
        
        return {"language": "en"}  # Default to English

    def _extract_location_preference(self, user_input):
        """Extract location preference"""
        # Simple location extraction - in real implementation would use more sophisticated parsing
        return {"location": user_input}
