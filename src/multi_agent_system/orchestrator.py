import asyncio
import traceback
import os
from datetime import datetime # Added missing import
from typing import Dict, Any, Optional, List, Tuple
from .tool_collections.communication_tools import send_reply_message

from .agents import (
    BaseAgent, TaskAgent, ReminderAgent, SilentModeAgent,
    CoderAgent, AuditAgent, ExpertAgent, GuideAgent
)

class Orchestrator:
    """Central orchestrator for the multi-agent system."""
    
    def __init__(self, supabase, ai_model):
        """Initialize the orchestrator with required dependencies."""
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

    # --- [NEW METHOD] ---
    # This method contains the slow file-reading logic.
    def load_all_agent_prompts(self, prompts_dir: str):
        """Loads system prompts from files into each respective agent."""
        if not prompts_dir or not os.path.exists(prompts_dir):
            print(f"WARNING: Prompts directory not found at {prompts_dir}. Agents will use default prompts.")
            return

        print(f"Orchestrator is loading all agent prompts from {prompts_dir}...")
        for agent_name, agent in self.agents.items():
            if hasattr(agent, 'load_prompts'):
                # Assuming 'load_prompts' is a method on your agent classes
                agent.load_prompts(prompts_dir)
        print("...All agent prompts loaded.")
    # --- [END NEW METHOD] ---
    
    async def process_user_input(self, user_id, user_input, conversation_id=None):
        """Process user input and route to the appropriate agent."""
        # ... (rest of your orchestrator logic remains the same)
        # ... (I've included the full correct class below for clarity)
        try:
            is_silent = await self._check_silent_mode(user_id)
            if is_silent and 'silent' not in user_input.lower():
                return {
                    "message": "Currently in silent mode. Your message has been recorded.",
                    "is_silent": True, "actions": []
                }
            
            context = await self._get_or_create_context(user_id, conversation_id)
            context['last_input'] = user_input
            
            classification = await self._classify_user_input(user_input, context)
            agent_type = classification['agent_type']
            
            actions = [{"type": "classification", "agent": agent_type, "confidence": classification['confidence'], "reasoning": classification['reasoning']}]
            
            if classification['confidence'] >= 0.4:
                if agent_type in self.agents:
                    agent_response = await self.agents[agent_type].process(user_input, context)
                    context['last_agent'] = agent_type
                    context['last_response'] = agent_response
                    response = {"message": agent_response.get('message', 'I processed your request.'), "agent": agent_type, "actions": actions}
                    for key, value in agent_response.items():
                        if key not in ['message', 'status']: response[key] = value
                    return response
                else:
                    return {"message": "I'm not sure how to handle that request right now.", "actions": actions}
            else:
                return {"message": "I'm not sure I understand what you're asking for. Could you please clarify?", "actions": actions}
                
        except Exception as e:
            error_msg = str(e)
            traceback_str = traceback.format_exc()
            print(f"ERROR in process_user_input: {error_msg}\n{traceback_str}")
            return {"message": "I encountered an error while processing your request. Please try again.", "error": error_msg, "actions": []}
    
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
                    return {"classification": agent_type, "agent_type": agent_type, "confidence": 0.9, "confidence_level": "high", "reasoning": f"Strong match with '{keyword}' pattern", "all_scores": {agent: 0.1 for agent in patterns.keys()}}
        scores = {agent: 0.0 for agent in patterns.keys()}
        for agent_type, keywords in patterns.items():
            for keyword in keywords:
                if keyword in user_input_lower: scores[agent_type] += 0.3
        last_agent = context.get('last_agent')
        if last_agent and last_agent in scores: scores[last_agent] += 0.1
        highest_score = max(scores.values())
        if highest_score > 0:
            best_agent = max(scores.items(), key=lambda x: x[1])[0]
            confidence_level = "high" if highest_score >= 0.8 else "medium" if highest_score >= 0.6 else "low"
            return {"classification": best_agent, "agent_type": best_agent, "confidence": highest_score, "confidence_level": confidence_level, "reasoning": "Best match based on keyword patterns", "all_scores": scores}
        return {"classification": "task", "agent_type": "task", "confidence": 0.3, "confidence_level": "low", "reasoning": "No clear pattern match, defaulting to task agent", "all_scores": scores}
    
    async def _check_silent_mode(self, user_id):
        """Check if the user is in silent mode."""
        try:
            from database_silent import get_silent_status
            status = get_silent_status(self.supabase, user_id)
            return status.get('is_silent', False)
        except Exception as e:
            print(f"ERROR in _check_silent_mode: {str(e)}")
            return False
    
    async def _get_or_create_context(self, user_id, conversation_id=None):
        """Get or create the context for this user and conversation."""
        context_key = f"{user_id}:{conversation_id or 'default'}"
        if context_key not in self.user_contexts:
            self.user_contexts[context_key] = {
                'user_id': user_id, 'conversation_id': conversation_id, 'created_at': datetime.now().isoformat(),
                'last_agent': None, 'last_input': None, 'last_response': None, 'memory': {}
            }
        return self.user_contexts[context_key]

# --- [MODIFIED] ---
# This function is now very simple and fast.
def create_multi_agent_system(supabase, ai_model, prompts_dir=None):
    """Creates and returns a new Orchestrator instance."""
    return Orchestrator(supabase, ai_model)