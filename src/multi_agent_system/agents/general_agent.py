from .base_agent import BaseAgent

class GeneralAgent(BaseAgent):
    def __init__(self, supabase, ai_model):
        super().__init__(supabase_manager, gemini_manager)
        self.agent_type = "general"

    async def process(self, user_input, context, routing_info=None):
        """
        Process general queries and conversations.
        routing_info contains assumptions and confidence from IntentClassifierAgent.
        """
        try:
            # Use routing_info assumptions if available
            assumptions = routing_info.get('assumptions', {}) if routing_info else {}
            
            # Load prompts
            prompt_files = [
                "01_main_system_prompt.md",
                "02_general_agent_specific.md",
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

            response = await self.gemini_manager.generate_response(
                system_prompt, user_prompt
            )
            
            return {
                "message": response,
                "actions": ["general_conversation"],
                "data": {"topic": assumptions.get('topic', 'general')}
            }
            
        except Exception as e:
            return {
                "message": "I'm having trouble processing your request right now. Could you please try again?",
                "actions": ["error"],
                "error": str(e)
            }