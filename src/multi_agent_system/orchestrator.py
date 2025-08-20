# orchestrator.py (FINAL, CONSOLIDATED VERSION)
# Uses the single, unified tool registry.

import asyncio
import traceback
import os
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

# --- [THE FIX] ---
# Import the one, true tool_registry from the correct, consolidated file.
# We also need to add the path correction to ensure it can be found.
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.append(project_root)
from enhanced_tools import tool_registry
import enhanced_ai_tools
# --- [END OF FIX] ---

from .agents import (
    BaseAgent, TaskAgent, ReminderAgent, SilentModeAgent,
    CoderAgent, AuditAgent, ExpertAgent, GuideAgent,
    IntentClassifierAgent , InformationAgent, GeneralAgent
)
from .response_combiner import ResponseCombiner

class Orchestrator:
    """Orchestrator using a unified tool system and transactional agent routing."""
    
    def __init__(self, supabase, ai_model):
        self.supabase = supabase
        self.ai_model = ai_model
        self.agents = {}
        self.user_contexts = {}
        self.intent_classifier = IntentClassifierAgent(supabase, ai_model)
        self._initialize_agents()
    
    def _initialize_agents(self):
        # ... (initializations are correct)
        self.agents['task'] = TaskAgent(self.supabase, self.ai_model)
        self.agents['reminder'] = ReminderAgent(self.supabase, self.ai_model)
        self.agents['silent_mode'] = SilentModeAgent(self.supabase, self.ai_model)
        self.agents['coder'] = CoderAgent(self.supabase, self.ai_model)
        self.agents['audit'] = AuditAgent(self.supabase, self.ai_model)
        self.agents['expert'] = ExpertAgent(self.supabase, self.ai_model)
        self.agents['guide'] = GuideAgent(self.supabase, self.ai_model)
        self.agents['information'] = InformationAgent(self.supabase, self.ai_model)
        self.agents['general'] = GeneralAgent(self.supabase, self.ai_model)

    def load_all_agent_prompts(self, prompts_dir: str):
        # ... (this function is correct)
        if not prompts_dir or not os.path.exists(prompts_dir): return
        print(f"Orchestrator is loading all agent prompts from {prompts_dir}...")
        all_agents = {**self.agents, 'intent_classifier': self.intent_classifier}
        for agent_name, agent in all_agents.items():
            if hasattr(agent, 'load_prompts'): agent.load_prompts(prompts_dir)
        print("...All agent prompts loaded.")

    async def process_user_input(self, user_id: str, user_input: str, phone_number: str, conversation_id: Optional[str] = None):
        """Processes user input and sends a reply using the unified tool registry."""
        final_response_dict = {}
        # --- [THE FIX] Set the context for all tools at the start of the request ---
        tool_registry.set_injection_context({"supabase": self.supabase, "user_id": user_id})
        # --- [END OF FIX] ---
        try:
            is_silent, session = await self._check_silent_mode(user_id)
            if is_silent and 'silent' not in user_input.lower():
                return {"message": "Silent mode is active. Message recorded.", "actions": []}

            # ... (rest of the agent processing logic is correct)
            context = await self._get_or_create_context(user_id, conversation_id)
            classification = await self._classify_user_input(user_input, context)
            agent_responses = []
            primary_agent_name = classification.get('primary_intent')
            if primary_agent_name == 'clarification_needed':
                final_response_dict = {"message": "I'm not quite sure what you mean. Could you please rephrase that?", "status": "clarification_needed"}
            elif primary_agent_name in self.agents:
                primary_response = await self.agents[primary_agent_name].process(user_input, context, classification)
                agent_responses.append(primary_response)
                if primary_response.get('status') == 'success':
                    for secondary_agent_name in classification.get('secondary_intents', []):
                        if secondary_agent_name in self.agents and secondary_agent_name != primary_agent_name:
                            secondary_response = await self.agents[secondary_agent_name].process(user_input, context, classification)
                            agent_responses.append(secondary_response)
            if agent_responses:
                final_response_dict = ResponseCombiner.combine_responses(agent_responses, classification)
            
            # Send the final reply using the tool registry
            message_to_send = final_response_dict.get('message')
            if message_to_send:
                print(f"Orchestrator sending final reply to {phone_number}: '{message_to_send}'")
                # --- [THE FIX] Execute the tool via the registry ---
                tool_registry.execute(
                    "send_reply_message",
                    phone_number=phone_number,
                    message=message_to_send
                )
            
            return final_response_dict

        except Exception as e:
            traceback.print_exc()
            error_message = "I encountered an error. My team has been notified."
            # Also try to send the error message back to the user via the registry
            tool_registry.execute("send_reply_message", phone_number=phone_number, message=error_message)
            return {"message": "An internal error occurred.", "error": str(e)}

    async def _check_silent_mode(self, user_id):
        # --- [THE FIX] Import from the single, consolidated 'database' file ---
        try:
            from database_personal import get_active_silent_session
            session = get_active_silent_session(self.supabase, user_id)
            return session is not None, session
        except Exception as e:
            print(f"ERROR in _check_silent_mode: {str(e)}")
            return False, None

    async def _classify_user_input(self, user_input, context):
        return await self.intent_classifier.classify_intent(user_input, context)

    async def _get_or_create_context(self, user_id, conversation_id=None):
        context_key = f"{user_id}:{conversation_id or 'default'}"
        if context_key not in self.user_contexts:
            self.user_contexts[context_key] = {
                'user_id': user_id, 'conversation_id': conversation_id, 'created_at': datetime.now().isoformat(),
                'last_agent': None, 'last_input': None, 'last_response': None, 'last_classification': None,
                'history': [], 'preferences': {}, 'memory': {}
            }
        context = self.user_contexts[context_key]
        if len(context['history']) > 10: context['history'] = context['history'][-10:]
        return context