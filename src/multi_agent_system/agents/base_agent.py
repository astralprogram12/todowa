# base_agent.py
# Clean version that prevents information leakage

import database_personal as database
import os
import re
from datetime import datetime

class BaseAgent:
    """Base agent class with leak-proof architecture and conversation memory for v3.5."""

    def __init__(self, supabase, ai_model, agent_name=None):
        """Initialize the base agent with correct parameters."""
        self.supabase = supabase
        self.ai_model = ai_model
        self.agent_name = agent_name or self.__class__.__name__
        self.prompts = {}
        self.comprehensive_prompts = {}
        
    def load_comprehensive_prompts(self):
        """Loads all prompts relative to the project's structure."""
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
            else:
                print(f"WARNING: Prompts directory not found at {v1_dir}")

            self.comprehensive_prompts = {
                'core_system': self._build_base_system_prompt(prompts_dict)
            }
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}

    def _build_base_system_prompt(self, prompts_dict):
        """Builds the system prompt for the base agent."""
        core_identity = prompts_dict.get('00_core_identity', 'You are a helpful assistant.')
        # CRITICAL: Add leak prevention instructions
        leak_prevention = """
        
IMPORTANT: Your response must be ONLY user-friendly text. Never include:
        - Technical details, system information, or internal data
        - JSON structures, code blocks, or technical formatting
        - Action logs, debugging info, or system status
        - References to internal processes, agents, or system architecture
        
        Respond as a helpful assistant would in natural conversation.
        """
        return f"{core_identity}{leak_prevention}"
    
    def _clean_response(self, response_text):
        """Clean response text to prevent system leaks."""
        if not response_text:
            return ""
        
        # Remove JSON structures
        clean_message = re.sub(r'\{[^}]*\}', '', response_text)
        
        # Remove obvious system references
        system_terms = [
            'actions":', 'status":', 'entity_type', 'action_type', 
            'supabase', 'database', 'agent', 'routing', 'classification',
            'error:', 'ERROR:', 'DEBUG:', 'INFO:', 'WARNING:'
        ]
        
        for term in system_terms:
            clean_message = re.sub(rf'.*{re.escape(term)}.*\n?', '', clean_message, flags=re.IGNORECASE)
        
        # Remove multiple whitespace and clean up
        clean_message = re.sub(r'\s+', ' ', clean_message).strip()
        
        return clean_message
    
    def _update_conversation_memory(self, context, user_input, response_text):
        """Update the conversation memory with the latest exchange."""
        if not context:
            return
            
        # Initialize memory if it doesn't exist
        if 'conversation_memory' not in context:
            context['conversation_memory'] = []
            
        # Add the new exchange
        timestamp = datetime.now().isoformat()
        exchange = {
            'timestamp': timestamp,
            'user': user_input,
            'assistant': response_text
        }
        
        context['conversation_memory'].append(exchange)
        
        # Keep only the last 10 exchanges
        if len(context['conversation_memory']) > 10:
            context['conversation_memory'] = context['conversation_memory'][-10:]
            
    def _get_conversation_history(self, context):
        """Get formatted conversation history for context."""
        if not context or 'conversation_memory' not in context:
            return ""
            
        history = context.get('conversation_memory', [])
        if not history:
            return ""
            
        formatted_history = "Recent Conversation History:\n"
        for exchange in history:
            formatted_history += f"User: {exchange.get('user', '')}\n"
            formatted_history += f"Assistant: {exchange.get('assistant', '')}\n\n"
            
        return formatted_history
        
    async def process(self, user_input, context, routing_info=None):
        """Process user input and return a response."""
        raise NotImplementedError("Subclasses must implement this method")
    
    def _log_action(self, user_id, action_type, entity_type, entity_id=None, 
                   action_details=None, success_status=True, error_details=None):
        """Log an action performed by the agent."""
        try:
            database.log_action(
                supabase=self.supabase,
                user_id=user_id,
                action_type=action_type,
                entity_type=entity_type,
                entity_id=entity_id,
                action_details=action_details,
                success_status=success_status,
                error_details=error_details
            )
        except Exception as e:
            print(f"Logging error in {self.agent_name}: {e}")
