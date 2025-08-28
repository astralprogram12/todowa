#!/usr/bin/env python3
"""
Todowa Chat - Task Management Assistant
### NEW: Now with a unified ScheduleAgent for all time-based actions.

ARCHITECTURE:
- Context Resolution Agent (Master Router): Clarifies intent and routes commands
  directly to the appropriate specialized agent.
- Specialized Agents (Task, Journal, Schedule, Brain): Handle specific domains,
  perform deep analysis, and generate final JSON for execution.
- Action Executor: Executes the final JSON from specialized agents.
- Answering Agent: Formats all user-facing responses.
"""

import os
import sys
import json
import traceback
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List

# --- Configuration and Imports ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger('httpx').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

try:
    import google.generativeai as genai
    from supabase import create_client, Client
    import config
    from api_key_manager import ApiKeyManager, initialize_api_key_manager, APIProvider
    from action_executor import ActionExecutor
    from database import DatabaseManager 
    import ai_tools 
    from src.multi_agent_system.agents.context_resolution_agent import ContextResolutionAgent
    from src.multi_agent_system.agents.journal_agent import JournalAgent
    from src.multi_agent_system.agents.brain_agent import BrainAgent
    from src.multi_agent_system.agents.task_agent import TaskAgent
    # --- CHANGE 1: Import the new ScheduleAgent ---
    from src.multi_agent_system.agents.schedule_agent import ScheduleAgent
    from src.multi_agent_system.agents.answering_agent import AnsweringAgent

except ImportError as e:
    print(f"❌ Import Error: {e}. Please run 'pip install -r requirements.txt'")
    sys.exit(1)

