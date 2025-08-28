# --- Standard Library Imports ---
import os
import sys
import logging
import asyncio
from datetime import datetime
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


# --- CHANGE 1: The robust ConversationHistory class is restored and integrated ---
class ConversationHistory:
    """
    Stores structured conversation history locally in memory for a single session.
    Perfectly suited for a productivity app that needs context on actions, not just chat.
    """
    def __init__(self):
        self.history: List[Dict[str, Any]] = []
        self.max_history = 5  # Keeps the last 5 full turns
        self.turn_counter = 0
    
    def add_interaction(self, user_input: str, clarified_input: str, response: Any):
        self.turn_counter += 1
        interaction = {
            'timestamp': datetime.now().isoformat(),
            'user_input': user_input,
            'clarified_input': clarified_input,
            'response': str(response) if response is not None else '',
            'conversation_turn': self.turn_counter
        }
        self.history.append(interaction)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_recent_context(self) -> List[Dict[str, Any]]:
        return self.history.copy()


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
        # --- CHANGE 2: The history manager now uses your structured class ---
        self.user_histories: Dict[str, ConversationHistory] = {}

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
        Asynchronously processes a user message using the Master Planner architecture
        and a robust, structured conversation history.
        """
        if not self._is_initialized:
            return "❌ The server is not properly initialized. Please contact support."

        final_response_text = ""
        clarified_summary = ""
        try:
            db_manager = DatabaseManager(self.supabase, user_id)
            logger.info(f"💬 Processing for user '{user_id}': '{message}'")
            
            # --- CHANGE 3: Get or create the dedicated history manager for the user ---
            history_manager = self.user_histories.setdefault(user_id, ConversationHistory())
            conversation_history = history_manager.get_recent_context()

            # The Master Planner receives the rich, structured history
            execution_plan = self.context_agent.resolve_context(message, conversation_history)
            sub_tasks = execution_plan.get('sub_tasks', [])

            # Create a summary of clarified commands for history logging
            if sub_tasks:
                clarified_summary = "; ".join([task.get('clarified_command', '') for task in sub_tasks])
            else:
                clarified_summary = message # Fallback if no plan was made

            if not sub_tasks:
                logger.warning(f"Master Planner failed to create a plan for: '{message}'. Falling back.")
                user_context = await self._build_user_context(user_id)
                agent_response = self.fallback_agent.process_command(user_command=message, user_context=user_context)
                
                # --- FIX IS HERE ---
                # Ensure the user_context is passed along to the AnsweringAgent.
                if 'user_context' not in agent_response:
                    agent_response['user_context'] = user_context
                # --- END OF FIX ---
                
                final_response_text = self.answering_agent.process_response(agent_response)
                return final_response_text

            TASK_LIMIT = 3
            if len(sub_tasks) > TASK_LIMIT:
                logger.warning(f"User command generated {len(sub_tasks)} sub-tasks. Processing the first {TASK_LIMIT} to prevent abuse.")
                sub_tasks = sub_tasks[:TASK_LIMIT]
            
            all_agent_responses, all_actions_to_execute = [], []
            
            agent_map = {
                "TaskAgent": self.task_agent.process_command,
                "JournalAgent": self.journal_agent.process_command,
                "BrainAgent": self.brain_agent.process_command,
                "ScheduleAgent": self.schedule_agent.process_command,
                "FindingAgent": self.finding_agent.process_command,
                "GeneralFallback": self.fallback_agent.process_command,
            }

            user_context = await self._build_user_context(user_id)
            user_context['conversation_history'] = conversation_history

            for task in sub_tasks:
                clarified_command = task.get('clarified_command')
                route_to = task.get('route_to')
                
                if not clarified_command or not route_to:
                    continue

                logger.info(f"  - Sub-task: '{clarified_command}' -> Routing to: {route_to}")
                
                if route_to in agent_map:
                    agent_response = agent_map[route_to](user_command=clarified_command, user_context=user_context)
                    if agent_response:
                        # --- FIX IS HERE ---
                        # Ensure every agent response includes the user_context before being stored.
                        if 'user_context' not in agent_response:
                            agent_response['user_context'] = user_context
                        # --- END OF FIX ---
                        
                        all_agent_responses.append(agent_response)
                        all_actions_to_execute.extend(agent_response.get('actions', []))
            
            execution_result = {}
            if all_actions_to_execute:
                execution_result = await self._execute_json_actions(user_id, all_actions_to_execute, db_manager)

            final_response_context = {
                'source': 'MultiAgentExecution',
                'original_command': message,
                'agent_responses': all_agent_responses,
                'execution_result': execution_result,
                'user_context': user_context,
            }
            final_response_text = self.answering_agent.process_multi_response(final_response_context)
            return final_response_text

        except Exception as e:
            logger.error(f"❌ An unexpected error occurred for user '{user_id}': {e}", exc_info=True)
            final_response_text = self.answering_agent.process_error("I ran into an unexpected problem.")
            return final_response_text
        finally:
            # --- CHANGE 4: Use the dedicated history manager to log the full, structured interaction ---
            history_manager = self.user_histories.setdefault(user_id, ConversationHistory())
            history_manager.add_interaction(
                user_input=message,
                clarified_input=clarified_summary,
                response=final_response_text
            )
            logger.info(f"Interaction logged for user '{user_id}'. History size: {len(history_manager.history)} turns.")

    async def _build_user_context(self, user_id: str) -> Dict[str, Any]:
        context = {
            'user_info': {'timezone': 'GMT+7', 'user_id': user_id},
            'ai_brain': []
        }
        if not self.supabase:
            return context
        try:
            brain_result = await self.supabase.table('ai_brain_memories').select('*').eq('user_id', user_id).limit(10).execute()
            if brain_result.data:
                context['ai_brain'] = brain_result.data
        except Exception as e:
            logger.warning(f"Could not fetch ai_brain context from database: {e}")
        return context
    
    async def _execute_json_actions(self, user_id: str, actions: List[Dict[str, Any]], db_manager: DatabaseManager) -> Dict[str, Any]:
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
app = Flask(__name__)
chat_app = TodowaApp()

# --- Application Initialization ---
logger.info("Starting Todowa application setup for Vercel...")
if not chat_app.initialize_system():
    logger.critical("FATAL: Todowa Application failed to initialize. The app will not work.")

# --- API Routes / Endpoints ---
@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return jsonify({"status": "verified"}), 200
        
    sender_phone = None
    try:
        data = request.get_json()
        if not data: return jsonify({"status": "error", "message": "Invalid JSON"}), 400

        sender_phone = data.get('sender')
        message_text = data.get('message')
        if not sender_phone or not message_text:
            return jsonify({"status": "error", "message": "Missing 'sender' or 'message'"}), 400

        user_id = database.get_user_id_by_phone(chat_app.supabase, sender_phone)
        if not user_id:
            reply = "Welcome! To use this service, please sign up on our website first."
            services.send_fonnte_message(sender_phone, reply)
            return jsonify({"status": "unauthorized_user_prompted"}), 200

        is_allowed, limit_message = database.check_and_update_usage(chat_app.supabase, sender_phone, user_id)
        if not is_allowed:
            services.send_fonnte_message(sender_phone, limit_message)
            return jsonify({"status": "limit_exceeded"}), 429

        response_text = asyncio.run(chat_app.process_message_async(message_text, user_id))
        services.send_fonnte_message(sender_phone, response_text)
        return jsonify({"status": "success"}), 200

    except Exception as e:
        logger.critical(f"!!! UNHANDLED ERROR IN WEBHOOK: {e}", exc_info=True)
        error_reply = "I ran into an unexpected problem and my developers have been notified."
        if sender_phone:
            services.send_fonnte_message(sender_phone, error_reply)
        return jsonify({"status": "internal_server_error"}), 500

@app.route('/', methods=['GET'])
def health_check():
    """A simple health check endpoint."""
    return jsonify({"status": "ok", "initialized": chat_app._is_initialized}), 200

# This block is for LOCAL DEVELOPMENT ONLY. Vercel will ignore it.
if __name__ == "__main__":
    logger.info("Starting Flask development server on http://localhost:5001")
    app.run(host='0.0.0.0', port=5001, debug=True)