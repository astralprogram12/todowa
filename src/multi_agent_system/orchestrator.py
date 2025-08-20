# orchestrator.py
# Central orchestrator for the multi-agent system

import asyncio
import traceback
import os
from typing import Dict, Any, Optional, List, Tuple

from .agents import (
    BaseAgent,
    TaskAgent,
    ReminderAgent,
    SilentModeAgent,
    CoderAgent,
    AuditAgent,
    ExpertAgent,
    GuideAgent
)

class Orchestrator:
    """Central orchestrator for the multi-agent system.
    
    The orchestrator is responsible for:
    1. Classifying user input to determine the appropriate agent
    2. Routing requests to the appropriate agent
    3. Managing the conversation context
    4. Handling errors and fallbacks
    """
    
    def __init__(self, supabase, ai_model):
        """Initialize the orchestrator with required dependencies.
        
        Args:
            supabase: The Supabase client for database operations
            ai_model: The AI model for natural language processing
        """
        self.supabase = supabase
        self.ai_model = ai_model
        self.agents = {}
        self.user_contexts = {}  # In-memory store for user contexts
        
        # Initialize the specialized agents
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize all specialized agents."""
        # Core agents
        self.agents['task'] = TaskAgent(self.supabase, self.ai_model)
        self.agents['reminder'] = ReminderAgent(self.supabase, self.ai_model)
        self.agents['silent_mode'] = SilentModeAgent(self.supabase, self.ai_model)
        self.agents['coder'] = CoderAgent(self.supabase, self.ai_model)
        
        # Additional agents
        self.agents['audit'] = AuditAgent(self.supabase, self.ai_model)
        self.agents['expert'] = ExpertAgent(self.supabase, self.ai_model)
        self.agents['guide'] = GuideAgent(self.supabase, self.ai_model)
    
    async def process_user_input(self, user_id, user_input, conversation_id=None):
        """Process user input and route to the appropriate agent.
        
        Args:
            user_id: The ID of the user
            user_input: The input text from the user
            conversation_id: Optional conversation ID for context tracking
            
        Returns:
            A response to the user input
        """
        try:
            # Check for silent mode first - this is a high-priority check
            is_silent = await self._check_silent_mode(user_id)
            if is_silent and 'silent' not in user_input.lower():
                # If in silent mode and not trying to exit, just acknowledge
                return {
                    "message": "Currently in silent mode. Your message has been recorded.",
                    "is_silent": True,
                    "actions": []
                }
            
            # Get or create the context for this user
            context = await self._get_or_create_context(user_id, conversation_id)
            
            # Update the context with the current user input
            context['last_input'] = user_input
            
            # Classify the user input to determine the appropriate agent
            classification = await self._classify_user_input(user_input, context)
            agent_type = classification['agent_type']
            
            # Include the classification in the actions
            actions = [{
                "type": "classification",
                "agent": agent_type,
                "confidence": classification['confidence'],
                "reasoning": classification['reasoning']
            }]
            
            # Route to the appropriate agent if classification is confident enough
            if classification['confidence'] >= 0.4:  # Threshold for reasonable confidence
                if agent_type in self.agents:
                    agent_response = await self.agents[agent_type].process(user_input, context)
                    
                    # Update the user context with the agent's response
                    context['last_agent'] = agent_type
                    context['last_response'] = agent_response
                    
                    # Build the response
                    response = {
                        "message": agent_response.get('message', 'I processed your request.'),
                        "agent": agent_type,
                        "actions": actions
                    }
                    
                    # Include any additional data from the agent response
                    for key, value in agent_response.items():
                        if key not in ['message', 'status']:
                            response[key] = value
                    
                    return response
                else:
                    # Agent type not found - fall back to a default response
                    return {
                        "message": "I'm not sure how to handle that request right now.",
                        "actions": actions
                    }
            else:
                # Low confidence - use confusion helper
                return {
                    "message": "I'm not sure I understand what you're asking for. Could you please clarify?",
                    "actions": actions
                }
                
        except Exception as e:
            error_msg = str(e)
            traceback_str = traceback.format_exc()
            
            print(f"ERROR in process_user_input: {error_msg}\n{traceback_str}")
            
            # Return a user-friendly error message
            return {
                "message": "I encountered an error while processing your request. Please try again.",
                "error": error_msg,
                "actions": []
            }
    
    async def _classify_user_input(self, user_input, context):
        """Classify the user input to determine the appropriate agent.
        
        Args:
            user_input: The input text from the user
            context: The context of the conversation
            
        Returns:
            A classification result with agent type and confidence
        """
        # This is a simplified classification logic.
        # In a real implementation, this would use the AI model for classification.
        user_input_lower = user_input.lower()
        
        # Define classification patterns for each agent type
        patterns = {
            'task': ['task', 'todo', 'to-do', 'to do', 'add task', 'create task', 'new task', 'complete task', 'finish task'],
            'reminder': ['remind', 'reminder', 'alert', 'notify', 'at time', 'on date'],
            'silent_mode': ['silent mode', 'go silent', 'stop replying', 'no replies', 'exit silent', 'end silent'],
            'coder': ['code', 'script', 'program', 'function', 'coding', 'programming', 'develop'],
            'audit': ['activity', 'log', 'history', 'what did i', 'what have i', 'show me what'],
            'expert': ['advice', 'best way', 'how should i', 'tips', 'strategy', 'recommend'],
            'guide': ['how to', 'guide', 'steps', 'instructions', 'process', 'explain how']
        }
        
        # Check for exact pattern matches first (higher confidence)
        for agent_type, keywords in patterns.items():
            for keyword in keywords:
                if f" {keyword} " in f" {user_input_lower} " or user_input_lower.startswith(keyword + ' ') or user_input_lower.endswith(' ' + keyword):
                    return {
                        "classification": agent_type,
                        "agent_type": agent_type,
                        "confidence": 0.9,
                        "confidence_level": "high",
                        "reasoning": f"Strong match with '{keyword}' pattern",
                        "all_scores": {agent: 0.1 for agent in patterns.keys()}
                    }
        
        # Check for partial matches (lower confidence)
        scores = {agent: 0.0 for agent in patterns.keys()}
        
        for agent_type, keywords in patterns.items():
            for keyword in keywords:
                if keyword in user_input_lower:
                    scores[agent_type] += 0.3
        
        # Consider conversation context for continuity
        last_agent = context.get('last_agent')
        if last_agent and last_agent in scores:
            # Slight boost for the previously used agent (conversation continuity)
            scores[last_agent] += 0.1
        
        # Determine the highest scoring agent
        highest_score = max(scores.values())
        if highest_score > 0:
            best_agent = max(scores.items(), key=lambda x: x[1])[0]
            confidence_level = "high" if highest_score >= 0.8 else "medium" if highest_score >= 0.6 else "low"
            
            return {
                "classification": best_agent,
                "agent_type": best_agent,
                "confidence": highest_score,
                "confidence_level": confidence_level,
                "reasoning": f"Best match based on keyword patterns",
                "all_scores": scores
            }
        
        # Default to task agent with low confidence if no matches
        return {
            "classification": "task",
            "agent_type": "task",
            "confidence": 0.3,
            "confidence_level": "low",
            "reasoning": "No clear pattern match, defaulting to task agent",
            "all_scores": scores
        }
    
    async def _check_silent_mode(self, user_id):
        """Check if the user is in silent mode.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            True if the user is in silent mode, False otherwise
        """
        try:
            from database_silent import get_silent_status
            
            status = get_silent_status(self.supabase, user_id)
            return status.get('is_silent', False)
        except Exception as e:
            print(f"ERROR in _check_silent_mode: {str(e)}")
            return False
    
    async def _get_or_create_context(self, user_id, conversation_id=None):
        """Get or create the context for this user and conversation.
        
        Args:
            user_id: The ID of the user
            conversation_id: Optional conversation ID for context tracking
            
        Returns:
            The context for this user and conversation
        """
        # Create a unique key for this user and conversation
        context_key = f"{user_id}:{conversation_id or 'default'}"
        
        # Get or create the context
        if context_key not in self.user_contexts:
            self.user_contexts[context_key] = {
                'user_id': user_id,
                'conversation_id': conversation_id,
                'created_at': datetime.now().isoformat(),
                'last_agent': None,
                'last_input': None,
                'last_response': None,
                'memory': {}
            }
        
        return self.user_contexts[context_key]
    
    async def test_agent(self, agent_type, test_input, user_id, conversation_id=None):
        """Test a specific agent with direct input (for debugging and development).
        
        Args:
            agent_type: The type of agent to test
            test_input: The input text to test with
            user_id: The ID of the user
            conversation_id: Optional conversation ID for context tracking
            
        Returns:
            The agent's response to the input
        """
        if agent_type not in self.agents:
            return {"status": "error", "message": f"Agent type '{agent_type}' not found"}
        
        # Get or create the context for this user
        context = await self._get_or_create_context(user_id, conversation_id)
        
        # Process the input with the specified agent
        return await self.agents[agent_type].process(test_input, context)

# For importing in other modules
def create_multi_agent_system(supabase, ai_model, prompts_dir=None):
    """Create and return a new multi-agent system.
    
    Args:
        supabase: The Supabase client for database operations
        ai_model: The AI model for natural language processing
        prompts_dir: Optional directory containing prompt files for the agents
        
    Returns:
        An initialized Orchestrator instance
    """
    orchestrator = Orchestrator(supabase, ai_model)
    
    # If prompt directory is provided, load prompts for all agents
    if prompts_dir and os.path.exists(prompts_dir):
        print(f"Loading prompts from {prompts_dir}")
        # Load prompts into each agent
        for agent_name, agent in orchestrator.agents.items():
            if hasattr(agent, 'load_prompts'):
                agent.load_prompts(prompts_dir)
    
    return orchestrator
