from .base_agent import BaseAgent

class SilentAgent(BaseAgent):
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model, agent_name="SilentAgent")
        self.agent_type = "silent"

    async def process(self, user_input, context, routing_info=None):
        """
        Process requests that require no response or silent actions.
        routing_info contains assumptions and confidence from IntentClassifierAgent.
        """
        try:
            # Use routing_info assumptions if available
            assumptions = routing_info.get('assumptions', {}) if routing_info else {}
            
            # Load prompts
            prompt_files = [
                "01_main_system_prompt.md",
                "02_silent_agent_specific.md",
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
            
            # Determine if this truly requires silence or acknowledgment
            user_prompt = f"""
User Input: {user_input}
Context: {enhanced_context}

Analyze if this requires:
1. Complete silence (no response)
2. Silent action with acknowledgment
3. Minimal response

If routing assumptions suggest specific silent behavior, follow them confidently.
"""

            response = await self.ai_model.generate_content(
                system_prompt, user_prompt
            )
            
            # Determine response type based on analysis
            if "complete silence" in response.lower():
                # Return empty response for true silence
                return {
                    "message": "",
                    "actions": ["silent_mode"],
                    "silent": True
                }
            elif "acknowledgment" in response.lower():
                return {
                    "message": "👍",
                    "actions": ["silent_acknowledgment"]
                }
            else:
                return {
                    "message": "Understood.",
                    "actions": ["minimal_response"]
                }
                
        except Exception as e:
            # Even errors should be silent for this agent
            return {
                "message": "",
                "actions": ["silent_error"],
                "silent": True
            }