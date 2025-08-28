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
        if self._is_initialized:
            return True

        logger.info("🔧 Initializing Todowa system...")
        try:
            self.supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
            logger.info("✅ Supabase connected")

            ### --- CHANGE STARTS HERE --- ###
            # This section is updated to use the new stateless config and ApiKeyManager.
            
            # 1. Call the new function from your updated config.py
            gemini_keys_dict = config.get_gemini_api_keys()
            
            # 2. Initialize the ApiKeyManager directly with the result.
            self.api_key_manager = ApiKeyManager(gemini_keys=gemini_keys_dict)
            
            ### --- CHANGE ENDS HERE --- ###

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
        if not self._is_initialized:
            return "❌ The server is not properly initialized. Please contact support."

        try:
            db_manager = DatabaseManager(self.supabase, user_id)
            logger.info(f"💬 Processing for user '{user_id}': '{message}'")
            
            routing_result = self.context_agent.resolve_context(message)
            if self.context_agent.needs_clarification(routing_result):
                clarification_prompt = f"I'm not quite sure what you mean by '{message}'. Could you please rephrase or provide more details?"
                return self.answering_agent.process_context_clarification(clarification_prompt)

            clarified_command = routing_result['clarified_command']
            route_to = routing_result['route_to']
            logger.info(f"🔍 Intent: '{clarified_command}' -> Routing to: {route_to}")

            user_context = await self._build_user_context(user_id)
            
            agent_response = None

            agent_map = {
                "TaskAgent": self.task_agent.process_command,
                "JournalAgent": self.journal_agent.process_command,
                "BrainAgent": self.brain_agent.process_command,
                "ScheduleAgent": self.schedule_agent.process_command,
            }

            if route_to in agent_map:
                agent_response = agent_map[route_to](user_command=clarified_command, user_context=user_context)
            elif route_to == 'FindingAgent':
                agent_response = self.finding_agent.process_command(user_command=clarified_command, user_context=user_context)
            elif route_to == 'GeneralFallback':
                agent_response = self.fallback_agent.process_command(user_command=clarified_command, user_context=user_context)
            else:
                 return self.answering_agent.process_error(f"Error: Router specified an unknown agent: '{route_to}'.")

            actions_to_execute = agent_response.get('actions', [])
            execution_result = {}
            if actions_to_execute:
                logger.info(f"▶️ Executing {len(actions_to_execute)} action(s)...")
                execution_result = await self._execute_json_actions(user_id, actions_to_execute, db_manager)

            self.context_agent.add_interaction(message, clarified_command, agent_response)

            final_response_context = {
                'source': route_to, 'message': agent_response.get('response', ''),
                'actions': actions_to_execute, 'status': 'success' if agent_response.get('success', True) else 'error',
                'execution_result': execution_result, 'processing_context': agent_response,
                'user_context': user_context, 'original_command': message, 'resolved_command': clarified_command
            }
            return self.answering_agent.process_response(final_response_context)

        except Exception as e:
            logger.error(f"❌ An unexpected error occurred while processing message for user '{user_id}': {e}", exc_info=True)
            return self.answering_agent.process_error("I seem to have run into an unexpected problem. My developers have been notified.")

    async def _build_user_context(self, user_id: str) -> Dict[str, Any]:
        context = {
            'user_info': {'timezone': 'GMT+7', 'user_id': user_id},
            'ai_brain': []
        }
        if not self.supabase:
            return context
            
        try:
            brain_result = self.supabase.table('ai_brain_memories').select('*').eq('user_id', user_id).limit(10).execute()
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
logger.info("Starting Todowa application setup...")
if not chat_app.initialize_system():
    logger.critical("FATAL: Todowa Application failed to initialize. The server will not start.")
    sys.exit(1)

# --- API Routes / Endpoints ---
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        logger.info("Received GET request for webhook verification.")
        return jsonify({"status": "success", "message": "Webhook is active."}), 200

    sender_phone = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Invalid JSON"}), 400

        sender_phone = data.get('sender')
        message_text = data.get('message')

        if not sender_phone or not message_text:
            return jsonify({"status": "error", "message": "Missing 'sender' or 'message'"}), 400

        user_id = database.get_user_id_by_phone(chat_app.supabase, sender_phone)
        
        if not user_id:
            logger.info(f"New sender '{sender_phone}' is not registered. Prompting to sign up.")
            reply = "Welcome! To use this service, please sign up on our website first."
            services.send_fonnte_message(sender_phone, reply)
            return jsonify({"status": "unauthorized_user_prompted"}), 200

        is_allowed, limit_message = database.check_and_update_usage(chat_app.supabase, sender_phone, user_id)
        if not is_allowed:
            logger.warning(f"User '{user_id}' ({sender_phone}) has exceeded their usage limit.")
            services.send_fonnte_message(sender_phone, limit_message)
            return jsonify({"status": "limit_exceeded"}), 429

        response_text = asyncio.run(chat_app.process_message_async(message_text, user_id))
        services.send_fonnte_message(sender_phone, response_text)
        return jsonify({"status": "success", "message_sent": True}), 200

    except Exception as e:
        logger.critical(f"!!! AN UNEXPECTED ERROR OCCURRED IN WEBHOOK: {e}", exc_info=True)
        error_reply = "I seem to have run into an unexpected problem. My developers have been notified."
        if sender_phone:
            services.send_fonnte_message(sender_phone, error_reply)
        return jsonify({"status": "internal_server_error"}), 500

