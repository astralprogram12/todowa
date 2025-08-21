from .base_agent import BaseAgent
import database_personal as database
import os
import re
from datetime import datetime, timedelta, timezone

class AuditAgent(BaseAgent):
    """Enhanced Audit Agent for version 3.0 that verifies truth in responses."""
    
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model, agent_name="AuditAgent")
        self.comprehensive_prompts = {}

    def load_comprehensive_prompts(self):
        try:
            prompts_dict = {}
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
            v1_dir = os.path.join(project_root, "prompts", "v1")
            
            if os.path.exists(v1_dir):
                for file_name in os.listdir(v1_dir):
                    if file_name.endswith('.md'):
                        prompt_name = file_name.replace('.md', '')
                        file_path = os.path.join(v1_dir, file_name)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            prompts_dict[prompt_name] = f.read()

            self.comprehensive_prompts = {
                'core_system': self._build_audit_system_prompt(prompts_dict)
            }
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}
    
    def _build_audit_system_prompt(self, prompts_dict):
        core_identity = prompts_dict.get('00_core_identity', 'You are a helpful audit assistant.')
        audit_specialized = prompts_dict.get('13_audit_specialized', '')
        leak_prevention = """
        
CRITICAL: Provide audit information naturally. Never include:
- System details, technical information, or internal processes
- JSON, debugging info, or technical formatting
- References to agents, databases, or system architecture

You are a VERIFICATION AGENT designed to:
1. Check responses for factual accuracy
2. Verify that time-related information is correct (e.g., "in 5 minutes" vs "tomorrow")
3. Ensure all claims made are true and supported
4. Flag any potential inconsistencies or errors

Respond like a professional audit consultant who prioritizes TRUTH above all else.
        """
        return f"{core_identity}\n\n{audit_specialized}{leak_prevention}"

    async def verify_time_accuracy(self, response_text, user_input):
        """
        Verify that time-related information in the response matches the user's request.
        This specifically checks for time discrepancies like "in 5 minutes" vs "tomorrow".
        """
        # Check if user input contains time-related phrases
        time_phrases = [
            (r'in (\d+) minute', 'minutes'),
            (r'in (\d+) hour', 'hours'),
            (r'in (\d+) day', 'days'),
            (r'today at (\d+)', 'today'),
            (r'tomorrow at (\d+)', 'tomorrow'),
            (r'next week', 'next week'),
        ]
        
        user_time_spec = None
        for pattern, time_type in time_phrases:
            match = re.search(pattern, user_input.lower())
            if match:
                user_time_spec = (time_type, match.group(0))
                break
        
        if not user_time_spec:
            return response_text  # No time specification to verify
        
        # Check if response contains a different time than specified
        incorrect_time = False
        if user_time_spec[0] == 'minutes' and 'tomorrow' in response_text.lower():
            incorrect_time = True
        elif user_time_spec[0] == 'hours' and 'tomorrow' in response_text.lower():
            incorrect_time = True
        elif user_time_spec[0] == 'today' and 'tomorrow' in response_text.lower():
            incorrect_time = True
            
        if incorrect_time:
            # Generate a corrected response
            system_prompt = """You are a correction agent. Fix the following response to accurately reflect the time specified in the user's request.
            DO NOT mention that you're correcting anything - simply provide the corrected response."""
            
            user_prompt = f"""User request: {user_input}
            Original response: {response_text}
            
            The time mentioned in the response does not match what the user requested. 
            Provide a corrected version that accurately reflects the user's requested time."""
            
            try:
                correction = self.ai_model.generate_content([system_prompt, user_prompt])
                return correction.text
            except Exception as e:
                print(f"Error generating time correction: {e}")
                return response_text
        
        return response_text
        
    async def process(self, user_input, context, routing_info=None):
        try:
            if not self.comprehensive_prompts:
                self.load_comprehensive_prompts()
            
            system_prompt = self.comprehensive_prompts.get('core_system', 'You are a helpful audit assistant.')
            
            user_prompt = f"""
User has an audit-related question: {user_input}

Provide helpful audit-related information. Be professional and thorough.
Do not include any technical details or system information.
"""
            
            # Make AI call (synchronous)
            response = self.ai_model.generate_content([system_prompt, user_prompt])
            response_text = response.text
            
            # Clean the response to prevent leaks
            clean_message = self._clean_response(response_text)
            
            # Verify time accuracy in responses
            if 'remind' in user_input.lower() or 'reminder' in user_input.lower():
                clean_message = await self.verify_time_accuracy(clean_message, user_input)
            
            # Log action (internal only)
            user_id = context.get('user_id')
            if user_id:
                self._log_action(
                    user_id=user_id,
                    action_type="chat_interaction",
                    entity_type="system",
                    action_details={"type": "audit_request"},
                    success_status=True
                )
            
            # Return ONLY clean user message
            return {
                "message": clean_message
            }
            
        except Exception as e:
            print(f"ERROR in AuditAgent: {e}")
            return {
                "message": "I can help with audit-related questions. What specific audit topic would you like assistance with?"
            }
