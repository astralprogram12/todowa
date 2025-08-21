from .base_agent import BaseAgent
import database_personal  # Fix #4: Proper database import
import os

class GuideAgent(BaseAgent):
    """Agent for providing how-to instructions and procedural guidance."""
    
    def __init__(self, supabase, ai_model):  # Fix #1: Correct constructor
        super().__init__(supabase, ai_model, "GuideAgent")
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
            
            # Create comprehensive system prompt for guide assistance
            self.comprehensive_prompts = {
                'core_system': self._build_guide_system_prompt(prompts_dict),
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
    
    def _build_guide_system_prompt(self, prompts_dict):
        """Build comprehensive system prompt for guide agent."""
        core_identity = prompts_dict.get('00_core_identity', '')
        ai_interactions = prompts_dict.get('04_ai_interactions', '')
        context_memory = prompts_dict.get('03_context_memory', '')
        templates = prompts_dict.get('08_templates', '')
        decision_tree = prompts_dict.get('09_intelligent_decision_tree', '')
        requirements = prompts_dict.get('requirements', '')
        
        return f"""{core_identity}

## GUIDE AGENT SPECIALIZATION
You are specifically focused on providing help and guidance including:
- Creating step-by-step instructions and procedural guidance
- Explaining how-to processes for app features and functionality
- Providing clear, structured tutorials and walk-throughs
- Assisting users who are confused about app functionality
- Offering onboarding guidance for new users

{ai_interactions}

{context_memory}

{templates}

{decision_tree}

## REQUIREMENTS COMPLIANCE
{requirements}

## GUIDE AGENT BEHAVIOR
- Apply guide mode interaction patterns for instructional delivery
- Use structured templates for step-by-step guidance formatting
- Reference user context and memories for personalized instructions
- Follow intelligent decision tree for proper classification
- Provide concrete examples and clear action steps"""

    async def process(self, user_input, context, routing_info=None):
        """Process guide requests with comprehensive prompt system.
        
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
            print(f"GuideAgent using AI assumptions: {routing_info['assumptions']}")
            # Use AI-suggested topic if available
            topic = routing_info['assumptions'].get('topic') or self._determine_topic(user_input)
        else:
            # Determine the topic for the guide
            topic = self._determine_topic(user_input)
        
        # Generate guide with comprehensive prompts
        return await self._generate_guide_comprehensive(user_id, user_input, topic, enhanced_context, routing_info)
    
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
    
    async def _generate_guide_comprehensive(self, user_id, user_input, topic, context, routing_info):
        """Generate a guide using comprehensive prompt system."""
        try:
            # Build comprehensive prompt using all relevant prompts
            system_prompt = self.comprehensive_prompts.get('core_system', 'You are a helpful guide agent.')
            
            # Include specific prompt sections for enhanced processing
            ai_interactions = self.comprehensive_prompts.get('ai_interactions', '')
            templates = self.comprehensive_prompts.get('templates', '')
            context_memory = self.comprehensive_prompts.get('context_memory', '')
            
            user_prompt = f"""
Topic: {topic}
User Question: {user_input}
Context: {context}
Routing Info: {routing_info}

USING COMPREHENSIVE PROMPTS:
1. Apply guide mode interaction patterns for instructional delivery
2. Use structured templates for step-by-step guidance formatting
3. Reference user context and memories for personalized instructions
4. Follow the complete guide assistance guidelines
5. Provide concrete examples and clear action steps

Create a comprehensive step-by-step guide for: {topic}

Provide clear, detailed instructions following all prompt guidelines:
- Use structured formatting with headers and bullet points
- Include concrete examples where helpful
- Break down complex processes into manageable steps
- Reference app features and functionality when relevant
- End with helpful follow-up questions
"""
            
            # Enhanced AI model call with comprehensive prompts
            full_prompt = f"{system_prompt}\n\nSPECIFIC GUIDANCE:\n{ai_interactions}\n{templates}\n{context_memory}\n\nUSER REQUEST:\n{user_prompt}"
            
            response = self.ai_model.generate_content([
                full_prompt
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
                        "guide_length": len(response_text),
                        "comprehensive_prompts_used": True
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
