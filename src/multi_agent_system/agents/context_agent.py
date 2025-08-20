from .base_agent import BaseAgent

class ContextAgent(BaseAgent):
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model, agent_name="ContextAgent")
        self.agent_type = "context"

    async def process(self, user_input, context, routing_info=None):
        """
        Process context-related requests and manage conversation context.
        routing_info contains assumptions and confidence from IntentClassifierAgent.
        """
        try:
            # Use routing_info assumptions if available
            assumptions = routing_info.get('assumptions', {}) if routing_info else {}
            
            # Load prompts
            prompt_files = [
                "01_main_system_prompt.md",
                "02_context_agent_specific.md",
                "03_context_understanding.md",
                "04_response_formatting.md",
                "05_datetime_handling.md",
                "06_error_handling.md",
                "07_conversation_flow.md",
                "08_whatsapp_integration.md",
                "09_intelligent_decision_tree.md"
            ]
            
            system_prompt = self.load_prompts(prompt_files)
            
            # Add routing info to context if available
            enhanced_context = context.copy()
            if routing_info:
                enhanced_context['routing_info'] = routing_info
                enhanced_context['intent_assumptions'] = assumptions
            
            # Analyze context request
            user_prompt = f"""
User Input: {user_input}
Current Context: {enhanced_context}

This appears to be a context-related request. This could involve:
- Asking about previous conversation
- Requesting clarification
- Referencing earlier topics
- Managing conversation state

If routing assumptions suggest specific context operations, apply them confidently.

Provide an appropriate response that addresses the context needs.
"""

            response = await self.ai_model.generate_content(
                system_prompt, user_prompt
            )
            
            # Determine if context needs to be updated or retrieved
            context_action = await self._determine_context_action(user_input, assumptions)
            
            result = {
                "message": response,
                "actions": ["context_processed"],
                "data": {
                    "context_action": context_action,
                    "topic_reference": assumptions.get('topic_reference')
                }
            }
            
            # Perform context operations if needed
            if context_action == "retrieve_history":
                history = await self._retrieve_conversation_history(enhanced_context)
                result["data"]["history"] = history
                result["actions"].append("history_retrieved")
            elif context_action == "update_context":
                await self._update_conversation_context(enhanced_context, user_input, response)
                result["actions"].append("context_updated")
            
            return result
            
        except Exception as e:
            return {
                "message": "I'm having trouble understanding the context of your request. Could you provide more details?",
                "actions": ["context_error"],
                "error": str(e)
            }

    async def _determine_context_action(self, user_input, assumptions):
        """Determine what context action is needed"""
        if any(word in user_input.lower() for word in ['earlier', 'before', 'previous', 'ago', 'remember']):
            return "retrieve_history"
        elif any(word in user_input.lower() for word in ['update', 'change', 'modify', 'set']):
            return "update_context"
        else:
            return "maintain_context"

    async def _retrieve_conversation_history(self, context):
        """Retrieve relevant conversation history"""
        try:
            # Get recent conversation history from database
            user_id = context.get('user_id')
            if user_id:
                history = await self.supabase_manager.get_records(
                    'conversations',
                    filters={'user_id': user_id},
                    limit=10,
                    order_by=[('created_at', 'desc')]
                )
                return history
            return []
        except Exception as e:
            print(f"Error retrieving conversation history: {e}")
            return []

    async def _update_conversation_context(self, context, user_input, response):
        """Update conversation context in database"""
        try:
            conversation_data = {
                "user_id": context.get('user_id'),
                "user_input": user_input,
                "agent_response": response,
                "context": context,
                "timestamp": context.get('timestamp'),
                "agent_type": "context"
            }
            
            await self.supabase_manager.create_record('conversations', conversation_data)
        except Exception as e:
            print(f"Error updating conversation context: {e}")