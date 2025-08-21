from .base_agent import BaseAgent
import database_personal  # Fix #4: Proper database import
import os

class SilentAgent(BaseAgent):
    def __init__(self, supabase, ai_model):  # Fix #1: Correct constructor
        super().__init__(supabase, ai_model, agent_name="SilentAgent")
        self.agent_type = "silent"
        self.comprehensive_prompts = {}

    async def process(self, user_input, context, routing_info=None):
        """
        Process requests that require no response or silent actions.
        routing_info contains assumptions and confidence from IntentClassifierAgent.
        """
        try:
            # Use routing_info assumptions if available
            assumptions = routing_info.get('assumptions', {}) if routing_info else {}
            
            # Load comprehensive prompts
            if not self.comprehensive_prompts:
                self.load_comprehensive_prompts()
            
            system_prompt = self.comprehensive_prompts.get('core_system', "You are a silent agent that provides minimal responses.")
            
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

            # Fix #2: Correct AI model call with array parameter
            response = self.ai_model.generate_content([
                system_prompt, user_prompt
            ])
            response_text = response.text
            
            # Log the silent action
            user_id = context.get('user_id')
            if user_id:
                database_personal.log_action(
                    supabase=self.supabase,
                    user_id=user_id,
                    action_type="silent_processing",
                    entity_type="silent",
                    action_details={
                        "response_type": "analyzed"
                    },
                    success_status=True
                )
            
            # Determine response type based on analysis
            if "complete silence" in response_text.lower():
                # Return empty response for true silence
                return {
                    "message": "",
                    "actions": ["silent_mode"],
                    "silent": True
                }
            elif "acknowledgment" in response_text.lower():
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
            
            # Create comprehensive system prompt for silent agent
            self.comprehensive_prompts = {
                'core_system': self._build_silent_system_prompt(prompts_dict),
                'core_identity': prompts_dict.get('00_core_identity', ''),
                'silent_mode': prompts_dict.get('05_silent_mode', ''),
                'templates': prompts_dict.get('08_templates', ''),
                'requirements': prompts_dict.get('requirements', ''),
                'all_prompts': prompts_dict
            }
            
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}
    
    def _build_silent_system_prompt(self, prompts_dict):
        """Build comprehensive system prompt for silent agent."""
        core_identity = prompts_dict.get('00_core_identity', '')
        silent_mode = prompts_dict.get('05_silent_mode', '')
        templates = prompts_dict.get('08_templates', '')
        requirements = prompts_dict.get('requirements', '')
        
        return f"""{core_identity}

## SILENT AGENT SPECIALIZATION
You are specifically focused on silent processing and minimal responses:
- Determining when complete silence is appropriate
- Providing minimal acknowledgments when needed
- Processing requests that require no verbal response
- Managing silent actions and background processing

{silent_mode}

{templates}

## REQUIREMENTS COMPLIANCE
{requirements}

## SILENT AGENT BEHAVIOR
- ALWAYS minimize response verbosity
- Prefer non-verbal acknowledgments when appropriate
- Apply silent mode guidelines comprehensively
- Follow comprehensive prompt system for enhanced decision making"""
