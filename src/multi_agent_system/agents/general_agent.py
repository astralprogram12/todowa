from .base_agent import BaseAgent
import database_personal  # Fix #4: Proper database import

class GeneralAgent(BaseAgent):
    def __init__(self, supabase, ai_model):  # Fix #1: Correct constructor
        super().__init__(supabase, ai_model, "GeneralAgent")
        self.agent_type = "general"

    async def process(self, user_input, context, routing_info=None):
        """
        Process general queries and conversations.
        routing_info contains assumptions and confidence from IntentClassifierAgent.
        """
        try:
            # Use routing_info assumptions if available
            assumptions = routing_info.get('assumptions', {}) if routing_info else {}
            
            # Fix #3: Load prompts synchronously (no await)
            prompts_dict = self.load_prompts("prompts")
            system_prompt = prompts_dict.get("00_core_identity", "You are a friendly, conversational AI.")
            
            # Add routing info to context if available
            enhanced_context = context.copy()
            if routing_info:
                enhanced_context['routing_info'] = routing_info
                enhanced_context['intent_assumptions'] = assumptions
            
            # Generate appropriate response for general conversation
            user_prompt = f"""
User Input: {user_input}
Context: {enhanced_context}

This is a general conversation or query. Provide a helpful, engaging response.
If routing assumptions suggest specific topics or approaches, incorporate them naturally.

Guidelines:
- Be conversational and friendly
- Provide useful information when possible
- Ask clarifying questions if needed
- Keep responses concise but informative
"""

            # Fix #2: Correct AI model call with array parameter
            response = await self.ai_model.generate_content([
                system_prompt, user_prompt
            ])
            response_text = response.text
            
            # Log the general conversation
            user_id = context.get('user_id')
            if user_id:
                database_personal.log_action(
                    supabase=self.supabase,
                    user_id=user_id,
                    action_type="general_conversation",
                    entity_type="conversation",
                    action_details={"topic": assumptions.get('topic', 'general')},
                    success_status=True
                )
            
            return {
                "status": "success",
                "message": response_text,
                "actions": [{"agent": self.agent_name, "action": "general_response"}]
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "message": "I'm having trouble understanding your request. Could you please rephrase it?",
                "error": str(e)
            }
