# V4.0 WhatsApp App Orchestrator - Complete Integration
# Copy of CLI orchestrator adapted for WhatsApp

import sys
import os

# Add CLI app path for shared components
cli_root = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'wa_todo_ai_modern_cli_4.0_AGENT')
sys.path.insert(0, cli_root)

from src.multi_agent_system.orchestrator import OrchestratorV4

# Use same V4.0 orchestrator for WhatsApp app
class WhatsAppOrchestratorV4(OrchestratorV4):
    """WhatsApp-specific V4.0 orchestrator with same capabilities as CLI."""
    
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model)
        
    async def process_whatsapp_message(self, user_id: str, message: str, phone_number: str):
        """Process WhatsApp message using V4.0 features."""
        return await self.process_user_input(user_id, message, phone_number)

# Alias for backward compatibility
Orchestrator = WhatsAppOrchestratorV4
