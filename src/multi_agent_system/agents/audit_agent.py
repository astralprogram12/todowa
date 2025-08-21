from .base_agent import BaseAgent
import database_personal as database
import os
import re
from datetime import datetime, timedelta, timezone

class AuditAgent(BaseAgent):
    """Enhanced Audit Agent for version 3.5 that verifies truth in responses and confirms ambiguous inputs."""
    
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
5. Extract clean task descriptions from user input
6. Request clarification for any ambiguous inputs

Respond like a professional audit consultant who prioritizes TRUTH above all else.
        """
        return f"{core_identity}\n\n{audit_specialized}{leak_prevention}"
    
    async def extract_task_description(self, user_input):
        """
        Use AI to extract only the essential task description from user input.
        For example, from "remind me to eat in 5 minutes", extract just "eat"
        """
        system_prompt = """You are a task extraction expert. Extract ONLY the core task from the user's input.
        DO NOT include time expressions, prepositions, or unnecessary context.
        Return ONLY the core task/action phrase - nothing else.
        
        Examples:
        "remind me to buy groceries tomorrow" → "buy groceries"
        "I need to call mom at 5pm" → "call mom"
        "Please create a task to finish report by Friday" → "finish report"
        "Add a reminder to eat in 10 minutes" → "eat"
        """
        
        user_prompt = f"Extract the core task from: {user_input}"
        
        try:
            response = self.ai_model.generate_content([system_prompt, user_prompt])
            return response.text.strip()
        except Exception as e:
            print(f"Error extracting task: {e}")
            # Fallback to simple extraction if AI fails
            for phrase in ['remind me to', 'remind me about', 'set reminder for', 'reminder to', 'task to']:
                if phrase in user_input.lower():
                    return user_input[user_input.lower().find(phrase) + len(phrase):].strip()
            return user_input

    async def verify_time_accuracy(self, response_text, user_input):
        """
        Verify that time-related information in the response matches the user's request.
        This specifically checks for time discrepancies like "in 5 minutes" vs "tomorrow".
        """
        # Enhanced time pattern recognition for abbreviations
        time_phrases = [
            (r'in \s*(\d+)\s*m(in(ute)?s?)?\b', 'minutes'),  # matches "in 5m", "in 5min", "in 5mins", "in 5 minutes"
            (r'in \s*(\d+)\s*h(our)?s?\b', 'hours'),  # matches "in 2h", "in 2hr", "in 2hrs", "in 2 hours"
            (r'in \s*(\d+)\s*d(ay)?s?\b', 'days'),  # matches "in 3d", "in 3day", "in 3days", "in 3 days"
            (r'today at \s*(\d+)(:\d+)?\s*(am|pm)?\b', 'today'),
            (r'tomorrow at \s*(\d+)(:\d+)?\s*(am|pm)?\b', 'tomorrow'),
            (r'next week\b', 'next week'),
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
    
    async def check_for_ambiguity(self, user_input):
        """
        Check if the user input is ambiguous and needs clarification.
        """
        system_prompt = """You are an ambiguity detection expert. Determine if the user's input is ambiguous and requires clarification.
        Return "YES" if clarification is needed with a specific question to ask the user.
        Return "NO" if the input is clear.
        
        Examples of ambiguous inputs:
        - "Remind me later" (When is "later"?)
        - "Create a task for the thing" (What "thing"?)
        - "Meeting with the team" (Which team? When?)
        - "10m" (Is this 10 minutes or 10 meters?)
        """
        
        user_prompt = f"Analyze this input for ambiguity: {user_input}"
        
        try:
            response = self.ai_model.generate_content([system_prompt, user_prompt])
            result = response.text.strip()
            
            if result.startswith("YES"):
                # Extract the clarification question
                question = result.replace("YES", "", 1).strip()
                return True, question
            else:
                return False, None
        except Exception as e:
            print(f"Error checking ambiguity: {e}")
            return False, None
        
    async def process(self, user_input, context, routing_info=None):
        try:
            if not self.comprehensive_prompts:
                self.load_comprehensive_prompts()
            
            system_prompt = self.comprehensive_prompts.get('core_system', 'You are a helpful audit assistant.')
            
            # First, check for ambiguity in the input
            is_ambiguous, clarification_question = await self.check_for_ambiguity(user_input)
            
            if is_ambiguous and clarification_question:
                return {
                    "message": clarification_question,
                    "status": "needs_clarification"
                }
            
            # If it's a reminder, extract the core task
            if 'remind' in user_input.lower() or 'reminder' in user_input.lower() or 'task' in user_input.lower():
                # Extract the core task from the user input
                task_description = await self.extract_task_description(user_input)
                
                # Determine if this is an important task that needs follow-up
                task_importance_system = """You are a task importance analyzer. Determine if the given task is important enough to offer additional assistance.
                Rate the task from 1-5, where 1 is routine (eating, drinking water) and 5 is critical (urgent meeting, important deadline).
                Return ONLY the number."""
                
                task_importance_prompt = f"Rate the importance of this task: {task_description}"
                
                try:
                    importance_response = self.ai_model.generate_content([task_importance_system, task_importance_prompt])
                    importance_rating = int(importance_response.text.strip())
                except:
                    importance_rating = 3  # Default to medium importance
                
                # For important tasks (4-5), provide a different response style
                if importance_rating >= 4:
                    response_text = f"I've added '{task_description}' to your tasks. Would you like me to help you prepare for this or provide any additional reminders?"
                else:
                    # For routine tasks, keep it simple
                    response_text = f"Got it! I've added '{task_description}' to your tasks."
                
                clean_message = response_text
            else:
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
