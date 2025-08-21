from .base_agent import BaseAgent
import database_personal as database
import os

class TaskAgent(BaseAgent):
    """Agent for task management without technical leaks."""
    
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model, agent_name="TaskAgent")
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
                'core_system': self._build_task_system_prompt(prompts_dict)
            }
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}

    def _build_task_system_prompt(self, prompts_dict):
        core_identity = prompts_dict.get('00_core_identity', 'You are a helpful task management assistant.')
        task_processing = prompts_dict.get('02_task_processing', '')
        leak_prevention = """
        
CRITICAL: Help with tasks naturally. Never include:
- System details, technical information, or internal processes
- JSON, debugging info, or technical formatting
- References to agents, databases, or system architecture

Respond like a helpful personal assistant would.
        """
        return f"{core_identity}\n\n{task_processing}{leak_prevention}"

    async def process(self, user_input, context, routing_info=None):
        try:
            if not self.comprehensive_prompts:
                self.load_comprehensive_prompts()
            
            system_prompt = self.comprehensive_prompts.get('core_system', 'You are a helpful task management assistant.')
            
            # Determine if this is task creation
            is_creating_task = any(phrase in user_input.lower() for phrase in 
                ['need to', 'have to', 'must', 'should', 'remind me', "don't forget", 'task'])
            
            if is_creating_task:
                user_prompt = f"""
User wants to create a task: {user_input}

Help them with their task. Respond naturally like a personal assistant.
Do not include any technical details.
"""
                
                # Make AI call (synchronous)
                response = self.ai_model.generate_content([system_prompt, user_prompt])
                response_text = response.text
                
                # Extract task details for internal processing
                title = user_input.strip()
                
                # Create the task internally
                user_id = context.get('user_id')
                if user_id:
                    try:
                        task_data = database.add_task_entry(
                            supabase=self.supabase,
                            user_id=user_id,
                            title=title,
                            category='general',
                            priority='medium'
                        )
                        
                        if task_data:
                            clean_message = f"Got it! I've added '{title}' to your tasks. Anything else you need help with?"
                        else:
                            clean_message = f"I'll help you remember to {title}. What else can I assist you with?"
                    except Exception as e:
                        print(f"Task creation error: {e}")
                        clean_message = f"I'll help you remember to {title}. What else can I assist you with?"
                else:
                    clean_message = f"I'll help you remember to {title}. What else can I assist you with?"
            else:
                user_prompt = f"""
User said: {user_input}

This is about task management. Respond naturally and helpfully.
Do not include any technical details.
"""
                
                # Make AI call (synchronous)
                response = self.ai_model.generate_content([system_prompt, user_prompt])
                response_text = response.text
                clean_message = self._clean_response(response_text)
            
            # Log action (internal only)
            user_id = context.get('user_id')
            if user_id:
                self._log_action(
                    user_id=user_id,
                    action_type="add_task" if is_creating_task else "chat_interaction",
                    entity_type="task" if is_creating_task else "system",
                    action_details={"type": "task_management"},
                    success_status=True
                )
            
            # Return ONLY clean user message
            return {
                "message": clean_message
            }
            
        except Exception as e:
            print(f"ERROR in TaskAgent: {e}")
            return {
                "message": "I'd be happy to help you with your tasks! What would you like to work on?"
            }
