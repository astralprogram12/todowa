from .base_agent import BaseAgent
import database_personal as database
import os
import random

class GeneralAgent(BaseAgent):
    """Enhanced General Agent for version 3.5 with adaptive responses and conversation memory."""
    
    # Add some conversational templates
    GREETINGS = [
        "Hello there! How can I help you today?",
        "Hi! What can I assist you with?",
        "Hey! How can I make your day better?",
        "Greetings! What would you like help with?",
        "Hi there! I'm here to help. What do you need?"
    ]
    
    AFFIRMATIONS = [
        "I understand.",
        "I see what you mean.",
        "That makes sense.",
        "I get it.",
        "I follow you."
    ]
    
    CONTINUERS = [
        "Is there anything else you'd like to talk about?",
        "What else can I help you with today?",
        "Do you need assistance with anything else?",
        "Is there something else on your mind?",
        "Anything else you'd like to discuss?"
    ]
    
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model, agent_name="GeneralAgent")
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
                'core_system': self._build_general_system_prompt(prompts_dict)
            }
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}
    
    def _build_general_system_prompt(self, prompts_dict):
        core_identity = prompts_dict.get('00_core_identity', 'You are a friendly, helpful assistant.')
        ai_interactions = prompts_dict.get('04_ai_interactions', '')
        general_specialized = prompts_dict.get('18_general_specialized', '')
        leak_prevention = """
        
CRITICAL: Be conversational and natural. Never include:
- System details, technical information, or internal processes
- JSON, debugging info, or technical formatting
- References to agents, databases, or system architecture

You are a CONVERSATIONAL AGENT designed to:
1. Have natural, engaging conversations
2. Show empathy and understanding
3. Use appropriate small talk and transitions
4. Respond naturally to casual questions
5. Maintain context and flow in conversations
6. Adapt your response style based on task importance

Respond like a helpful, knowledgeable friend in natural conversation.
        """
        return f"{core_identity}\n\n{ai_interactions}\n\n{general_specialized}{leak_prevention}"

    def handle_greeting(self, user_input):
        """
        Check if user input is a greeting and return an appropriate response.
        """
        greeting_patterns = ['hi', 'hello', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening']
        
        if any(pattern in user_input.lower() for pattern in greeting_patterns):
            return random.choice(self.GREETINGS)
        return None
    
    def get_conversation_enhancer(self):
        """
        Return a random conversation enhancer to make responses more natural.
        """
        return random.choice(self.CONTINUERS)
        
    async def analyze_task_importance(self, user_input):
        """
        Analyze if the input contains an important task that needs special handling.
        """
        # Skip if doesn't look like a task
        if not any(word in user_input.lower() for word in ['task', 'remind', 'meeting', 'call', 'appointment', 'deadline']):
            return False, None
            
        system_prompt = """You are a task importance analyzer. Determine if the user's message contains an important task.
        Important tasks include business meetings, urgent deadlines, critical appointments, etc.
        Routine tasks include eating, drinking water, checking email, etc.
        
        Return "IMPORTANT" if this is an important task that requires special handling.
        Return "ROUTINE" if this is a routine, everyday task.
        If there's no task mentioned, return "NO_TASK".
        """
        
        user_prompt = f"Analyze this message for task importance: {user_input}"
        
        try:
            response = self.ai_model.generate_content([system_prompt, user_prompt])
            result = response.text.strip().upper()
            
            if result == "IMPORTANT":
                return True, user_input
            else:
                return False, None
        except Exception as e:
            print(f"Error analyzing task importance: {e}")
            return False, None
    
    async def generate_adaptive_response(self, user_input, is_important_task):
        """
        Generate a response that adapts to the importance of the task.
        """
        if is_important_task:
            system_prompt = """You are a helpful assistant. The user has mentioned something that appears to be an important task.
            Respond with a helpful message that offers additional assistance, such as:
            1. Asking if they need any reminders
            2. Offering to help with preparation or first steps
            3. Suggesting related information that might be helpful
            
            Be conversational and helpful, not pushy or overly formal.
            """
        else:
            system_prompt = """You are a helpful assistant. Respond naturally to the user's message.
            Be conversational, friendly and concise.
            """
            
        user_prompt = f"User message: {user_input}"
        
        try:
            response = self.ai_model.generate_content([system_prompt, user_prompt])
            return response.text.strip()
        except Exception as e:
            print(f"Error generating adaptive response: {e}")
            return "I'm here to help with that. What would you like me to do?"
        
    async def process(self, user_input, context, routing_info=None):
        try:
            if not self.comprehensive_prompts:
                self.load_comprehensive_prompts()
            
            system_prompt = self.comprehensive_prompts.get('core_system', 'You are a friendly, helpful assistant.')
            
            # Get conversation history
            conversation_history = self._get_conversation_history(context)
            
            # Check for direct greetings first
            greeting_response = self.handle_greeting(user_input)
            if greeting_response and len(user_input.split()) <= 3:  # Simple greeting
                clean_message = greeting_response
            else:
                # Check if this contains an important task
                is_important, task_text = await self.analyze_task_importance(user_input)
                
                if is_important:
                    # Generate an adaptive response for important tasks
                    response_text = await self.generate_adaptive_response(user_input, True)
                    clean_message = self._clean_response(response_text)
                else:
                    # Regular processing for non-important messages
                    user_prompt = f"""
{conversation_history}

User said: {user_input}

Respond in a natural, conversational way. Be helpful, engaging and friendly.
Use a warm, personable tone and show empathy where appropriate.
Provide thoughtful responses rather than just quick answers.
Do not include any technical details or system information.
"""
                    
                    # Make AI call (synchronous)
                    response = self.ai_model.generate_content([system_prompt, user_prompt])
                    response_text = response.text
                    
                    # Clean the response to prevent leaks
                    clean_message = self._clean_response(response_text)
                    
                    # Add conversation enhancers for non-question responses
                    if not any(q in user_input.lower() for q in ['?', 'what', 'how', 'when', 'where', 'why', 'who']):
                        # For statements, sometimes add an affirmation
                        if random.random() < 0.3:  # 30% chance
                            affirmation = random.choice(self.AFFIRMATIONS)
                            clean_message = f"{affirmation} {clean_message}"
                    
                    # Add conversation continuers sometimes
                    if random.random() < 0.4 and not clean_message.endswith('?'):  # 40% chance
                        clean_message = f"{clean_message} {self.get_conversation_enhancer()}"
            
            # Update conversation memory
            self._update_conversation_memory(context, user_input, clean_message)
            
            # Log action (internal only)
            user_id = context.get('user_id')
            if user_id:
                self._log_action(
                    user_id=user_id,
                    action_type="chat_interaction",
                    entity_type="system",
                    action_details={"type": "general_conversation"},
                    success_status=True
                )
            
            # Return ONLY clean user message - no technical details
            return {
                "message": clean_message
            }
            
        except Exception as e:
            print(f"ERROR in GeneralAgent: {e}")
            return {
                "message": "I'm here to help! How can I assist you today?"
            }
