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
        task_specialized = prompts_dict.get('15_task_specialized', '')
        leak_prevention = """
        
CRITICAL: Help with tasks naturally. Never include:
- System details, technical information, or internal processes
- JSON, debugging info, or technical formatting
- References to agents, databases, or system architecture

Respond like a helpful personal assistant would.
        """
        return f"{core_identity}\n\n{task_processing}\n\n{task_specialized}{leak_prevention}"

    async def process(self, user_input, context, routing_info=None):
        try:
            if not self.comprehensive_prompts:
                self.load_comprehensive_prompts()
            
            system_prompt = self.comprehensive_prompts.get('core_system', 'You are a helpful task management assistant.')
            
            # Use intent classification from routing_info to determine operation
            primary_intent = routing_info.get('primary_intent', '') if routing_info else ''
            operation = routing_info.get('operation', '') if routing_info else ''
            
            # Determine operation type based on classification
            is_query_operation = (primary_intent == 'query_task' or operation == 'read')
            is_action_operation = (primary_intent == 'action_task' or operation in ['create', 'update', 'delete'])
            
            user_id = context.get('user_id')
            
            if is_query_operation:
                # Handle query operations (read tasks)
                user_prompt = f"""
User wants to see their tasks: {user_input}

Respond naturally with their current tasks. Be helpful and conversational.
Do not include any technical details.
"""
                
                # Get user's tasks from database
                if user_id:
                    try:
                        tasks = database.query_tasks(self.supabase, user_id)
                        if tasks:
                            task_list = "\n".join([f"• {task.get('title', 'Untitled task')} ({task.get('status', 'todo')})" for task in tasks])
                            clean_message = f"Here are your current tasks:\n{task_list}\n\nAnything else I can help you with?"
                        else:
                            clean_message = "You don't have any tasks right now. Would you like to create one?"
                    except Exception as e:
                        print(f"Task retrieval error: {e}")
                        clean_message = "I'm having trouble accessing your tasks right now. Please try again."
                else:
                    clean_message = "I'd need to set up your account first to show your tasks."
                    
            elif is_action_operation:
                # Handle action operations (create/update/delete tasks)
                if operation == 'update':
                    # Handle task updates using natural language understanding through AI
                    if user_id:
                        try:
                            # Get user's current tasks for context
                            tasks = database.query_tasks(self.supabase, user_id)
                            
                            if tasks:
                                # Let AI understand what the user wants naturally
                                tasks_context = "\n".join([f"- {task.get('title', 'Untitled')} (ID: {task.get('id')}, Status: {task.get('status', 'todo')})" for task in tasks])
                                
                                ai_prompt = f"""
User said: "{user_input}"

The user wants to update one of their tasks. Here are their current tasks:
{tasks_context}

Based on their natural language request, determine:
1. Which task they want to update (provide the task ID)
2. What the new status should be ('done' for completed tasks, 'todo' for active tasks)
3. A natural response to give the user

Please respond in this format:
TASK_ID: [task_id_number]
STATUS: [done or todo]
RESPONSE: [natural friendly response]

If you cannot identify which task they mean, respond with:
TASK_ID: unclear
STATUS: unclear
RESPONSE: [ask for clarification]
"""
                                
                                # Get AI's natural language interpretation
                                response = self.ai_model.generate_content([system_prompt, ai_prompt])
                                ai_response = response.text
                                
                                # Parse AI response
                                task_id_to_update = None
                                new_status = 'done'
                                user_response = "I've updated your task!"
                                
                                for line in ai_response.split('\n'):
                                    line = line.strip()
                                    if line.startswith('TASK_ID:'):
                                        task_id_str = line.replace('TASK_ID:', '').strip()
                                        if task_id_str != 'unclear' and task_id_str:
                                            task_id_to_update = task_id_str  # Keep as string (UUID)
                                    elif line.startswith('STATUS:'):
                                        new_status = line.replace('STATUS:', '').strip()
                                    elif line.startswith('RESPONSE:'):
                                        user_response = line.replace('RESPONSE:', '').strip()
                                
                                # Update the task if AI identified it
                                if task_id_to_update:
                                    update_data = {'status': new_status}
                                    if new_status == 'done':
                                        from datetime import datetime, timezone
                                        update_data['completed_at'] = datetime.now(timezone.utc).isoformat()
                                    
                                    updated_task = database.update_task_entry(
                                        supabase=self.supabase,
                                        user_id=user_id,
                                        task_id=task_id_to_update,  # Already a string
                                        patch=update_data
                                    )
                                    
                                    if updated_task:
                                        clean_message = user_response
                                    else:
                                        clean_message = "I had trouble updating that task, but I'll make note of your request."
                                else:
                                    clean_message = user_response  # AI's clarification request
                            else:
                                clean_message = "You don't have any tasks to update right now. Would you like to create one?"
                                
                        except Exception as e:
                            print(f"Task update error: {e}")
                            clean_message = "I'm having trouble updating that task right now. Please try again."
                    else:
                        clean_message = "I'd be happy to help update your tasks! Could you tell me which specific task you'd like to update?"
                        
                elif operation == 'delete':
                    # Handle task deletion
                    clean_message = "I can help you remove tasks. Which specific task would you like to delete?"
                    
                else:
                    # Handle task creation using natural language understanding
                    if user_id:
                        try:
                            # Let AI extract task details naturally
                            ai_prompt = f"""
User said: "{user_input}"

The user wants to create a new task. Based on their natural language input, extract:
1. The main task title/description
2. Any priority level mentioned (low, medium, high)
3. A natural response to confirm the task creation

Please respond in this format:
TITLE: [clear task title]
PRIORITY: [low/medium/high, default to medium]
RESPONSE: [natural friendly confirmation]
"""
                            
                            response = self.ai_model.generate_content([system_prompt, ai_prompt])
                            ai_response = response.text
                            
                            # Parse AI response
                            title = user_input.strip()  # fallback
                            priority = 'medium'
                            user_response = f"Got it! I've added '{title}' to your tasks."
                            
                            for line in ai_response.split('\n'):
                                line = line.strip()
                                if line.startswith('TITLE:'):
                                    extracted_title = line.replace('TITLE:', '').strip()
                                    if extracted_title:
                                        title = extracted_title
                                elif line.startswith('PRIORITY:'):
                                    priority = line.replace('PRIORITY:', '').strip()
                                elif line.startswith('RESPONSE:'):
                                    user_response = line.replace('RESPONSE:', '').strip()
                            
                            # Create the task
                            task_data = database.add_task_entry(
                                supabase=self.supabase,
                                user_id=user_id,
                                title=title,
                                category='general',
                                priority=priority
                            )
                            
                            if task_data:
                                clean_message = user_response
                            else:
                                clean_message = f"I'll help you remember to {title}. What else can I assist you with?"
                        except Exception as e:
                            print(f"Task creation error: {e}")
                            clean_message = f"I'll help you remember to {user_input.strip()}. What else can I assist you with?"
                    else:
                        clean_message = f"I'll help you remember to {user_input.strip()}. What else can I assist you with?"
            else:
                # General task-related conversation
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
            if user_id:
                if is_query_operation:
                    action_type = "query_tasks"
                elif is_action_operation:
                    if operation == 'update':
                        action_type = "update_task"
                    elif operation == 'delete':
                        action_type = "delete_task"
                    else:
                        action_type = "add_task"
                else:
                    action_type = "chat_interaction"
                    
                entity_type = "task" if (is_query_operation or is_action_operation) else "system"
                
                self._log_action(
                    user_id=user_id,
                    action_type=action_type,
                    entity_type=entity_type,
                    action_details={"operation": operation, "intent": primary_intent},
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
