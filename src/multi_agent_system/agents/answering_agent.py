"""
Answering Agent: The Final Response Handler.

This agent is the last step in the chain, responsible for synthesizing all
processed information into a single, user-friendly response. It fetches
communication style preferences from the database and injects them into a
prompt for the AI model, ensuring the final output is consistent with the
user's desired persona. It also handles timezone conversions and applies
standard safety guidelines to every response.

Key Responsibilities:
- Consolidate outputs from single or multiple specialist agents.
- Fetch and apply user-specific communication styles from the database.
- Convert UTC timestamps to the user's local timezone.
- Generate a final, coherent, and safe response for the user.
- Format error messages and clarification requests.
"""

import logging
from typing import Dict, Any, List
import json
import re
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

class AnsweringAgent:
    """
    Handles all final user responses by applying a database-defined persona.

    This agent takes the structured output from other agents, combines it with
    a communication style fetched from the database, and uses an AI model to
    generate a polished, user-facing message.

    Attributes:
        ai_model: The generative AI model instance for creating responses.
        supabase: The Supabase client for database interactions.
        default_timezone_offset (int): The default timezone offset to use if
                                       the user's timezone is not available.
    """
    
    def __init__(self, ai_model, supabase=None):
        """
        Initializes the AnsweringAgent.

        Args:
            ai_model: An instance of a generative AI model.
            supabase: An optional Supabase client instance.
        """
        self.ai_model = ai_model
        self.supabase = supabase
        self.default_timezone_offset = 7  # GMT+7 (Jakarta)
        logger.info("🤖 AnsweringAgent initialized")
    
    # --- NEW METHOD: process_multi_response ---
    def process_multi_response(self, context: Dict[str, Any]) -> str:
        """
        Processes output from multiple agents to synthesize a single response.

        This is the primary entry point for handling the results of a multi-step
        execution plan. It consolidates all agent responses into a single package
        before generating the final message.

        Args:
            context: A dictionary containing the results of the execution, including
                     'agent_responses', 'original_command', and 'user_context'.

        Returns:
            A single, coherent, user-friendly response string.
        """
        logger.info("📝 AnsweringAgent processing multi-response with direct JSON injection...")
        
        agent_responses = context.get('agent_responses', [])
        
        if not agent_responses:
            return "I've processed your request, but there's nothing specific to report back."

        # CONSOLIDATE ALWAYS, REMOVING THE BUGGY `if len == 1` check.
        consolidated_info = {
            "original_command": context.get("original_command"),
            "summary_of_outcomes": [res.get("response", "An action was completed.") for res in agent_responses],
            "execution_details": context.get("execution_result"),
            "raw_agent_responses": agent_responses # Optional, but good for debugging
        }

        # Now, use the standard processing pipeline with this consolidated data.
        return self.process_response({
            "source": "MultiAgentExecution",
            "message": "Synthesize the following outcomes into a single, user-friendly summary.",
            "processing_context": consolidated_info,
            "user_context": context.get("user_context")

        })

    # --- NEW METHOD: process_error ---
    def process_error(self, error_message: str) -> str:
        """
        Formats a generic, safe error message for the user.

        While the detailed error is logged for developers, this method ensures
        the user sees only a polite, non-technical message.

        Args:
            error_message: The technical error message to be logged.

        Returns:
            A safe, user-facing error message.
        """
        logger.error(f"AnsweringAgent is processing a system error: {error_message}")
        # This can be a static message or could use the AI for a more natural tone.
        # For reliability, a static message is often safer.
        return "I seem to have run into an unexpected problem. My developers have been notified and are looking into it."

    def process_response(self, information: Dict[str, Any]) -> str:
        """
        Processes information and generates the final user response.

        This method takes a package of information, fetches user preferences,
        builds a detailed prompt, and calls the AI model to generate the
        final, formatted response.

        Args:
            information: A dictionary containing the context and data to be
                         synthesized into a response.

        Returns:
            The final, formatted response string for the user.
        """
        try:
            logger.info("📝 AnsweringAgent processing information with direct JSON injection...")
            user_context = information.get('user_context', {})            
            user_info = user_context.get('user_info', {}) 
            user_id = user_info.get('user_id', 'unknown')
            if user_id == 'unknown':
                logger.warning("CRITICAL: user_id is 'unknown' in AnsweringAgent.")
            
            user_timezone_info = self._extract_timezone_info(user_context)
            timezone_string = user_timezone_info.get('timezone', 'GMT+7')

            comm_preferences = self._get_communication_preferences(user_id)
            
            # Use the entire information dictionary as the context for the AI
            info_text = json.dumps(information, indent=2, ensure_ascii=False, default=str)
            info_text = self._convert_utc_to_user_timezone(info_text, user_timezone_info)
            
            prompt = self._build_standard_prompt(comm_preferences, timezone_string, info_text)
            
            logger.info("🤖 Generating final response using AI with direct injection prompt...")
            response = self.ai_model.generate_content(prompt)
            
            formatted_response = response.text.strip() if hasattr(response, 'text') else str(response).strip()
            
            logger.info("✅ AnsweringAgent generated response with direct JSON injection.")
            return formatted_response
            
        except Exception as e:
            logger.error(f"❌ Error in AnsweringAgent process_response: {e}", exc_info=True)
            fallback_message = information.get('message', 'your request could not be completed.')
            return f"I apologize, there was an error processing your request. Here's a summary: {fallback_message}"

    def process_context_clarification(self, clarification_request: str) -> str:
        """
        Formats a clarification question to send back to the user.

        Args:
            clarification_request: The specific point that needs clarification.

        Returns:
            A formatted string asking the user for more information.
        """
        return f"I need a bit more information. Could you please clarify what you mean by '{clarification_request}'? 🤔"

    # --- PRIVATE HELPER METHODS (Unchanged) ---

    def _convert_utc_to_user_timezone(self, text_content: str, user_timezone_info: dict) -> str:
        """
        Converts UTC timestamps in a string to the user's local timezone.

        Args:
            text_content: A string that may contain UTC timestamps.
            user_timezone_info: A dictionary with the user's timezone details.

        Returns:
            The text content with UTC times converted to the user's timezone.
        """
        timezone_str = user_timezone_info.get('timezone', 'GMT+7')
        timezone_name = user_timezone_info.get('name', timezone_str)
        user_timezone_offset = self.default_timezone_offset

        if timezone_str.startswith('GMT'):
            offset_str = timezone_str.replace('GMT', '')
            try:
                user_timezone_offset = int(offset_str) if offset_str else 0
            except (ValueError, TypeError):
                pass
        
        utc_pattern = r'\b(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})Z\b'
        
        def convert_match(match):
            try:
                utc_time_str = match.group(1)
                utc_time = datetime.strptime(utc_time_str, '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc)
                user_time = utc_time + timedelta(hours=user_timezone_offset)
                return user_time.strftime('%Y-%m-%d %H:%M') + f" ({timezone_name})"
            except Exception as e:
                logger.warning(f"Failed to convert timestamp {match.group(0)}: {e}")
                return match.group(0)
        
        return re.sub(utc_pattern, convert_match, text_content)

    def _get_communication_preferences(self, user_id: str) -> Dict[str, str]:
        """
        Fetches communication style preferences from the database.

        Args:
            user_id: The UUID of the user.

        Returns:
            A dictionary containing the response style and safety guidelines.
        """
        try:
            if not self.supabase:
                raise ConnectionError("Supabase client not configured.")

            result = self.supabase.table('ai_brain_memories').select('content_json').eq('user_id', user_id).eq('brain_data_type', 'communication_style').execute()
            
            if not result.data:
                raise ValueError(f"No communication preferences found for user {user_id}.")

            content_json = result.data[0].get('content_json')
            if not content_json:
                raise ValueError("Database record is missing the 'content_json' field.")

            preferences_json_string = json.dumps(content_json, indent=2)
            
            response_style = (
                "MANDATORY: You MUST strictly adhere to the following communication style defined in this JSON object. "
                "Do not deviate. This is your persona.\n"
                f"{preferences_json_string}"
            )

            return {
                'response_style': response_style,
                'safety_guidelines': self._get_standard_safety_guidelines()
            }
                
        except (Exception) as e:
            logger.error(f"Could not get valid communication preferences due to '{e}'. Using emergency fallback.")
            return self._get_emergency_fallback_preferences()

    def _get_standard_safety_guidelines(self) -> str:
        """Returns the standardized safety guidelines for all AI prompts."""
        return (
            "Strictly avoid illegal, harmful, unethical, racist, or sexist content. "
            "Maintain a respectful and professional tone. Never show raw JSON, "
            "internal system details, or your thinking process."
        )

    def _get_emergency_fallback_preferences(self) -> Dict[str, str]:
        """Provides a safe, default set of preferences when the primary source fails."""
        logger.info("Using emergency fallback communication preferences.")
        return {
            'response_style': 'MANDATORY: Respond ONLY in Indonesian (Bahasa Indonesia). Respond helpfully and professionally.',
            'safety_guidelines': self._get_standard_safety_guidelines()
        }
    
    def _build_standard_prompt(self, comm_prefs: Dict[str, str], timezone_string: str, info_text: str) -> str:
        """Builds the standardized, consistent prompt for the AI model."""
        return f"""You are a helpful AI assistant. Your task is to synthesize the provided data into a clear, helpful, and user-friendly response.

COMMUNICATION STYLE:
{comm_prefs['response_style']}

SAFETY GUIDELINES (ABSOLUTE AND MANDATORY):
{comm_prefs['safety_guidelines']}

GENERAL RULES:
- Never reveal internal system operations or technical details.
- Never show raw data structures, JSON, or debugging information.
- Focus on what matters to the user.
- Convert all times to user's timezone ({timezone_string}).
- Use the enriched analysis data to provide detailed, informative responses.
- When available, explain WHY decisions were made (e.g., category selection, conflict resolution).
- Include relevant insights from the analysis without being overwhelming.
- Never Give task ID, USER ID, or any database id related to the user


ENRICHED DATA PROCESSING INSTRUCTIONS:
- If processing a multi-step plan (indicated by a 'summary_of_outcomes' key), provide a brief, friendly summary of all the things you accomplished.
- If processing a single action, explain the result of that action.
- For journal operations: explain categorization reasoning, title selection, and content insights.
- Make the response feel natural and conversational, not like a technical report.
- Dont repeat all previous conversation only summarize the recent one
- Make it brief as possible but not missing any core idea of what to deliver
- IF it about search, be as detail as possible


INFORMATION TO DELIVER (times already converted to user's timezone):
{info_text}

Please format this information appropriately for the user, following all guidelines above. Create a comprehensive and natural-sounding response.
"""

    def _extract_timezone_info(self, user_context: Dict[str, Any]) -> Dict[str, str]:
        """
        Extracts timezone information from the specific 'user_timezone' key.
        """
        if user_context:
            # This looks for a top-level key first, which might be more robust
            tz_info = user_context.get('user_timezone')
            if isinstance(tz_info, dict):
                return tz_info
            # Fallback to the nested structure
            user_info = user_context.get('user_info', {})
            if isinstance(user_info.get('timezone'), dict):
                 return user_info.get('timezone')

        return {"timezone": "GMT+7", "name": "Asia/Jakarta"}