#!/usr/bin/env python3
"""
Answering Agent - Final Response Handler (Direct JSON Injection)
 
This agent formats the final user response by directly injecting a JSON
configuration from the database into the AI prompt. It is now upgraded to
handle both single and multi-step execution plans.

RESPONSIBILITIES:
- Process information from other agents.
- Format final responses for the user.
- Fetch a mandatory communication style JSON from the database.
- Inject this JSON directly into the AI prompt as a strict instruction.
- Apply standardized safety rules to every response.
- Convert UTC times to the user's timezone for display.
"""

import logging
from typing import Dict, Any, List
import json
import re
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

class AnsweringAgent:
    """Handles all final responses by directly applying a database-defined JSON style."""
    
    def __init__(self, ai_model, supabase=None):
        self.ai_model = ai_model
        self.supabase = supabase
        self.default_timezone_offset = 7  # GMT+7 (Indonesia/Jakarta)
        logger.info("🤖 AnsweringAgent initialized (Direct JSON Injection Mode)")
    
    # --- NEW METHOD: process_multi_response ---
    def process_multi_response(self, context: Dict[str, Any]) -> str:
        """
        Processes the output from MULTIPLE specialist agents (from a multi-step plan)
        and synthesizes a single, coherent response for the user. This is the new
        primary entry point for the Master Planner architecture.
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
        Formats a generic, safe error message to be shown to the user.
        It logs the technical details but only shows a polite message.
        """
        logger.error(f"AnsweringAgent is processing a system error: {error_message}")
        # This can be a static message or could use the AI for a more natural tone.
        # For reliability, a static message is often safer.
        return "I seem to have run into an unexpected problem. My developers have been notified and are looking into it."

    def process_response(self, information: Dict[str, Any]) -> str:
        """
        Processes information from a single agent (or a consolidated package) 
        and generates the final user response.
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
        """Formats a clarification request to the user."""
        try:
            # Using a simple, reliable f-string for this is often better than an AI call.
            return f"Maaf, saya kurang mengerti. Bisakah Anda memperjelas maksud Anda tentang '{clarification_request}'? 🤔"
        except Exception as e:
            logger.error(f"❌ Error in clarification: {e}")
            return f"Maaf, bisakah Anda memberikan informasi lebih jelas? {clarification_request}"

    # --- PRIVATE HELPER METHODS (Unchanged) ---

    def _convert_utc_to_user_timezone(self, text_content: str, user_timezone_info: dict) -> str:
        """
        Convert UTC timestamps in text content to user's timezone for display.
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
        Fetches a mandatory communication style JSON from the database and formats it
        for direct injection into the AI prompt.
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
            "Strictly avoid generating any content that is illegal, harmful, racist, sexist, unethical, or promotes hate speech. "
            "Maintain a respectful, professional, and safe tone at all times. "
            "Never show raw JSON, internal system details, debugging information, or your thinking process."
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