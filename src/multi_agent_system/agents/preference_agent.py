from .base_agent import BaseAgent

class PreferenceAgent(BaseAgent):
    def __init__(self, supabase_manager, gemini_manager):
        super().__init__(supabase_manager, gemini_manager)
        self.agent_type = "preference"

    async def process(self, user_input, context, routing_info=None):
        """
        Process user preference and settings requests.
        routing_info contains assumptions and confidence from IntentClassifierAgent.
        """
        try:
            # Use routing_info assumptions if available
            assumptions = routing_info.get('assumptions', {}) if routing_info else {}
            
            # Load prompts
            prompt_files = [
                "01_main_system_prompt.md",
                "02_preference_agent_specific.md",
                "03_context_understanding.md",
                "04_response_formatting.md",
                "05_datetime_handling.md",
                "06_error_handling.md",
                "07_conversation_flow.md",
                "08_whatsapp_integration.md",
                "09_intelligent_decision_tree.md"
            ]
            
            system_prompt = await self.load_prompts(prompt_files)
            
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

            response = await self.gemini_manager.generate_response(
                system_prompt, user_prompt
            )
            
            # Parse and handle the preference request
            preference_result = await self._handle_preference_request(
                response, user_input, enhanced_context, assumptions
            )
            
            return preference_result
            
        except Exception as e:
            return {
                "message": f"I encountered an error while handling your preferences: {str(e)}",
                "actions": ["preference_error"],
                "error": str(e)
            }

    async def _handle_preference_request(self, ai_response, original_input, context, assumptions):
        """Handle the specific preference request based on AI analysis"""
        try:
            preference_type = assumptions.get('preference_type', 'general')
            action = assumptions.get('action', 'unknown')
            
            if action in ['set', 'update', 'change']:
                return await self._set_preference(preference_type, ai_response, context)
            elif action in ['get', 'view', 'show']:
                return await self._get_preference(preference_type, context)
            elif action in ['delete', 'remove', 'clear']:
                return await self._delete_preference(preference_type, context)
            else:
                # Default to showing current preferences and asking for clarification
                current_prefs = await self._get_all_preferences(context)
                return {
                    "message": f"{ai_response}\n\nYour current preferences:\n{self._format_preferences(current_prefs)}",
                    "actions": ["preference_info_shown"],
                    "data": {"preferences": current_prefs}
                }
                
        except Exception as e:
            return {
                "message": "I couldn't process your preference request. Please try being more specific.",
                "actions": ["preference_failed"],
                "error": str(e)
            }

    async def _set_preference(self, preference_type, ai_response, context):
        """Set or update a user preference"""
        try:
            user_id = context.get('user_id')
            if not user_id:
                return {
                    "message": "I need to identify you to save your preferences.",
                    "actions": ["preference_auth_required"]
                }
            
            # Extract preference data from AI response
            preference_data = await self._extract_preference_data(ai_response, preference_type)
            
            if preference_data:
                # Save to database
                result = await self.supabase_manager.upsert_record(
                    'user_preferences',
                    {'user_id': user_id, **preference_data},
                    ['user_id', 'preference_type']
                )
                
                if result:
                    return {
                        "message": f"✅ {preference_type.title()} preference updated successfully!",
                        "actions": ["preference_updated"],
                        "data": preference_data
                    }
            
            return {
                "message": "I couldn't understand what preference you want to set. Could you be more specific?",
                "actions": ["preference_clarification_needed"]
            }
            
        except Exception as e:
            return {
                "message": f"Failed to save preference: {str(e)}",
                "actions": ["preference_save_failed"],
                "error": str(e)
            }

    async def _get_preference(self, preference_type, context):
        """Retrieve specific user preference"""
        try:
            user_id = context.get('user_id')
            preferences = await self.supabase_manager.get_records(
                'user_preferences',
                filters={'user_id': user_id, 'preference_type': preference_type}
            )
            
            if preferences:
                pref_data = preferences[0]
                return {
                    "message": f"Your {preference_type} preference: {self._format_single_preference(pref_data)}",
                    "actions": ["preference_retrieved"],
                    "data": pref_data
                }
            else:
                return {
                    "message": f"You haven't set any {preference_type} preferences yet.",
                    "actions": ["preference_not_found"]
                }
                
        except Exception as e:
            return {
                "message": f"Error retrieving preference: {str(e)}",
                "actions": ["preference_retrieval_failed"],
                "error": str(e)
            }

    async def _delete_preference(self, preference_type, context):
        """Delete a user preference"""
        try:
            user_id = context.get('user_id')
            result = await self.supabase_manager.delete_records(
                'user_preferences',
                filters={'user_id': user_id, 'preference_type': preference_type}
            )
            
            return {
                "message": f"✅ {preference_type.title()} preference deleted successfully!",
                "actions": ["preference_deleted"],
                "data": {"deleted_type": preference_type}
            }
            
        except Exception as e:
            return {
                "message": f"Error deleting preference: {str(e)}",
                "actions": ["preference_deletion_failed"],
                "error": str(e)
            }

    async def _get_all_preferences(self, context):
        """Get all user preferences"""
        try:
            user_id = context.get('user_id')
            if user_id:
                return await self.supabase_manager.get_records(
                    'user_preferences',
                    filters={'user_id': user_id}
                )
            return []
        except:
            return []

    async def _extract_preference_data(self, ai_response, preference_type):
        """Extract structured preference data from AI response"""
        # This would contain logic to parse the AI response and extract
        # the actual preference values to store
        return {
            "preference_type": preference_type,
            "value": ai_response,  # Simplified - would need proper parsing
            "updated_at": "now()"
        }

    def _format_preferences(self, preferences):
        """Format preferences list for display"""
        if not preferences:
            return "No preferences set."
        
        formatted = []
        for pref in preferences:
            formatted.append(f"• {pref.get('preference_type', 'Unknown')}: {pref.get('value', 'Not set')}")
        
        return "\n".join(formatted)

    def _format_single_preference(self, preference):
        """Format single preference for display"""
        return preference.get('value', 'Not set')