class TodowaChat:
    
    def __init__(self):
        self.session_start = datetime.now()
        self.message_count = 0
        self.supabase: Client = None
        self.api_key_manager: ApiKeyManager = None
        
        self.context_agent: ContextResolutionAgent = None
        self.journal_agent: JournalAgent = None
        self.brain_agent: BrainAgent = None
        self.task_agent: TaskAgent = None
        # --- CHANGE 2: Add a placeholder for the ScheduleAgent instance ---
        self.schedule_agent: ScheduleAgent = None
        self.answering_agent: AnsweringAgent = None
        
    def initialize_system(self):
        print("🔧 Initializing Todowa system...")
        try:
            self.supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
            print("✅ Supabase connected")
            
            named_api_keys = config.get_named_api_keys()
            self.api_key_manager = initialize_api_key_manager(self.supabase, named_api_keys)
            print(f"🔑 API Key Manager initialized with {self.api_key_manager.get_statistics_sync()['total_keys']} keys.")

            self.context_agent = ContextResolutionAgent(
                ai_model=self.api_key_manager.create_agent_ai_model(APIProvider.GEMINI, "context_agent"),
            )
            self.journal_agent = JournalAgent(
                ai_model=self.api_key_manager.create_agent_ai_model(APIProvider.GEMINI, "journal_agent"),
                supabase=self.supabase,
            )
            self.brain_agent = BrainAgent(
                ai_model=self.api_key_manager.create_agent_ai_model(APIProvider.GEMINI, "brain_agent"),
            )
            self.task_agent = TaskAgent(
                ai_model=self.api_key_manager.create_agent_ai_model(APIProvider.GEMINI, "task_agent"),
                supabase=self.supabase,
            )
            # --- CHANGE 3: Initialize the new ScheduleAgent ---
            self.schedule_agent = ScheduleAgent(
                ai_model=self.api_key_manager.create_agent_ai_model(APIProvider.GEMINI, "schedule_agent"),
                supabase=self.supabase, # The agent needs this for its internal limit check
            )
            self.answering_agent = AnsweringAgent(
                ai_model=self.api_key_manager.create_agent_ai_model(APIProvider.GEMINI, "answering_agent"),
                supabase=self.supabase
            )
            print("✅ All specialized agents initialized.")
            print("✅ System ready!")
            return True
            
        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            traceback.print_exc()
            return False
    
    async def process_message_async(self, message: str) -> str:
        # Renamed task_reminder_agent to task_agent for clarity
        if not all([self.context_agent, self.journal_agent, self.brain_agent, self.task_agent, self.schedule_agent, self.answering_agent]):
            return "❌ System is not fully initialized. Please restart."

        try:
            self.message_count += 1
            test_user_id = config.CHAT_TEST_USER_ID
            
            db_manager = DatabaseManager(self.supabase, test_user_id)
            
            print(f"\n💬 Processing: '{message}'")
            
            routing_result = self.context_agent.resolve_context(message)
            
            if self.context_agent.needs_clarification(routing_result):
                clarification_prompt = f"I'm not quite sure what you mean by '{message}'. Could you please rephrase or provide more details?"
                return self.answering_agent.process_context_clarification(clarification_prompt)

            clarified_command = routing_result['clarified_command']
            route_to = routing_result['route_to']
            
            print(f"🔍 Intent: '{clarified_command}' -> Routing to: {route_to}")
            
            user_context = await self._build_user_context(test_user_id)
            agent_response = None
            
            # --- CHANGE 4: Add the ScheduleAgent to the agent map ---
            agent_map = {
                "TaskAgent": self.task_agent.process_command,
                "JournalAgent": self.journal_agent.process_command,
                "BrainAgent": self.brain_agent.process_command,
                "ScheduleAgent": self.schedule_agent.process_command,
            }

            if route_to in agent_map:
                agent_response = agent_map[route_to](
                    user_command=clarified_command, 
                    user_context=user_context
                )
            elif route_to == 'GeneralFallback':
                return self.answering_agent.process_response({
                    'source': 'general_chat',
                    'message': clarified_command,
                    'user_context': user_context
                })
            else:
                 return self.answering_agent.process_error(f"Error: The router specified an unknown agent destination: '{route_to}'.")

            actions_to_execute = agent_response.get('actions', [])
            execution_result = {}
            if actions_to_execute:
                print(f"▶️ Executing {len(actions_to_execute)} action(s)...")
                execution_result = await self._execute_json_actions(test_user_id, actions_to_execute, db_manager)
            
            self.context_agent.add_interaction(message, clarified_command, agent_response)
            
            final_response_context = {
                'source': route_to,
                'message': agent_response.get('response', ''),
                'actions': actions_to_execute,
                'status': 'success' if agent_response.get('success', True) else 'error',
                'execution_result': execution_result,
                'processing_context': agent_response,
                'user_context': user_context,
                'original_command': message,
                'resolved_command': clarified_command
            }
            return self.answering_agent.process_response(final_response_context)
            
        except Exception as e:
            error_msg = f"❌ An unexpected error occurred: {e}"
            print(error_msg)
            traceback.print_exc()
            return self.answering_agent.process_error(error_msg)
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
    # FIXED: Corrected the import to match the new, improved api_key_manager.py
    from api_key_manager import ApiKeyManager, APIProvider
    from action_executor import ActionExecutor
    from database import DatabaseManager
    import ai_tools

    # --- Agent Imports ---
    # Assuming these are correctly located in a 'src' folder or similar
    from src.multi_agent_system.agents.context_resolution_agent import ContextResolutionAgent
    from src.multi_agent_system.agents.journal_agent import JournalAgent
    from src.multi_agent_system.agents.brain_agent import BrainAgent
    from src.multi_agent_system.agents.task_agent import TaskAgent
    from src.multi_agent_system.agents.schedule_agent import ScheduleAgent
    from src.multi_agent_system.agents.answering_agent import AnsweringAgent

except ImportError as e:
    logger.critical(f"❌ Import Error: {e}. Please ensure all dependencies are installed (`pip install -r requirements.txt`) and all required local modules (config, services, database) are present.")
    sys.exit(1)


