# --- Standard Library Imports ---
import os
import sys
import logging
import asyncio
from typing import Dict, Any, List

# --- Third-Party Imports ---
from flask import Flask, request, jsonify

# --- Project-Specific Imports ---
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger('httpx').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


try:
    # --- Core Dependencies ---
    from supabase import create_client, Client

    # --- Local Module Imports ---
    import config
    import services
    import database
    from api_key_manager import ApiKeyManager
    from action_executor import ActionExecutor
    from database import DatabaseManager
    import ai_tools

    # --- Agent Imports ---
    from src.multi_agent_system.agents.context_resolution_agent import ContextResolutionAgent
    from src.multi_agent_system.agents.journal_agent import JournalAgent
    from src.multi_agent_system.agents.brain_agent import BrainAgent
    from src.multi_agent_system.agents.task_agent import TaskAgent
    from src.multi_agent_system.agents.schedule_agent import ScheduleAgent
    from src.multi_agent_system.agents.answering_agent import AnsweringAgent
    from src.multi_agent_system.agents.general_fallback_agent import GeneralFallbackAgent
    from src.multi_agent_system.agents.finding_agent import FindingAgent

except ImportError as e:
    logger.critical(f"❌ Import Error: {e}. Ensure all dependencies and local modules are present.")
    sys.exit(1)


