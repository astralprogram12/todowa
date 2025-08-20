# src/multi_agent_system/__init__.py

# This file helps define the multi_agent_system as a Python package.

# --- [THE FIX] ---
# We are no longer using the 'create_multi_agent_system' function.
# The application now imports the 'Orchestrator' class directly.
# We are changing this file to reflect the new, correct structure.
from .orchestrator import Orchestrator
# --- [END OF FIX] ---

# You can also export other components here if needed in the future, for example:
# from .agents import BaseAgent