# --- The Core Application Logic Class ---
class TodowaApp:
    """
    Encapsulates the entire multi-agent system and its state.
    """
    def __init__(self):
        self.supabase: Client = None
        self.api_key_manager: ApiKeyManager = None
        self.context_agent: ContextResolutionAgent = None
        self.journal_agent: JournalAgent = None
        self.brain_agent: BrainAgent = None
        self.task_agent: TaskAgent = None
        self.schedule_agent: ScheduleAgent = None
        self.answering_agent: AnsweringAgent = None
        self._is_initialized = False

    def initialize_system(self) -> bool:
        """
        Initializes all components of the Todowa system. Called once at startup.
        Returns True on success, False on failure.
        """
        if self._is_initialized:
            return True

        logger.info("🔧 Initializing Todowa system...")
        try:
            self.supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
            logger.info("✅ Supabase connected")

            # --- FIXED: Corrected the entire initialization block ---
            # 1. Get the configuration dictionary from config.py
            named_api_keys = config.get_named_api_keys()
            
            # 2. Create an instance of our new manager class directly with the config
            self.api_key_manager = ApiKeyManager(named_api_keys)
            
            # 3. Log the count of keys for the Gemini provider for confirmation
            gemini_key_count = self.api_key_manager.get_key_count(APIProvider.GEMINI)
            logger.info(f"🔑 API Key Manager initialized with {gemini_key_count} Gemini key(s).")
            # --- END OF FIX ---

            # --- FIXED: Renamed all method calls to 'create_ai_model' ---
            self.context_agent = ContextResolutionAgent(ai_model=self.api_key_manager.create_ai_model(APIProvider.GEMINI, "context_agent"))
            self.journal_agent = JournalAgent(ai_model=self.api_key_manager.create_ai_model(APIProvider.GEMINI, "journal_agent"), supabase=self.supabase)
            self.brain_agent = BrainAgent(ai_model=self.api_key_manager.create_ai_model(APIProvider.GEMINI, "brain_agent"))
            self.task_agent = TaskAgent(ai_model=self.api_key_manager.create_ai_model(APIProvider.GEMINI, "task_agent"), supabase=self.supabase)
            self.schedule_agent = ScheduleAgent(ai_model=self.api_key_manager.create_ai_model(APIProvider.GEMINI, "schedule_agent"), supabase=self.supabase)
            self.answering_agent = AnsweringAgent(ai_model=self.api_key_manager.create_ai_model(APIProvider.GEMINI, "answering_agent"), supabase=self.supabase)

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
        Asynchronously processes a single user message through the agent pipeline.
        """
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
            agent_map = {
                "TaskAgent": self.task_agent.process_command,
                "JournalAgent": self.journal_agent.process_command,
                "BrainAgent": self.brain_agent.process_command,
                "ScheduleAgent": self.schedule_agent.process_command,
            }

            if route_to in agent_map:
                agent_response = agent_map[route_to](user_command=clarified_command, user_context=user_context)
            elif route_to == 'GeneralFallback':
                return self.answering_agent.process_response({'source': 'general_chat', 'message': clarified_command, 'user_context': user_context})
            else:
                 return self.answering_agent.process_error(f"Error: Router specified an unknown agent: '{route_to}'.")

            actions_to_execute = agent_response.get('actions', [])
            if actions_to_execute:
                logger.info(f"▶️ Executing {len(actions_to_execute)} action(s)...")
                execution_result = await self._execute_json_actions(user_id, actions_to_execute, db_manager)

            self.context_agent.add_interaction(message, clarified_command, agent_response)

            final_response_context = {
                'source': route_to, 'message': agent_response.get('response', ''),
                'actions': actions_to_execute, 'status': 'success' if agent_response.get('success', True) else 'error',
                'execution_result': agent_response.get('execution_result', {}), 'processing_context': agent_response,
                'user_context': user_context, 'original_command': message, 'resolved_command': clarified_command
            }
            return self.answering_agent.process_response(final_response_context)

        except Exception as e:
            logger.error(f"❌ An unexpected error occurred while processing message for user '{user_id}': {e}", exc_info=True)
            return self.answering_agent.process_error("I seem to have run into an unexpected problem. My developers have been notified.")

    async def _build_user_context(self, user_id: str) -> Dict[str, Any]:
        """Builds the user context by fetching data from the database."""
        context = {
            'user_info': {'timezone': 'GMT+7', 'user_id': user_id},
            'tasks': [],
            'ai_brain': [],
            'conversation_history': []
        }
        if not self.supabase:
            return context
            
        try:
            tasks_result = self.supabase.table('tasks').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(10).execute()
            if tasks_result.data:
                context['tasks'] = tasks_result.data
            
            brain_result = self.supabase.table('ai_brain_memories').select('*').eq('user_id', user_id).limit(10).execute()
            if brain_result.data:
                context['ai_brain'] = brain_result.data

        except Exception as e:
            logger.warning(f"Could not fetch full user context from database: {e}")
            
        return context
    
    async def _execute_json_actions(self, user_id: str, actions: List[Dict[str, Any]], db_manager: DatabaseManager) -> Dict[str, Any]:
        """Executes a list of actions using the ActionExecutor."""
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
    """Main webhook endpoint for Fonnte."""
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

@app.route('/health', methods=['GET'])
def health_check():
    """A simple health check endpoint."""
    return jsonify({"status": "ok", "initialized": chat_app._is_initialized}), 200

# --- Main Execution Block ---
if __name__ == "__main__":
    logger.info("Starting Flask development server...")
    app.run(host='0.0.0.0', port=5001, debug=True)
    async def _build_user_context(self, user_id: str) -> Dict[str, Any]:
        # This function remains the same, but its context is now used by the ScheduleAgent too
        context = {
            'user_info': {'timezone': 'GMT+7', 'user_id': user_id},
            'tasks': [],
            'ai_brain': [],
            'conversation_history': []
        }
        if not self.supabase: return context
        try:
            # --- FIX: Added 'await' to make the database calls non-blocking ---
            tasks_result = await self.supabase.table('tasks').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(10).execute()
            if tasks_result.data: context['tasks'] = tasks_result.data
            
            # --- FIX: Added 'await' here as well ---
            brain_result = await self.supabase.table('ai_brain_memories').select('*').eq('user_id', user_id).limit(10).execute()
            if brain_result.data: context['ai_brain'] = brain_result.data

        except Exception as e:
            # This will no longer be triggered by the TypeError
            logger.warning(f"Could not fetch full user context from database: {e}")
        return context
    
    async def _execute_json_actions(self, user_id: str, actions: List[Dict[str, Any]], db_manager: DatabaseManager) -> Dict[str, Any]:
        # This function remains the same. The ActionExecutor will need to be updated
        # to know about the new 'create_schedule' tool.
        if not actions: return {'success': True, 'results': []}
        try:
            executor = ActionExecutor(db_manager, user_id)
            execution_results = executor.execute_actions(actions)
            successful_count = sum(1 for r in execution_results if not (isinstance(r, dict) and 'error' in r))
            total_count = len(execution_results)
            
            print(f"📊 Execution: {successful_count}/{total_count} successful.")
            return {
                "total_actions": total_count,
                "successful_actions": successful_count,
                "results": execution_results
            }
        except Exception as e:
            logger.error(f"❌ Action execution failed: {e}")
            traceback.print_exc()
            return {'success': False, 'error': str(e), 'results': []}

    def process_message(self, message):
        """Synchronous wrapper for the async message processor."""
        try:
            asyncio.get_running_loop()
            print("❌ Error: Cannot run synchronously in an active async context. Use 'await chat.process_message_async(msg)'.")
            return "Error: Running in an async context."
        except RuntimeError:
            return asyncio.run(self.process_message_async(message))

    def run(self):
        """Main chat loop for command-line interface."""
        if not self.initialize_system():
            return
        
        print("\n✅ System is ready. Type your message or 'exit' to quit.")
        
        while True:
            try:
                user_input = input("\n💬 You: ").strip()
                if not user_input: continue
                
                if user_input.lower() == 'exit':
                    print(f"\n👋 Goodbye! Session lasted {datetime.now() - self.session_start}")
                    break
                
                response = self.process_message(user_input)
                print(f"\n🤖 AI: {response}")
                    
            except KeyboardInterrupt:
                print(f"\n\n👋 Chat interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"❌ A critical error occurred in the chat loop: {e}")
                traceback.print_exc()

def main():
    chat = TodowaChat()
    chat.run()

if __name__ == "__main__":
    main()