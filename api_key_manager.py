import itertools
import logging
from typing import Dict, List, Any, Optional

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

logger = logging.getLogger(__name__)


class ResilientGeminiModel:
    """
    A proxy wrapper around the Gemini model that handles API key rotation
    on failures like quota errors or permission issues, using the ApiKeyManager.
    """
    def __init__(self, key_manager: 'ApiKeyManager', agent_name: str, is_json_model: bool):
        self._key_manager = key_manager
        self._agent_name = agent_name
        self._is_json_model = is_json_model
        
        self._current_key: Optional[str] = None
        self._current_model: Optional[genai.GenerativeModel] = None
        
        # Initialize the first model with the first valid key
        self._get_new_model()

    def _get_new_model(self):
        """Fetches the next valid key and creates a new internal model instance."""
        self._current_key = self._key_manager.get_next_key()
        if self._current_key is None:
            self._current_model = None
            raise RuntimeError(f"All available Gemini API keys have failed for agent '{self._agent_name}'.")

        logger.info(f"Agent '{self._agent_name}' is now using a new API key ending in ...{self._current_key[-4:]}")
        genai.configure(api_key=self._current_key)
        
        # Configure the model based on whether JSON output is required
        if self._is_json_model:
            self._current_model = genai.GenerativeModel(
                'gemini-1.5-flash-latest',
                generation_config={"response_mime_type": "application/json"}
            )
        else:
            self._current_model = genai.GenerativeModel('gemini-2.5-flash-lite') # Updated model name

    def generate_content(self, *args, **kwargs) -> Any:
        """
        A wrapper for the real generate_content method that includes retry logic.
        It will cycle through all available keys if failures occur.
        """
        if self._current_model is None:
            raise RuntimeError(f"No valid model available for agent '{self._agent_name}'. All keys may be broken.")

        # The number of retries is limited by the number of initially valid keys.
        for attempt in range(self._key_manager.get_valid_key_count()):
            try:
                # Attempt the API call with the current model
                return self._current_model.generate_content(*args, **kwargs)
            
            except (google_exceptions.ResourceExhausted, google_exceptions.PermissionDenied) as e:
                error_type = "Quota Exceeded (ResourceExhausted)" if isinstance(e, google_exceptions.ResourceExhausted) else "Permission Denied"
                logger.warning(f"{error_type} for agent '{self._agent_name}' with key ending in ...{self._current_key[-4:]}. Marking key as broken and rotating.")
                
                # Mark the failed key as broken for the current session
                self._key_manager.mark_key_as_broken(self._current_key)
                
                # Try to get a new model with the next available key
                try:
                    self._get_new_model()
                except RuntimeError:
                    # This happens if we've run out of keys
                    logger.error(f"All available keys have failed. Raising final exception for agent '{self._agent_name}'.")
                    raise e # Re-raise the last caught exception
                
                # If we successfully got a new model, the loop will continue and retry the call.

        # If the loop finishes without a successful return, it means all keys were tried and failed.
        raise RuntimeError(f"Failed to get a response for agent '{self._agent_name}' after trying all available API keys.")


class ApiKeyManager:
    """
    Manages and rotates Gemini API keys entirely in memory. This version is
    stateless and does not persist the 'broken' status of keys to a file,
    making it safe and reliable for serverless environments like Vercel.
    """

    def __init__(self, gemini_keys: Dict[str, str]):
        if not gemini_keys:
            raise ValueError("Gemini API key dictionary cannot be empty.")

        # Initialize all keys with a 'is_broken' status of False.
        # The status is only tracked in memory for this instance's lifetime.
        self._keys: List[Dict[str, Any]] = [
            {"value": key_value, "is_broken": False}
            for key_name, key_value in gemini_keys.items()
        ]

        if not self._keys:
            raise ValueError("No valid Gemini API keys were loaded from the configuration.")

        # The cycler will loop through the list of keys indefinitely.
        self._key_cycle = itertools.cycle(self._keys)
        logger.info(f"ApiKeyManager initialized with {len(self._keys)} Gemini API key(s).")

    def mark_key_as_broken(self, key_value: str):
        """Marks a specific key as broken in memory for the current session."""
        for key_info in self._keys:
            if key_info['value'] == key_value:
                if not key_info['is_broken']:
                    key_info['is_broken'] = True
                    logger.warning(f"Marked key ending in ...{key_value[-4:]} as broken for this session.")
                break

    def get_next_key(self) -> Optional[str]:
        """
        Gets the next valid (not broken) Gemini key from the in-memory list.
        Returns None if all keys have been marked as broken during this session.
        """
        if self.get_valid_key_count() == 0:
            logger.error("All Gemini keys are marked as broken for this session.")
            return None

        # Cycle through the keys until a non-broken one is found.
        # We loop at most the total number of keys to avoid an infinite loop.
        for _ in range(len(self._keys)):
            key_info = next(self._key_cycle)
            if not key_info['is_broken']:
                return key_info['value']
        
        # This should not be reached if get_valid_key_count() > 0, but is a safeguard.
        return None

    def create_ai_model(self, agent_name: str = "default") -> ResilientGeminiModel:
        """Creates a resilient JSON-ONLY Gemini client instance for specialist agents."""
        return ResilientGeminiModel(key_manager=self, agent_name=agent_name, is_json_model=True)

    def create_chat_model(self, agent_name: str = "default") -> ResilientGeminiModel:
        """Creates a resilient NATURAL LANGUAGE Gemini client for user-facing chat."""
        return ResilientGeminiModel(key_manager=self, agent_name=agent_name, is_json_model=False)

    def get_key_count(self) -> int:
        """Returns the total number of keys loaded."""
        return len(self._keys)

    def get_valid_key_count(self) -> int:
        """Returns the number of keys NOT marked as broken in this session."""
        return sum(1 for key in self._keys if not key['is_broken'])