# --- The Core Application Logic Class ---
class TodowaApp:
    def __init__(self):
        self.supabase: Client = None
        self.api_key_manager: ApiKeyManager = None
        self.context_agent: ContextResolutionAgent = None
        self.journal_agent: JournalAgent = None
        self.brain_agent: BrainAgent = None
        self.task_agent: TaskAgent = None
        self.schedule_agent: ScheduleAgent = None
        self.finding_agent: FindingAgent = None
        self.fallback_agent: GeneralFallbackAgent = None
        self.answering_agent: AnsweringAgent = None
        self._is_initialized = False

    def initialize_system(self) -> bool:
        # This initialization logic is correct and does not need to be changed.
        if self._is_initialized:
            return True

        logger.info("🔧 Initializing Todowa system...")
        try:
            self.supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
            logger.info("✅ Supabase connected")

            gemini_keys_dict = config.get_gemini_api_keys()
            self.api_key_manager = ApiKeyManager(gemini_keys=gemini_keys_dict)
            gemini_key_count = self.api_key_manager.get_key_count()
            logger.info(f"🔑 API Key Manager initialized with {gemini_key_count} Gemini key(s).")

            self.context_agent = ContextResolutionAgent(ai_model=self.api_key_manager.create_ai_model("context_agent"))
            self.journal_agent = JournalAgent(ai_model=self.api_key_manager.create_ai_model("journal_agent"), supabase=self.supabase)
            self.brain_agent = BrainAgent(ai_model=self.api_key_manager.create_ai_model("brain_agent"))
            self.task_agent = TaskAgent(ai_model=self.api_key_manager.create_ai_model("task_agent"), supabase=self.supabase)
            self.schedule_agent = ScheduleAgent(ai_model=self.api_key_manager.create_ai_model("schedule_agent"), supabase=self.supabase)
            self.finding_agent = FindingAgent(ai_model=self.api_key_manager.create_ai_model("finding_agent"), supabase=self.supabase)
            self.fallback_agent = GeneralFallbackAgent(ai_model=self.api_key_manager.create_ai_model("fallback_agent"), supabase=self.supabase)
            self.answering_agent = AnsweringAgent(ai_model=self.api_key_manager.create_chat_model("answering_agent"), supabase=self.supabase)

            logger.info("✅ All specialized agents initialized.")
            logger.info("✅ System is fully operational!")
            self._is_initialized = True
            return True

        except Exception as e:
            logger.critical(f"❌ System initialization failed: {e}", exc_info=True)
            self._is_initialized = False
            return False

    async def process_message_async(self, message: str, user_id: str) -> str:
        """
        Asynchronously processes a user message using the Master Planner architecture.
        """
        if not self._is_initialized:
            return "❌ The server is not properly initialized. Please contact support."

        try:
            db_manager = DatabaseManager(self.supabase, user_id)
            logger.info(f"💬 Processing for user '{user_id}': '{message}'")
            
            # --- STEP 1: The "Planner" Call ---
            # The ContextResolutionAgent acts as a Master Planner, creating a multi-step plan.
            # This assumes you have updated the agent with a new prompt and a method like 'create_execution_plan'.
            execution_plan = self.context_agent.create_execution_plan(message)
            sub_tasks = execution_plan.get('sub_tasks', [])

            if not sub_tasks:
                logger.warning(f"Master Planner failed to create a plan for: '{message}'. Falling back.")
                # If the planner fails, you can fall back to a simpler agent or a default response.
                user_context = await self._build_user_context(user_id)
                return self.fallback_agent.process_command(user_command=message, user_context=user_context)

            # --- STEP 2: The Anti-Abuse Mechanism ---
            # Enforce a hard limit on the number of sub-tasks to process per command.
            TASK_LIMIT = 3
            if len(sub_tasks) > TASK_LIMIT:
                logger.warning(f"User command generated {len(sub_tasks)} sub-tasks. Processing the first {TASK_LIMIT} to prevent abuse.")
                sub_tasks = sub_tasks[:TASK_LIMIT]
            
            all_agent_responses = []
            all_actions_to_execute = []
            
            agent_map = {
                "TaskAgent": self.task_agent.process_command,
                "JournalAgent": self.journal_agent.process_command,
                "BrainAgent": self.brain_agent.process_command,
                "ScheduleAgent": self.schedule_agent.process_command,
                "FindingAgent": self.finding_agent.process_command,
                "GeneralFallback": self.fallback_agent.process_command,
            }

            user_context = await self._build_user_context(user_id)

            # --- STEP 3: The "Worker" Phase ---
            # Loop through the controlled plan and execute each step with the correct specialist.
            for task in sub_tasks:
                clarified_command = task.get('clarified_command')
                route_to = task.get('route_to')
                
                if not clarified_command or not route_to:
                    logger.warning(f"Skipping malformed sub-task from planner: {task}")
                    continue

                logger.info(f"  - Sub-task: '{clarified_command}' -> Routing to: {route_to}")
                
                if route_to in agent_map:
                    # Each specialist agent processes its own part of the command.
                    agent_response = agent_map[route_to](
                        user_command=clarified_command, 
                        user_context=user_context
                    )
                    if agent_response:
                        all_agent_responses.append(agent_response)
                        all_actions_to_execute.extend(agent_response.get('actions', []))
                else:
                    logger.warning(f"  - Skipping unknown route specified by planner: {route_to}")
            
            # --- STEP 4: Execute all collected actions in one batch ---
            execution_result = {}
            if all_actions_to_execute:
                logger.info(f"▶️ Executing a total of {len(all_actions_to_execute)} action(s) from the plan...")
                execution_result = await self._execute_json_actions(user_id, all_actions_to_execute, db_manager)

            # --- STEP 5: Consolidate and Generate Final Response ---
            # The AnsweringAgent synthesizes a single, coherent response from all the work done.
            # This assumes you will add a 'process_multi_response' method to your AnsweringAgent.
            final_response_context = {
                'source': 'MultiAgentExecution',
                'original_command': message,
                'agent_responses': all_agent_responses, # Pass all individual agent outputs
                'execution_result': execution_result,
                'user_context': user_context,
            }
            return self.answering_agent.process_multi_response(final_response_context)

        except Exception as e:
            logger.error(f"❌ An unexpected error occurred while processing message for user '{user_id}': {e}", exc_info=True)
            return self.answering_agent.process_error("I seem to have run into an unexpected problem. My developers have been notified.")

    async def _build_user_context(self, user_id: str) -> Dict[str, Any]:
        # This method is correct and does not need to be changed.
        context = {
            'user_info': {'timezone': 'GMT+7', 'user_id': user_id},
            'ai_brain': []
        }
        if not self.supabase:
            return context
        try:
            # Assuming supabase client is async-compatible
            brain_result = await self.supabase.table('ai_brain_memories').select('*').eq('user_id', user_id).limit(10).execute()
            if brain_result.data:
                context['ai_brain'] = brain_result.data
        except Exception as e:
            logger.warning(f"Could not fetch ai_brain context from database: {e}")
        return context
    
    async def _execute_json_actions(self, user_id: str, actions: List[Dict[str, Any]], db_manager: DatabaseManager) -> Dict[str, Any]:
        # This method is correct and does not need to be changed.
        if not actions: return {'success': True, 'results': []}
        try:
            executor = ActionExecutor(db_manager, user_id)
            execution_results = executor.execute_actions(actions)
            successful_count = sum(1 for r in execution_results if not (isinstance(r, dict) and 'error' in r))
            total_count = len(execution_results)
            logger.info(f"📊 Execution: {successful_count}/{total_count} successful for user '{user_id}'.")
            return {"total_actions": total_count, "successful_actions": successful_count, "results": execution_results}
        except Exception as e:
            logger.error(f"❌ Action execution failed for user '{user_id}': {e}", exc_info=True)
            return {'success': False, 'error': str(e), 'results': []}

# --- Flask Web Server Setup ---
# The Flask app, initialization, and webhook logic remain the same.
# They are already designed to call the `process_message_async` method, which
# now contains our new, more powerful logic.
# ... (Your existing Flask code from @app.route('/webhook') onwards) ...