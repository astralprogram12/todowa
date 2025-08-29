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
    from src.multi_agent_system.agents.audit_agent import AuditAgent
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


class ConversationHistory:
    """
    Stores structured conversation history locally in memory for a single session.
    """
    def __init__(self):
        self.history: List[Dict[str, Any]] = []
        self.max_history = 5
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


class TodowaApp:
    def __init__(self):
        self.supabase: Client = None
        self.api_key_manager: ApiKeyManager = None
        # --- Agent Placeholders ---
        self.context_agent: ContextResolutionAgent = None
        self.audit_agent: AuditAgent = None
        self.journal_agent: JournalAgent = None
        self.brain_agent: BrainAgent = None
        self.task_agent: TaskAgent = None
        self.schedule_agent: ScheduleAgent = None
        self.finding_agent: FindingAgent = None
        self.fallback_agent: GeneralFallbackAgent = None
        self.answering_agent: AnsweringAgent = None
        self._is_initialized = False
        self.user_histories: Dict[str, ConversationHistory] = {}

    def initialize_system(self) -> bool:
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
            self.audit_agent = AuditAgent(ai_model=self.api_key_manager.create_ai_model("audit_agent"))
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

        final_response_text = ""
        resolved_command = ""
        history_manager = self.user_histories.setdefault(user_id, ConversationHistory())
        
        try:
            db_manager = DatabaseManager(self.supabase, user_id)
            logger.info(f"💬 Processing for user '{user_id}': '{message}'")
            
            # STAGE 1: CONTEXT RESOLUTION
            conversation_history = history_manager.get_recent_context()
            context_result = self.context_agent.resolve_context(message, conversation_history)
            
            if context_result.get("status") != "SUCCESS":
                 final_response_text = f"I need more information: {context_result.get('reason', 'Could you please rephrase?')}"
                 resolved_command = message
                 return final_response_text

            resolved_command = context_result.get("resolved_command", message)
            logger.info(f"✅ Context Resolved: '{resolved_command}'")

            # STAGE 2: AUDIT & PLANNING
            execution_plan = self.audit_agent.create_execution_plan(resolved_command)
            sub_tasks = execution_plan.get('sub_tasks', [])
            
            logger.info(f"✅ Plan Created: Found {len(sub_tasks)} sub-task(s) for delegation.")

            if not sub_tasks:
                logger.warning(f"Audit Agent failed to create a plan for: '{resolved_command}'. Falling back.")
                user_context = await self._build_user_context(user_id)
                agent_response = self.fallback_agent.process_command(user_command=resolved_command, user_context=user_context)
                
                final_response_text = self.answering_agent.process_response(agent_response)
                return final_response_text

            TASK_LIMIT = 3
            if len(sub_tasks) > TASK_LIMIT:
                logger.warning(f"User command generated {len(sub_tasks)} sub-tasks. Processing the first {TASK_LIMIT}.")
                sub_tasks = sub_tasks[:TASK_LIMIT]
            
            all_agent_responses, all_actions_to_execute = [], []
            
            agent_map = {
                "TaskAgent": self.task_agent,
                "JournalAgent": self.journal_agent,
                "BrainAgent": self.brain_agent,
                "ScheduleAgent": self.schedule_agent,
                "FindingAgent": self.finding_agent,
                "GeneralFallback": self.fallback_agent,
            }

            user_context = await self._build_user_context(user_id)

            for task in sub_tasks:
                clarified_command = task.get('clarified_command')
                route_to = task.get('route_to')
                
                if not clarified_command or not route_to:
                    continue

                logger.info(f"  - Delegating to {route_to}: '{clarified_command}'")
                
                if route_to in agent_map:
                    specialist_agent = agent_map[route_to]
                    agent_response = specialist_agent.process_command(user_command=clarified_command, user_context=user_context)
                    
                    if agent_response:
                        if 'user_context' not in agent_response:
                            agent_response['user_context'] = user_context
                        
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
            history_manager.add_interaction(
                user_input=message,
                clarified_input=resolved_command,
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

# --- CHANGE: Eagerly initialize the system when the app is created. ---
# This replaces the need for the deprecated @app.before_first_request decorator.
logger.info("Starting Todowa application setup...")
if not chat_app.initialize_system():
    logger.critical("FATAL: Todowa Application failed to initialize. The app may not work correctly.")

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
    return jsonify({"status": "ok", "initialized": chat_app._is_initialized}), 200

if __name__ == "__main__":
    logger.info("Starting Flask development server on http://localhost:5001")
    # The app is already initialized, so we just need to run it.
    app.run(host='0.0.0.0', port=5001, debug=True)