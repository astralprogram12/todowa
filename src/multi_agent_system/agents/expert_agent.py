from .base_agent import BaseAgent
import database_personal  # Fix #4: Proper database import

class ExpertAgent(BaseAgent):
    """Agent for providing domain-specific advice and strategies."""
    
    def __init__(self, supabase, ai_model):  # Fix #1: Correct constructor
        super().__init__(supabase, ai_model, "ExpertAgent")
    
    async def process(self, user_input, context, routing_info=None):
        """Process expert advice requests and return a response.
        
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
            print(f"ExpertAgent using AI assumptions: {routing_info['assumptions']}")
            # Use AI-suggested domain if available
            domain = routing_info['assumptions'].get('domain') or self._determine_domain(user_input)
        else:
            # Determine the domain for the expert advice
            domain = self._determine_domain(user_input)
        
        # Generate expert advice based on the domain and user input
        return await self._generate_expert_advice(user_id, user_input, domain, context)
    
    def _apply_ai_assumptions(self, context, routing_info):
        """Apply AI assumptions to enhance the context"""
        enhanced_context = context.copy()
        if routing_info:
            enhanced_context.update(routing_info.get('assumptions', {}))
        return enhanced_context
    
    def _determine_domain(self, user_input):
        """Determine the domain for expert advice from the user input."""
        user_input_lower = user_input.lower()
        
        # Define domain keywords
        domain_keywords = {
            'productivity': ['productive', 'efficiency', 'time management', 'organize', 'prioritize', 'focus'],
            'career': ['career', 'job', 'professional', 'work', 'interview', 'resume', 'workplace'],
            'technology': ['technology', 'tech', 'computer', 'software', 'hardware', 'digital', 'online'],
            'finance': ['finance', 'money', 'budget', 'saving', 'investment', 'financial', 'expense'],
            'health': ['health', 'fitness', 'exercise', 'diet', 'nutrition', 'wellness', 'mental health'],
            'education': ['education', 'learning', 'study', 'academic', 'school', 'university', 'course'],
            'relationships': ['relationship', 'communication', 'social', 'family', 'friend', 'partner', 'conflict']
        }
        
        # Check for domain keywords in the user input
        for domain, keywords in domain_keywords.items():
            if any(keyword in user_input_lower for keyword in keywords):
                return domain
        
        # Default to productivity if no specific domain is detected
        return 'productivity'
    
    async def _generate_expert_advice(self, user_id, user_input, domain, context):
        """Generate expert advice based on the domain and user input."""
        try:
            # Fix #3: Load prompts synchronously (no await)
            prompts_dict = self.load_prompts("prompts")
            system_prompt = prompts_dict.get("00_core_identity", "You are an expert advisor.")
            
            user_prompt = f"""
Domain: {domain.title()}
User Question: {user_input}
Context: {context}

As an expert in {domain}, provide detailed, actionable advice for this question.
Include:
- Specific strategies or solutions
- Best practices in this domain  
- Practical steps the user can take
- Potential challenges and how to overcome them
- Resources for further learning

Make your advice practical and tailored to the user's situation.
"""
            
            # Fix #2: Correct AI model call with array parameter
            response = await self.ai_model.generate_content([
                system_prompt, user_prompt
            ])
            response_text = response.text
            
            # Log the expert advice request
            if user_id:
                database_personal.log_action(
                    supabase=self.supabase,
                    user_id=user_id,
                    action_type="expert_advice",
                    entity_type="advice",
                    action_details={
                        "domain": domain,
                        "question_length": len(user_input)
                    },
                    success_status=True
                )
            
            return {
                "status": "success",
                "message": response_text,
                "domain": domain,
                "actions": [{"agent": self.agent_name, "action": "expert_advice_provided"}]
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"I'm having trouble providing expert advice right now. Please try rephrasing your question.",
                "error": str(e)
            }
