from .base_agent import BaseAgent
import database_personal  # Fix #4: Proper database import

class GuideAgent(BaseAgent):
    """Agent for providing how-to instructions and procedural guidance."""
    
    def __init__(self, supabase, ai_model):  # Fix #1: Correct constructor
        super().__init__(supabase, ai_model, "GuideAgent")
    
    async def process(self, user_input, context, routing_info=None):
        """Process guide requests and return a response.
        
        Args:
            user_input: The input text from the user
            context: The context of the conversation
            routing_info: NEW - AI classification with smart assumptions
            
        Returns:
            A response to the user input
        """
        user_id = context.get('user_id')
        
        # NEW: Apply AI assumptions to enhance processing
        enhanced_context = self._apply_ai_assumptions(context, routing_info)
        
        # NEW: Use AI assumptions if available
        if routing_info and routing_info.get('assumptions'):
            print(f"GuideAgent using AI assumptions: {routing_info['assumptions']}")
            # Use AI-suggested topic if available
            topic = routing_info['assumptions'].get('topic') or self._determine_topic(user_input)
        else:
            # Determine the topic for the guide
            topic = self._determine_topic(user_input)
        
        # Generate guide based on the topic and user input
        return await self._generate_guide(user_id, user_input, topic, context)
    
    def _apply_ai_assumptions(self, context, routing_info):
        """Apply AI assumptions to enhance the context"""
        enhanced_context = context.copy()
        if routing_info:
            enhanced_context.update(routing_info.get('assumptions', {}))
        return enhanced_context
    
    def _determine_topic(self, user_input):
        """Determine the topic for the guide from the user input."""
        user_input_lower = user_input.lower()
        
        # Extract the topic from the user input
        topic_indicators = ['how to', 'guide for', 'steps to', 'instructions for', 'process for']
        
        for indicator in topic_indicators:
            if indicator in user_input_lower:
                parts = user_input_lower.split(indicator, 1)
                if len(parts) > 1:
                    return parts[1].strip()
        
        # If no specific topic is found, use the entire input
        return user_input
    
    async def _generate_guide(self, user_id, user_input, topic, context):
        """Generate a guide based on the topic and user input."""
        try:
            # Fix #3: Load prompts synchronously (no await)
            prompts_dict = self.load_prompts("prompts")
            system_prompt = prompts_dict.get("00_core_identity", "You are a helpful guide agent.")
            
            user_prompt = f"Create a step-by-step guide for: {topic}\n\nProvide clear, detailed instructions with examples where helpful."
            
            # Fix #2: Correct AI model call with array parameter
            response = await self.ai_model.generate_content([
                system_prompt, user_prompt
            ])
            response_text = response.text
            
            # Log the action
            if user_id:
                database_personal.log_action(
                    supabase=self.supabase,
                    user_id=user_id,
                    action_type="generate_guide",
                    entity_type="guide",
                    action_details={
                        "topic": topic,
                        "guide_length": len(response_text)
                    },
                    success_status=True
                )
            
            return {
                "status": "success",
                "message": response_text,
                "topic": topic,
                "actions": [{"agent": self.agent_name, "action": "guide_generated"}]
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"I'm having trouble creating a guide for that topic. Please try rephrasing your request.",
                "error": str(e)
            }
