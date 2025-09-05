# --- Standard Library Imports ---
import os
import sys
import logging
import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Type

# --- Third-Party Imports ---
import jwt
from supabase import create_client, Client

# --- Project-Specific Imports ---
# Add the 'src' directory to the Python path to allow for absolute imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)


# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger('httpx').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- Import Core Components ---
try:
    import config
    from api_key_manager import ApiKeyManager
    # Agent Imports
    from multi_agent_system.agents.financial_agent import FinancialAgent
    from multi_agent_system.agents.tech_support_agent import TechSupportAgent
    from multi_agent_system.agents.journal_agent import JournalAgent
    from multi_agent_system.agents.task_agent import TaskAgent
    from multi_agent_system.agents.schedule_agent import ScheduleAgent
    from multi_agent_system.agents.brain_agent import BrainAgent
    from multi_agent_system.agents.finding_agent import FindingAgent
    from multi_agent_system.agents.guide_agent import GuideAgent
    from multi_agent_system.agents.general_fallback_agent import GeneralFallbackAgent
    from multi_agent_system.agents.answering_agent import AnsweringAgent
    from multi_agent_system.agents.context_resolution_agent import ContextResolutionAgent
    from multi_agent_system.agents.audit_agent import AuditAgent

except ImportError as e:
    logger.critical(f"❌ Import Error: {e}. Make sure you have all dependencies installed and the script is run from the project root.")
    sys.exit(1)

# --- Agent Mapping ---
# Maps a user-friendly name to the agent class
AGENT_MAP: Dict[str, Type] = {
    "FinancialAgent": FinancialAgent,
    "TechSupportAgent": TechSupportAgent,
    "JournalAgent": JournalAgent,
    "TaskAgent": TaskAgent,
    "ScheduleAgent": ScheduleAgent,
    "BrainAgent": BrainAgent,
    "FindingAgent": FindingAgent,
    "GuideAgent": GuideAgent,
    "GeneralFallbackAgent": GeneralFallbackAgent,
    # These agents are part of the main orchestration, but can be tested
    "AnsweringAgent": AnsweringAgent,
    "ContextResolutionAgent": ContextResolutionAgent,
    "AuditAgent": AuditAgent,
}

# --- Utility Functions (adapted from wa_version.py) ---

def create_user_jwt(user_id: str, jwt_secret: str) -> str:
    """Generates a JWT for a given user ID."""
    payload = {
        "sub": user_id,
        "role": "authenticated",
        "aud": "authenticated",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    return jwt.encode(payload, jwt_secret, algorithm="HS256")

def create_user_supabase_client(user_id: str) -> Optional[Client]:
    """Creates a new Supabase client authenticated for a specific user (RLS)."""
    if not all([config.SUPABASE_URL, config.SUPABASE_ANON_KEY, config.SUPABASE_JWT_SECRET]):
        logger.error("Supabase URL, Anon Key, or JWT Secret is not configured.")
        return None
    try:
        user_jwt = create_user_jwt(user_id, config.SUPABASE_JWT_SECRET)
        user_supabase_client = create_client(config.SUPABASE_URL, config.SUPABASE_ANON_KEY)
        user_supabase_client.auth.set_session(access_token=user_jwt, refresh_token="dummy-refresh-token")
        logger.info(f"Successfully created RLS-enabled client for user {user_id}")
        return user_supabase_client
    except Exception as e:
        logger.error(f"Error creating user-specific Supabase client: {e}", exc_info=True)
        return None

async def build_user_context(user_id: str, user_supabase_client: Optional[Client]) -> Dict[str, Any]:
    """Builds the user context dictionary required by agents."""
    context = {
        'user_info': {'timezone': 'GMT+7', 'user_id': user_id},
        'ai_brain': []
    }
    if not user_supabase_client:
        logger.warning("No Supabase client, cannot fetch AI brain memories.")
        return context
    try:
        # This is an async call in the original code, but the python client is sync
        # We will call it synchronously here.
        brain_result = user_supabase_client.table('ai_brain_memories').select('*').eq('user_id', user_id).limit(10).execute()
        if brain_result.data:
            context['ai_brain'] = brain_result.data
    except Exception as e:
        logger.warning(f"Could not fetch ai_brain context from database: {e}")
    return context


class AgentTesterCLI:
    """An interactive CLI for testing individual agents."""

    def __init__(self):
        self.api_key_manager: Optional[ApiKeyManager] = None

    def initialize(self) -> bool:
        """Initializes the API Key Manager."""
        logger.info("Initializing Agent Tester...")
        try:
            gemini_keys = config.get_gemini_api_keys()
            if not gemini_keys:
                logger.critical("No Gemini API keys found. Please set GEMINI_API_KEY1, etc. in your environment.")
                return False
            self.api_key_manager = ApiKeyManager(gemini_keys=gemini_keys)
            logger.info(f"✅ API Key Manager initialized with {self.api_key_manager.get_key_count()} key(s).")
            return True
        except Exception as e:
            logger.critical(f"❌ Initialization failed: {e}", exc_info=True)
            return False

    async def run(self):
        """Runs the main interactive loop for the CLI."""
        if not self.initialize():
            return

        logger.info("--- Welcome to the Agent Tester CLI ---")

        # Get User ID once
        user_id = input(f"Enter the User ID to test with (default: {config.CHAT_TEST_USER_ID}): ").strip()
        if not user_id:
            user_id = config.CHAT_TEST_USER_ID

        user_supabase_client = create_user_supabase_client(user_id)
        if not user_supabase_client:
            logger.error(f"Could not create a database client for user {user_id}. Some agents may fail.")

        while True:
            try:
                print("\nAvailable Agents:")
                for agent_name in AGENT_MAP.keys():
                    print(f"- {agent_name}")

                agent_name = input("\nEnter the name of the agent to test (or 'q' to quit): ").strip()
                if agent_name.lower() == 'q':
                    break
                if agent_name not in AGENT_MAP:
                    logger.error(f"Invalid agent name '{agent_name}'. Please choose from the list above.")
                    continue

                command = input(f"Enter the command for {agent_name}: ").strip()
                if not command:
                    logger.warning("Command cannot be empty.")
                    continue

                # --- Agent Processing ---
                logger.info(f"--- Testing {agent_name} ---")

                # Instantiate the agent
                agent_class = AGENT_MAP[agent_name]
                ai_model = self.api_key_manager.create_ai_model(agent_name)

                # Some agents don't need a supabase client
                try:
                    agent_instance = agent_class(ai_model=ai_model, supabase=user_supabase_client)
                except TypeError:
                    logger.info(f"{agent_name} does not require a Supabase client.")
                    agent_instance = agent_class(ai_model=ai_model)


                # Build context
                user_context = await build_user_context(user_id, user_supabase_client)

                # Process command
                logger.info(f"Processing command: '{command}'")
                result = agent_instance.process_command(user_command=command, user_context=user_context)

                # Print result
                print("\n--- Agent Result ---")
                print(json.dumps(result, indent=2, default=str))
                print("--------------------\n")

            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    cli = AgentTesterCLI()
    asyncio.run(cli.run())
