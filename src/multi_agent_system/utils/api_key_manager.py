"""
API Key Manager for OpenAI Client Rotation

This module provides centralized management of OpenAI API keys to avoid rate limiting
by rotating through multiple keys in a round-robin fashion.
"""

import os
import itertools
import logging
from typing import List, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class APIKeyManager:
    """Manages rotation of OpenAI API keys to distribute API calls and avoid rate limits."""
    
    def __init__(self):
        self._keys: List[str] = []
        self._key_cycle: Optional[itertools.cycle] = None
        self._load_keys()
    
    def _load_keys(self) -> None:
        """Load API keys from environment variable."""
        keys_env = os.getenv('OPENAI_API_KEYS', '')
        
        if not keys_env:
            # Fallback to single key if multiple keys not configured
            single_key = os.getenv('OPENAI_API_KEY', '')
            if single_key:
                self._keys = [single_key]
                logger.warning("Using single API key. Consider setting OPENAI_API_KEYS for rotation.")
            else:
                raise ValueError("No OpenAI API keys found. Set OPENAI_API_KEY or OPENAI_API_KEYS environment variable.")
        else:
            # Parse comma-separated keys and clean whitespace
            self._keys = [key.strip() for key in keys_env.split(',') if key.strip()]
            
        if not self._keys:
            raise ValueError("No valid OpenAI API keys found.")
            
        # Create cycle iterator for rotation
        self._key_cycle = itertools.cycle(self._keys)
        
        logger.info(f"Loaded {len(self._keys)} OpenAI API key(s) for rotation.")
    
    def get_next_key(self) -> str:
        """Get the next API key in rotation."""
        if not self._key_cycle:
            raise RuntimeError("API keys not initialized.")
        return next(self._key_cycle)
    
    def get_client(self) -> OpenAI:
        """Create OpenAI client with the next API key in rotation."""
        api_key = self.get_next_key()
        return OpenAI(api_key=api_key)
    
    def get_key_count(self) -> int:
        """Return the number of available API keys."""
        return len(self._keys)


# Global instance for shared use across the application
_api_key_manager = None


def get_api_key_manager() -> APIKeyManager:
    """Get the global APIKeyManager instance."""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager


def get_openai_client() -> OpenAI:
    """Convenience function to get an OpenAI client with rotating API keys."""
    return get_api_key_manager().get_client()


def get_next_api_key() -> str:
    """Convenience function to get the next API key in rotation."""
    return get_api_key_manager().get_next_key()