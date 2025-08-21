from .base_agent import BaseAgent
import database_personal  # Fix #4: Proper database import
import os

class GeneralAgent(BaseAgent):
    def __init__(self, supabase, ai_model):  # Fix #1: Correct constructor
        super().__init__(supabase, ai_model, "GeneralAgent")
        self.agent_type = "general"
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
            
            # Create comprehensive system prompt for general conversation
            self.comprehensive_prompts = {
                'core_system': self._build_general_system_prompt(prompts_dict),
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
    
    def _build_general_system_prompt(self, prompts_dict):
        """Build comprehensive system prompt for general agent."""
        core_identity = prompts_dict.get('00_core_identity', '')
        ai_interactions = prompts_dict.get('04_ai_interactions', '')
        context_memory = prompts_dict.get('03_context_memory', '')
        templates = prompts_dict.get('08_templates', '')
        decision_tree = prompts_dict.get('09_intelligent_decision_tree', '')
        requirements = prompts_dict.get('requirements', '')
        
        return f"""{core_identity}

## GENERAL AGENT SPECIALIZATION
You are specifically focused on general conversation and chat interactions including:
- Handling casual conversation and social interaction
- Providing friendly, engaging responses to general queries
- Managing greeting exchanges and gratitude expressions
- Building rapport and maintaining conversational flow
- Routing complex requests to appropriate specialized agents

{ai_interactions}

{context_memory}

{templates}

{decision_tree}

## REQUIREMENTS COMPLIANCE
{requirements}

## GENERAL AGENT BEHAVIOR
- Apply chat mode interaction patterns for friendly engagement
- Use structured templates for consistent response formatting
- Reference user context and memories for personalized conversation
- Follow intelligent decision tree for proper classification
- Maintain warm, professional tone while building rapport"""

    async def process(self, user_input, context, routing_info=None):
        """
        Process general queries and conversations with comprehensive prompt system.
        routing_info contains assumptions and confidence from IntentClassifierAgent.
        """
        try:
            # Load comprehensive prompts
            if not self.comprehensive_prompts:
                self.load_comprehensive_prompts()
            
            # Use routing_info assumptions if available
            assumptions = routing_info.get('assumptions', {}) if routing_info else {}
            
            # Add routing info to context if available
            enhanced_context = context.copy()
            if routing_info:
                enhanced_context['routing_info'] = routing_info
                enhanced_context['intent_assumptions'] = assumptions
            
            # Use comprehensive prompt system
            return await self._process_with_comprehensive_prompts(user_input, enhanced_context, routing_info)
            
        except Exception as e:
            return {
                "status": "error", 
                "message": "I'm having trouble understanding your request. Could you please rephrase it?",
                "error": str(e)
            }
    
    async def _process_with_comprehensive_prompts(self, user_input, context, routing_info):
        """Process general conversation with comprehensive prompt system."""
        assumptions = routing_info.get('assumptions', {}) if routing_info else {}
        
        # Build comprehensive prompt using all relevant prompts
        system_prompt = self.comprehensive_prompts.get('core_system', 'You are a friendly, conversational AI.')
        
        # Include specific prompt sections for enhanced processing
        ai_interactions = self.comprehensive_prompts.get('ai_interactions', '')
        templates = self.comprehensive_prompts.get('templates', '')
        context_memory = self.comprehensive_prompts.get('context_memory', '')
        
        user_prompt = f"""
User Input: {user_input}
Context: {context}
Routing Info: {routing_info}

USING COMPREHENSIVE PROMPTS:
1. Apply chat mode interaction patterns for friendly engagement
2. Use structured templates for consistent response formatting
3. Reference user context and memories for personalized conversation
4. Follow intelligent decision tree for classification
5. Maintain warm, professional tone while building rapport

This is a general conversation or query. Provide a helpful, engaging response following all prompt guidelines.
If routing assumptions suggest specific topics or approaches, incorporate them naturally.

Guidelines:
- Be conversational and friendly
- Provide useful information when possible
- Ask clarifying questions if needed
- Keep responses concise but informative
- Apply structured formatting for professional presentation
"""
        
        # Enhanced AI model call with comprehensive prompts
        full_prompt = f"{system_prompt}\n\nSPECIFIC GUIDANCE:\n{ai_interactions}\n{templates}\n{context_memory}\n\nUSER REQUEST:\n{user_prompt}"
        
        response = self.ai_model.generate_content([
            full_prompt
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
                action_details={
                    "topic": assumptions.get('topic', 'general'),
                    "comprehensive_prompts_used": True
                },
                success_status=True
            )
        
        return {
            "status": "success",
            "message": response_text,
            "actions": [{"agent": self.agent_name, "action": "general_response"}]
        }
