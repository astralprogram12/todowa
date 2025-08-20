from .base_agent import BaseAgent

class InformationAgent(BaseAgent):
    def __init__(self, supabase_manager, gemini_manager):
        super().__init__(supabase_manager, gemini_manager)
        self.agent_type = "information"

    async def process(self, user_input, context, routing_info=None):
        """
        Process information requests and knowledge queries.
        routing_info contains assumptions and confidence from IntentClassifierAgent.
        """
        try:
            # Use routing_info assumptions if available
            assumptions = routing_info.get('assumptions', {}) if routing_info else {}
            
            # Load prompts
            prompt_files = [
                "01_main_system_prompt.md",
                "02_information_agent_specific.md",
                "03_context_understanding.md",
                "04_response_formatting.md",
                "05_datetime_handling.md",
                "06_error_handling.md",
                "07_conversation_flow.md",
                "08_whatsapp_integration.md",
                "09_intelligent_decision_tree.md"
            ]
            
            system_prompt = await self._load_prompts(prompt_files)
            
            # Add routing info to context if available
            enhanced_context = context.copy()
            if routing_info:
                enhanced_context['routing_info'] = routing_info
                enhanced_context['intent_assumptions'] = assumptions
            
            # Process information request
            user_prompt = f"""
User Input: {user_input}
Context: {enhanced_context}

This is an information or knowledge request. Provide accurate, helpful information.

If routing assumptions suggest specific:
- Information type (facts, explanations, how-to, etc.)
- Subject matter or domain
- Detail level needed

Incorporate these assumptions confidently in your response.

Guidelines:
- Provide clear, accurate information
- Structure responses logically
- Include relevant details
- Cite sources when appropriate
- Offer to clarify or expand if needed
"""

            response = await self.gemini_manager.generate_response(
                system_prompt, user_prompt
            )
            
            # Check if we should store this information for future reference
            should_store = await self._should_store_information(user_input, response, assumptions)
            
            result = {
                "message": response,
                "actions": ["information_provided"],
                "data": {
                    "topic": assumptions.get('topic', 'general'),
                    "information_type": assumptions.get('information_type', 'factual')
                }
            }
            
            if should_store:
                await self._store_information_exchange(user_input, response, enhanced_context)
                result["actions"].append("information_stored")
            
            return result
            
        except Exception as e:
            return {
                "message": "I'm having trouble retrieving that information right now. Could you please try rephrasing your question?",
                "actions": ["error"],
                "error": str(e)
            }

    async def _should_store_information(self, user_input, response, assumptions):
        """Determine if this information exchange should be stored for future reference"""
        try:
            # Store information that might be useful for future conversations
            store_keywords = ['how to', 'what is', 'explain', 'definition', 'procedure']
            return any(keyword in user_input.lower() for keyword in store_keywords)
        except:
            return False

    async def _store_information_exchange(self, user_input, response, context):
        """Store information exchange for future reference"""
        try:
            data = {
                "question": user_input,
                "answer": response,
                "context": context,
                "timestamp": context.get('timestamp'),
                "agent_type": "information"
            }
            
            await self.supabase_manager.create_record('information_exchanges', data)
        except Exception as e:
            print(f"Error storing information exchange: {e}")