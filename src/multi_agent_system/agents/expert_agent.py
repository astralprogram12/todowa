# Expert Agent - provides domain-specific advice and strategies

from .base_agent import BaseAgent

class ExpertAgent(BaseAgent):
    """Agent for providing domain-specific advice and strategies."""
    
    def __init__(self, supabase, ai_model):
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
            # Use the AI model to generate expert advice
            prompt = f"Act as an expert in {domain}. Provide professional advice for: {user_input}\n\nGive structured, actionable advice with clear steps and examples."
            
            # In a real implementation, we would use the AI model to generate the advice
            # For now, let's provide a sample response
            advice = self._get_sample_advice(domain)
            
            # Log the action
            self._log_action(
                user_id=user_id,
                action_type="generate_expert_advice",
                entity_type="expert_advice",
                action_details={
                    "domain": domain,
                    "query": user_input
                },
                success_status=True
            )
            
            return {
                "status": "ok",
                "message": f"Here's my expert advice on {domain}:",
                "advice": advice,
                "domain": domain
            }
            
        except Exception as e:
            error_msg = str(e)
            
            # Log the error
            self._log_action(
                user_id=user_id,
                action_type="generate_expert_advice",
                entity_type="expert_advice",
                action_details={
                    "domain": domain,
                    "query": user_input
                },
                success_status=False,
                error_details=error_msg
            )
            
            return {
                "status": "error",
                "message": f"Failed to generate expert advice: {error_msg}"
            }
    
    def _get_sample_advice(self, domain):
        """Get sample advice for the specified domain."""
        sample_advice = {
            'productivity': """**Productivity Strategy:**

**Key Principles:**
• Focus on high-impact tasks first
• Minimize context-switching
• Use time-blocking for deep work

**Implementation Steps:**
1. Identify your 1-3 most important tasks each morning
2. Block 90-minute distraction-free sessions for deep work
3. Take deliberate breaks using the Pomodoro technique

**Example Workflow:**
Start your day by completing one high-impact task before checking email or messages. This builds momentum and ensures progress on what matters most.""",
            
            'career': """**Career Development Strategy:**

**Key Principles:**
• Focus on developing transferable skills
• Build your professional network consistently
• Document your achievements for visibility

**Implementation Steps:**
1. Identify skill gaps based on target roles
2. Schedule monthly coffee chats with industry professionals
3. Create a system to track and showcase your accomplishments

**Example Approach:**
Set up a "professional development hour" every week specifically dedicated to learning a high-value skill in your field.""",
            
            'technology': """**Technology Integration Strategy:**

**Key Principles:**
• Start with problems, not technologies
• Prioritize systems that reduce friction
• Build for flexibility and future expansion

**Implementation Steps:**
1. Audit your current workflow to identify pain points
2. Research solutions that integrate with existing tools
3. Test with small experiments before full implementation

**Example Setup:**
Implement an automation tool like Zapier to connect your most-used applications, saving manual data transfer time.""",
            
            'finance': """**Financial Planning Strategy:**

**Key Principles:**
• Automate essential savings and investments
• Focus on big-win decisions over micro-frugality
• Align spending with your personal values

**Implementation Steps:**
1. Set up automatic transfers to savings on payday
2. Review and negotiate major recurring expenses
3. Create separate accounts for different financial goals

**Example Approach:**
Use the 50/30/20 budget: 50% on essentials, 30% on discretionary spending, and 20% on financial goals.""",
            
            'health': """**Holistic Health Strategy:**

**Key Principles:**
• Focus on sustainable habits over quick results
• Address sleep quality as your foundation
• Integrate movement throughout your day

**Implementation Steps:**
1. Establish a consistent sleep and wake schedule
2. Incorporate 5-10 minute movement breaks every hour
3. Prepare nutrient-dense meals in batch cooking sessions

**Example Routine:**
Start with a 10-minute morning routine combining light stretching, brief meditation, and a glass of water before checking your phone.""",
            
            'education': """**Effective Learning Strategy:**

**Key Principles:**
• Use active recall instead of passive review
• Space your practice for long-term retention
• Connect new concepts to existing knowledge

**Implementation Steps:**
1. Convert notes into question-answer formats
2. Schedule spaced review sessions (1 day, 3 days, 7 days)
3. Teach concepts to others to identify knowledge gaps

**Example Technique:**
Use the Feynman Technique: explain a concept in simple language as if teaching a beginner to identify areas you don't fully understand.""",
            
            'relationships': """**Relationship Building Strategy:**

**Key Principles:**
• Practice active listening without interruption
• Express appreciation specifically and regularly
• Address issues directly without blame language

**Implementation Steps:**
1. Schedule dedicated quality time without distractions
2. Use "I" statements when discussing concerns
3. Establish regular check-ins for open communication

**Example Approach:**
When conflicts arise, use the format: "When [situation occurs], I feel [emotion] because [reason]. What I need is [request]."""
        }
        
        return sample_advice.get(domain, sample_advice['productivity'])
