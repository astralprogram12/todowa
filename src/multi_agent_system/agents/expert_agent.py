from .base_agent import BaseAgent
import database_personal  # Fix #4: Proper database import
import os

class ExpertAgent(BaseAgent):
    """Agent for providing domain-specific advice and strategies."""
    
    def __init__(self, supabase, ai_model):  # Fix #1: Correct constructor
        super().__init__(supabase, ai_model, "ExpertAgent")
        self.comprehensive_prompts = {}
    
    def load_comprehensive_prompts(self):
        """Load ALL prompts from the prompts/v1/ directory and requirements."""
        try:
            prompts_dict = {}
            
            # Load all prompts from v1 directory
            v1_dir = "/workspace/user_input_files/todowa/prompts/v1"
            if os.path.exists(v1_dir):
                for file_name in os.listdir(v1_dir):
                    if file_name.endswith('.md'):
                        prompt_name = file_name.replace('.md', '')
                        file_path = os.path.join(v1_dir, file_name)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            prompts_dict[prompt_name] = f.read()
            
            # Load requirements
            requirements_path = "/workspace/user_input_files/99_requirements.md"
            if os.path.exists(requirements_path):
                with open(requirements_path, 'r', encoding='utf-8') as f:
                    prompts_dict['requirements'] = f.read()
            
            # Create comprehensive system prompt for expert advice
            self.comprehensive_prompts = {
                'core_system': self._build_expert_system_prompt(prompts_dict),
                'ai_interactions': prompts_dict.get('04_ai_interactions', ''),
                'context_memory': prompts_dict.get('03_context_memory', ''),
                'templates': prompts_dict.get('08_templates', ''),
                'decision_tree': prompts_dict.get('09_intelligent_decision_tree', ''),
                'requirements': prompts_dict.get('requirements', ''),
                'all_prompts': prompts_dict
            }
            
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}
    
    def _build_expert_system_prompt(self, prompts_dict):
        """Build comprehensive system prompt for expert agent."""
        core_identity = prompts_dict.get('00_core_identity', '')
        ai_interactions = prompts_dict.get('04_ai_interactions', '')
        context_memory = prompts_dict.get('03_context_memory', '')
        templates = prompts_dict.get('08_templates', '')
        decision_tree = prompts_dict.get('09_intelligent_decision_tree', '')
        requirements = prompts_dict.get('requirements', '')
        
        return f"""{core_identity}

## EXPERT AGENT SPECIALIZATION
You are specifically focused on providing expert advice and strategic guidance including:
- Domain-specific expertise across multiple fields
- Strategic advice for productivity, career, technology, finance, health, education, relationships
- Best practices and actionable recommendations
- Problem-solving strategies and frameworks
- Resource recommendations and learning paths

{ai_interactions}

{context_memory}

{templates}

{decision_tree}

## REQUIREMENTS COMPLIANCE
{requirements}

## EXPERT AGENT BEHAVIOR
- Apply expert mode interaction patterns for advice delivery
- Use structured templates for expert response formatting
- Reference user context and memories for personalized advice
- Provide comprehensive, actionable guidance with clear next steps
- Include multiple approaches and frameworks when appropriate"""

    async def process(self, user_input, context, routing_info=None):
        """Process expert advice requests with comprehensive prompt system.
        
        Args:
            user_input: The input text from the user
            context: The context of the conversation
            routing_info: NEW - AI classification with smart assumptions
            
        Returns:
            A response to the user input
        """
        user_id = context.get('user_id')
        
        # Load comprehensive prompts
        if not self.comprehensive_prompts:
            self.load_comprehensive_prompts()
        
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
        
        # Generate expert advice with comprehensive prompts
        return await self._generate_expert_advice_comprehensive(user_id, user_input, domain, enhanced_context, routing_info)
    
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
    
    async def _generate_expert_advice_comprehensive(self, user_id, user_input, domain, context, routing_info):
        """Generate expert advice using comprehensive prompt system."""
        try:
            # Build comprehensive prompt using all relevant prompts
            system_prompt = self.comprehensive_prompts.get('core_system', 'You are an expert advisor.')
            
            # Include specific prompt sections for enhanced processing
            ai_interactions = self.comprehensive_prompts.get('ai_interactions', '')
            templates = self.comprehensive_prompts.get('templates', '')
            context_memory = self.comprehensive_prompts.get('context_memory', '')
            
            user_prompt = f"""
Domain: {domain.title()}
User Question: {user_input}
Context: {context}
Routing Info: {routing_info}

USING COMPREHENSIVE PROMPTS:
1. Apply expert mode interaction patterns for advice delivery
2. Use structured templates for professional expert response formatting
3. Reference user context and memories for personalized advice
4. Follow the complete expert advice guidelines
5. Provide strategic, actionable recommendations with clear frameworks

As an expert in {domain}, provide detailed, actionable advice following all prompt guidelines.
Include:
- Specific strategies or solutions
- Best practices in this domain  
- Practical steps the user can take
- Potential challenges and how to overcome them
- Resources for further learning

Make your advice practical and tailored to the user's situation.
"""
            
            # Enhanced AI model call with comprehensive prompts
            full_prompt = f"{system_prompt}\n\nSPECIFIC GUIDANCE:\n{ai_interactions}\n{templates}\n{context_memory}\n\nUSER REQUEST:\n{user_prompt}"
            
            response = self.ai_model.generate_content([
                full_prompt
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
                        "question_length": len(user_input),
                        "comprehensive_prompts_used": True
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
