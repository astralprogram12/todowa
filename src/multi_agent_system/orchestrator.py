# orchestrator.py
# Central orchestrator for the multi-agent system

import asyncio
import traceback
import os
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

# We import the communication tool directly to use it for sending replies.
from .tool_collections.communication_tools import send_reply_message

from .agents import (
    BaseAgent, TaskAgent, ReminderAgent, SilentModeAgent,
    CoderAgent, AuditAgent, ExpertAgent, GuideAgent
)

class Orchestrator:
    """Central orchestrator for the multi-agent system."""
    
    def __init__(self, supabase, ai_model):
        """Initialize the orchestrator."""
        self.supabase = supabase
        self.ai_model = ai_model
        self.agents = {}
        self.user_contexts = {}
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize all specialized agents."""
        self.agents['task'] = TaskAgent(self.supabase, self.ai_model)
        self.agents['reminder'] = ReminderAgent(self.supabase, self.ai_model)
        self.agents['silent_mode'] = SilentModeAgent(self.supabase, self.ai_model)
        self.agents['coder'] = CoderAgent(self.supabase, self.ai_model)
        self.agents['audit'] = AuditAgent(self.supabase, self.ai_model)
        self.agents['expert'] = ExpertAgent(self.supabase, self.ai_model)
        self.agents['guide'] = GuideAgent(self.supabase, self.ai_model)

    def load_all_agent_prompts(self, prompts_dir: str):
        """Loads system prompts from files into each respective agent."""
        if not prompts_dir or not os.path.exists(prompts_dir):
            print(f"WARNING: Prompts directory not found at {prompts_dir}.")
            return
        print(f"Orchestrator is loading all agent prompts from {prompts_dir}...")
        for agent_name, agent in self.agents.items():
            if hasattr(agent, 'load_prompts'):
                agent.load_prompts(prompts_dir)
        print("...All agent prompts loaded.")

    # --- [THE FIX] Added 'phone_number' to the function signature ---
    async def process_user_input(self, user_id: str, user_input: str, phone_number: str, conversation_id: Optional[str] = None):
        """Process user input, route to an agent, and ALWAYS send the reply."""
        final_response_dict = {}
        try:
            # High-priority check for silent mode
            is_silent, session = await self._check_silent_mode(user_id)
            if is_silent and 'silent' not in user_input.lower():
                # We do not send a reply in silent mode
                return {"message": "Silent mode is active. Message recorded.", "actions": []}

            # Normal agent processing to determine a response
            context = await self._get_or_create_context(user_id, conversation_id)
            context['last_input'] = user_input
            
            classification = await self._classify_user_input(user_input, context)
            agent_type = classification['agent_type']
            
            # --- This is where the AI "thinks" of a response ---
            if classification['confidence'] >= 0.4:
                if agent_type in self.agents:
                    # The responsible agent processes the request
                    final_response_dict = await self.agents[agent_type].process(user_input, context)
                else:
                    final_response_dict = {"message": "I'm not sure how to handle that request right now."}
            else:
                final_response_dict = {"message": "I'm not sure I understand. Could you please clarify?"}
            # --- End of AI thinking ---

            # --- ALWAYS SEND THE REPLY (unless silent mode) ---
            message_to_send = final_response_dict.get('message')
            if message_to_send:
                print(f"Orchestrator sending final reply to {phone_number}: '{message_to_send}'")
                # We call the communication tool directly to send the message.
                await send_reply_message(
                    supabase_client=self.supabase, 
                    user_id=user_id, 
                    phone_number=phone_number, 
                    message=message_to_send
                )
            # --- End of sending reply ---

            # Return the agent's internal thoughts for logging in Vercel
            return final_response_dict

        except Exception as e:
            traceback.print_exc()
            error_message = "I encountered an error while processing your request. Please try again."
            # Also try to send the error message back to the user
            await send_reply_message(self.supabase, user_id, phone_number, error_message)
            return {"message": "An internal error occurred.", "error": str(e)}

    async def _check_silent_mode(self, user_id):
        """Check if the user is in silent mode. Returns (bool, session_data)."""
        try:
            from database_silent import get_active_silent_session
            session = get_active_silent_session(self.supabase, user_id)
            return session is not None, session
        except Exception as e:
            print(f"ERROR in _check_silent_mode: {str(e)}")
            return False, None

    async def _classify_user_input(self, user_input, context):
        """Classify the user input to determine the appropriate agent."""
        user_input_lower = user_input.lower()
        patterns = {
            'task': ['task', 'todo', 'to-do', 'to do', 'add task', 'create task', 'new task', 'complete task', 'finish task'],
            'reminder': ['remind', 'reminder', 'alert', 'notify', 'at time', 'on date'],
            'silent_mode': ['silent mode', 'go silent', 'stop replying', 'no replies', 'exit silent', 'end silent'],
            'coder': ['code', 'script', 'program', 'function', 'coding', 'programming', 'develop'],
            'audit': ['activity', 'log', 'history', 'what did i', 'what have i', 'show me what'],
            'expert': ['advice', 'best way', 'how should i', 'tips', 'strategy', 'recommend'],
            'guide': ['how to', 'guide', 'steps', 'instructions', 'process', 'explain how']
        }
        for agent_type, keywords in patterns.items():
            for keyword in keywords:
                if f" {keyword} " in f" {user_input_lower} " or user_input_lower.startswith(keyword + ' ') or user_input_lower.endswith(' ' + keyword):
                    return {"classification": agent_type, "agent_type": agent_type, "confidence": 0.9, "reasoning": f"Strong match with '{keyword}' pattern"}
        scores = {agent: 0.0 for agent in patterns.keys()}
        for agent_type, keywords in patterns.items():
            for keyword in keywords:
                if keyword in user_input_lower: scores[agent_type] += 0.3
        last_agent = context.get('last_agent')
        if last_agent and last_agent in scores: scores[last_agent] += 0.1
        highest_score = max(scores.values())
        if highest_score > 0:
            best_agent = max(scores.items(), key=lambda x: x[1])[0]
            return {"classification": best_agent, "agent_type": best_agent, "confidence": highest_score, "reasoning": "Best match based on keyword patterns"}
        return {"classification": "task", "agent_type": "task", "confidence": 0.3, "reasoning": "No clear pattern match, defaulting to task agent"}

    async def _get_or_create_context(self, user_id, conversation_id=None):
        """Get or create the context for this user and conversation."""
        context_key = f"{user_id}:{conversation_id or 'default'}"
        if context_key not in self.user_contexts:
            self.user_contexts[context_key] = {
                'user_id': user_id, 'conversation_id': conversation_id, 'created_at': datetime.now().isoformat(),
                'last_agent': None, 'last_input': None, 'last_response': None, 'memory': {}
            }
        return self.user_contexts[context_key]