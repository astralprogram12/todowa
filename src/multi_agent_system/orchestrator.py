# orchestrator.py
# Central orchestrator for the multi-agent system
# UPDATED VERSION with AI-powered intent classification

import asyncio
import traceback
import os
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

# We import the communication tool directly to use it for sending replies.
from .tool_collections.communication_tools import send_reply_message

# UPDATED IMPORTS - Added new AI classification components
from .agents import (
    BaseAgent, TaskAgent, ReminderAgent, SilentModeAgent,
    CoderAgent, AuditAgent, ExpertAgent, GuideAgent,
    IntentClassifierAgent 
)
from .response_combiner import ResponseCombiner  # NEW

class Orchestrator:
    """Central orchestrator for the multi-agent system with AI-powered intent classification."""
    
    def __init__(self, supabase, ai_model):
        """Initialize the orchestrator with AI classification capability."""
        self.supabase = supabase
        self.ai_model = ai_model
        self.agents = {}
        self.user_contexts = {}
        
        # NEW: Initialize the AI intent classifier
        self.intent_classifier = IntentClassifierAgent(supabase, ai_model)
        
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
        
        # Load prompts for all agents including the new classifier
        all_agents = {**self.agents, 'intent_classifier': self.intent_classifier}
        
        for agent_name, agent in all_agents.items():
            if hasattr(agent, 'load_prompts'):
                agent.load_prompts(prompts_dir)
        print("...All agent prompts loaded.")

    async def process_user_input(self, user_id: str, user_input: str, phone_number: str, conversation_id: Optional[str] = None):
        """Process user input with AI-powered multi-agent routing and ALWAYS send reply."""
        final_response_dict = {}
        try:
            # High-priority check for silent mode (unchanged)
            is_silent, session = await self._check_silent_mode(user_id)
            if is_silent and 'silent' not in user_input.lower():
                return {"message": "Silent mode is active. Message recorded.", "actions": []}

            # NEW: AI-powered classification instead of keyword matching
            context = await self._get_or_create_context(user_id, conversation_id)
            classification = await self._classify_user_input(user_input, context)
            
            print(f"AI Classification: {classification}")
            
            # NEW: Handle multiple agents based on AI classification
            agent_responses = []
            
            # Process primary intent
            primary_agent = classification['primary_intent']
            if primary_agent in self.agents:
                print(f"Processing with primary agent: {primary_agent}")
                response = await self.agents[primary_agent].process(
                    user_input, context, classification
                )
                agent_responses.append(response)
            
            # Process secondary intents (if any)
            for secondary_agent in classification.get('secondary_intents', []):
                if secondary_agent in self.agents and secondary_agent != primary_agent:
                    print(f"Processing with secondary agent: {secondary_agent}")
                    response = await self.agents[secondary_agent].process(
                        user_input, context, classification
                    )
                    agent_responses.append(response)
            
            # Combine all agent responses intelligently
            if agent_responses:
                final_response_dict = ResponseCombiner.combine_responses(
                    agent_responses, classification
                )
            else:
                # Confident fallback response (never confusion)
                final_response_dict = {
                    "message": "I'll help you with that right away.",
                    "status": "success",
                    "confidence": 0.6
                }

            # Update context for next interaction
            context['last_agent'] = classification['primary_intent']
            context['last_input'] = user_input
            context['last_response'] = final_response_dict.get('message')
            context['last_classification'] = classification

            # --- ALWAYS SEND THE REPLY (unless silent mode) ---
            message_to_send = final_response_dict.get('message')
            if message_to_send:
                print(f"Orchestrator sending final reply to {phone_number}: '{message_to_send}'")
                send_reply_message(
                    supabase_client=self.supabase, 
                    user_id=user_id, 
                    phone_number=phone_number, 
                    message=message_to_send
                )
            
            return final_response_dict

        except Exception as e:
            traceback.print_exc()
            error_message = "I encountered an error while processing your request. Please try again."
            send_reply_message(self.supabase, user_id, phone_number, error_message)
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
        """AI-powered intent classification - REPLACES old keyword system"""
        return await self.intent_classifier.classify_intent(user_input, context)

    async def _get_or_create_context(self, user_id, conversation_id=None):
        """Get or create the context for this user and conversation."""
        context_key = f"{user_id}:{conversation_id or 'default'}"
        if context_key not in self.user_contexts:
            self.user_contexts[context_key] = {
                'user_id': user_id, 
                'conversation_id': conversation_id, 
                'created_at': datetime.now().isoformat(),
                'last_agent': None, 
                'last_input': None, 
                'last_response': None, 
                'last_classification': None,
                'history': [],  # NEW: Track conversation history
                'preferences': {},  # NEW: User preferences
                'memory': {}
            }
        
        # Update conversation history
        context = self.user_contexts[context_key]
        if len(context['history']) > 10:  # Keep last 10 interactions
            context['history'] = context['history'][-10:]
            
        return context