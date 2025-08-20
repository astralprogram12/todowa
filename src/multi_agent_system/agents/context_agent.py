from .base_agent import BaseAgent
import database_personal  # Fix #4: Proper database import

class ContextAgent(BaseAgent):
    def __init__(self, supabase, ai_model):  # Fix #1: Correct constructor
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
            
            # Fix #3: Load prompts synchronously (no await)
            prompts_dict = self.load_prompts("prompts")
            system_prompt = prompts_dict.get("00_core_identity", "You are a helpful context management agent.")
            
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

            # Fix #2: Correct AI model call with array parameter
            response = await self.ai_model.generate_content([
                system_prompt, user_prompt
            ])
            response_text = response.text
            
            # Determine if context needs to be updated or retrieved
            context_action = await self._determine_context_action(user_input, assumptions)
            
            result = {
                "message": response_text,
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
                await self._update_conversation_context(enhanced_context, user_input, response_text)
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
            user_id = context.get('user_id')
            if user_id:
                # Get conversation history using correct database function
                history = database_personal.get_conversation_history(
                    supabase=self.supabase,
                    user_id=user_id,
                    limit=10
                )
                return history
        except Exception as e:
            print(f"Error retrieving conversation history: {e}")
        
        return []

    async def _update_conversation_context(self, context, user_input, response):
        """Update the conversation context"""
        try:
            user_id = context.get('user_id')
            if user_id:
                # Store conversation context using correct database function
                database_personal.store_conversation_context(
                    supabase=self.supabase,
                    user_id=user_id,
                    user_input=user_input,
                    agent_response=response,
                    context_data=context
                )
        except Exception as e:
            print(f"Error updating conversation context: {e}")
