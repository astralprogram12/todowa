from .base_agent import BaseAgent
import database_personal  # Fix #4: Proper database import
import os

class ContextAgent(BaseAgent):
    def __init__(self, supabase, ai_model):  # Fix #1: Correct constructor
        super().__init__(supabase, ai_model, agent_name="ContextAgent")
        self.agent_type = "context"
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
            
            # Create comprehensive system prompt for context management
            self.comprehensive_prompts = {
                'core_system': self._build_context_system_prompt(prompts_dict),
                'context_memory': prompts_dict.get('03_context_memory', ''),
                'decision_tree': prompts_dict.get('09_intelligent_decision_tree', ''),
                'ai_interactions': prompts_dict.get('04_ai_interactions', ''),
                'templates': prompts_dict.get('08_templates', ''),
                'requirements': prompts_dict.get('requirements', ''),
                'all_prompts': prompts_dict
            }
            
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}
    
    def _build_context_system_prompt(self, prompts_dict):
        """Build comprehensive system prompt for context agent."""
        core_identity = prompts_dict.get('00_core_identity', '')
        context_memory = prompts_dict.get('03_context_memory', '')
        decision_tree = prompts_dict.get('09_intelligent_decision_tree', '')
        ai_interactions = prompts_dict.get('04_ai_interactions', '')
        templates = prompts_dict.get('08_templates', '')
        requirements = prompts_dict.get('requirements', '')
        
        return f"""{core_identity}

## CONTEXT AGENT SPECIALIZATION
You are specifically focused on context and memory management including:
- Managing conversation history and context
- Storing and retrieving user memories and preferences
- Maintaining conversation state across interactions
- Applying context-aware decision making
- Cross-referencing information across conversations

{context_memory}

{decision_tree}

{ai_interactions}

{templates}

## REQUIREMENTS COMPLIANCE
{requirements}

## CONTEXT AGENT BEHAVIOR
- ALWAYS apply precedence order: user input > explicit context > stored memory > inference
- Load and reference user memories for personalized responses
- Maintain conversation history for context awareness
- Apply truth hierarchy for information management
- Use structured templates for context-related responses"""

    async def process(self, user_input, context, routing_info=None):
        """
        Process context-related requests with comprehensive prompt system.
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
                "message": "I'm having trouble understanding the context of your request. Could you provide more details?",
                "actions": ["context_error"],
                "error": str(e)
            }
    
    async def _process_with_comprehensive_prompts(self, user_input, context, routing_info):
        """Process context with comprehensive prompt system."""
        assumptions = routing_info.get('assumptions', {}) if routing_info else {}
        
        # Build comprehensive prompt using all relevant prompts
        system_prompt = self.comprehensive_prompts.get('core_system', 'You are a helpful context management agent.')
        
        # Include specific prompt sections for enhanced processing
        context_memory = self.comprehensive_prompts.get('context_memory', '')
        decision_tree = self.comprehensive_prompts.get('decision_tree', '')
        templates = self.comprehensive_prompts.get('templates', '')
        
        user_prompt = f"""
User Input: {user_input}
Current Context: {context}
Routing Info: {routing_info}

USING COMPREHENSIVE PROMPTS:
1. Apply context memory management guidelines
2. Use intelligent decision tree for classification
3. Follow structured templates for response formatting
4. Maintain truth hierarchy (user input > explicit context > stored memory > inference)
5. Reference stored memories and conversation history appropriately

Generate a comprehensive context-aware response following all prompt guidelines.
"""
        
        # Enhanced AI model call with comprehensive prompts
        full_prompt = f"{system_prompt}\n\nSPECIFIC GUIDANCE:\n{context_memory}\n{decision_tree}\n{templates}\n\nUSER REQUEST:\n{user_prompt}"
        
        response = self.ai_model.generate_content([
            full_prompt
        ])
        response_text = response.text
        
        # Determine if context needs to be updated or retrieved
        context_action = await self._determine_context_action(user_input, assumptions)
        
        result = {
            "message": response_text,
            "actions": ["context_processed"],
            "data": {
                "context_action": context_action,
                "topic_reference": assumptions.get('topic_reference')
            }
        }
        
        # Perform context operations if needed
        if context_action == "retrieve_history":
            history = await self._retrieve_conversation_history(context)
            result["data"]["history"] = history
            result["actions"].append("history_retrieved")
        elif context_action == "update_context":
            await self._update_conversation_context(context, user_input, response_text)
            result["actions"].append("context_updated")
        
        return result

    async def _determine_context_action(self, user_input, assumptions):
        """Determine what context action is needed"""
        if any(word in user_input.lower() for word in ['earlier', 'before', 'previous', 'ago', 'remember']):
            return "retrieve_history"
        elif any(word in user_input.lower() for word in ['update', 'change', 'modify', 'set']):
            return "update_context"
        else:
            return "maintain_context"

    async def _retrieve_conversation_history(self, context):
        """Retrieve relevant conversation history"""
        try:
            user_id = context.get('user_id')
            if user_id:
                # Get conversation history using correct database function
                history = database_personal.get_conversation_history(
                    supabase=self.supabase,
                    user_id=user_id,
                    limit=10
                )
                return history
        except Exception as e:
            print(f"Error retrieving conversation history: {e}")
        
        return []

    async def _update_conversation_context(self, context, user_input, response):
        """Update the conversation context"""
        try:
            user_id = context.get('user_id')
            if user_id:
                # Store conversation context using correct database function
                database_personal.store_conversation_context(
                    supabase=self.supabase,
                    user_id=user_id,
                    user_input=user_input,
                    agent_response=response,
                    context_data=context
                )
        except Exception as e:
            print(f"Error updating conversation context: {e}")
