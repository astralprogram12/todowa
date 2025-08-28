#!/usr/bin/env python3
"""
Answering Agent - Final Response Handler (Direct JSON Injection)

This agent formats the final user response by directly injecting a JSON
configuration from the database into the AI prompt. The script does not
interpret the preferences; it only enforces them.

RESPONSIBILITIES:
- Process information from other agents.
- Format final responses for the user.
- Fetch a mandatory communication style JSON from the database.
- Inject this JSON directly into the AI prompt as a strict instruction.
- Apply standardized safety rules to every response.
- Convert UTC times to the user's timezone for display.
"""

import logging
from typing import Dict, Any
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
                pass # Keep default on parsing error
        
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

            # --- Direct JSON Injection Logic ---
            # Convert the Python dict to a formatted JSON string for the prompt.
            preferences_json_string = json.dumps(content_json, indent=2)
            
            # Create the response_style string that embeds the raw JSON.
            response_style = (
                "MANDATORY: You MUST strictly adhere to the following communication style defined in this JSON object. "
                "Do not deviate. This is your persona.\n"
                f"{preferences_json_string}"
            )
            # --- End of Direct Injection Logic ---

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
    
    def process_response(self, information: Dict[str, Any]) -> str:
        """
        Process information from other agents and generate the final user response.
        """
        try:
            logger.info("📝 AnsweringAgent processing information with direct JSON injection...")
            user_context = information.get('user_context', {})            
            user_info = user_context.get('user_info', {}) 
            user_id = user_info.get('user_id', 'unknown')
            if user_id == 'unknown':
                logger.warning("CRITICAL: user_id is 'unknown' even after attempting to read from user_info. The context package might be malformed.")
            
            user_timezone_info = self._extract_timezone_info(user_context)
            timezone_string = user_timezone_info.get('timezone', 'GMT+7')

            comm_preferences = self._get_communication_preferences(user_id)
            
            info_text = json.dumps(information, indent=2, ensure_ascii=False)
            info_text = self._convert_utc_to_user_timezone(info_text, user_timezone_info)
            
            prompt = self._build_standard_prompt(comm_preferences, timezone_string, info_text)
            
            logger.info("🤖 Generating final response using AI with direct injection prompt...")
            response = self.ai_model.generate_content(prompt)
            
            formatted_response = response.text.strip() if hasattr(response, 'text') else str(response).strip()
            formatted_response = self._convert_utc_to_user_timezone(formatted_response, user_timezone_info)
            
            logger.info("✅ AnsweringAgent generated response with direct JSON injection.")
            return formatted_response
            
        except Exception as e:
            logger.error(f"❌ Error in AnsweringAgent process_response: {e}")
            fallback_message = self._convert_utc_to_user_timezone(
                information.get('message', 'your request could not be completed.'),
                {"timezone": "GMT+7", "name": "Asia/Jakarta"}
            )
            return f"I apologize, there was an error processing your request. {fallback_message}"

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
- If operation summaries are available, use them to explain what was accomplished but be very brief.
- If analysis data is available, incorporate relevant insights naturally into your response.
- For journal operations: explain categorization reasoning, title selection, and content insights.
- Make the response feel natural and conversational, not like a technical report.


INFORMATION TO DELIVER (times already converted to user's timezone):
{info_text}

Please format this information appropriately for the user, following all guidelines above. Create a comprehensive and natural-sounding response.
"""

    def _extract_timezone_info(self, user_context: Dict[str, Any]) -> Dict[str, str]:
        """
        Extracts timezone information from the specific 'user_timezone' key.
        """
        if user_context:
            tz_info = user_context.get('user_timezone')
            if isinstance(tz_info, dict):
                return tz_info
        
        return {"timezone": "GMT+7", "name": "Asia/Jakarta"}

    def process_chat_json_response(self, json_response: Dict[str, Any], user_context: Dict[str, Any] = None) -> str:
        """
        Process structured JSON response and generate final user response.
        """
        try:
            logger.info("🎯 Processing JSON response with direct injection rules...")
            user_id = user_context.get('user_id', 'unknown') if user_context else 'unknown'
            user_timezone_info = self._extract_timezone_info(user_context)
            timezone_string = user_timezone_info.get('timezone', 'GMT+7')
            comm_preferences = self._get_communication_preferences(user_id)
            info_text = json.dumps(json_response, indent=2, ensure_ascii=False)
            info_text = self._convert_utc_to_user_timezone(info_text, user_timezone_info)
            prompt = self._build_standard_prompt(comm_preferences, timezone_string, info_text)
            
            response = self.ai_model.generate_content(prompt)
            
            if hasattr(response, 'text') and response.text:
                return self._convert_utc_to_user_timezone(response.text.strip(), user_timezone_info)
            
            logger.warning("AI response was empty, generating fallback.")
            return f"I have processed your request based on the provided information: {json_response.get('user_message', '')}"
                
        except Exception as e:
            logger.error(f"❌ Error processing chat JSON response: {e}")
            return "I apologize, but I encountered a technical difficulty. Please try again."

    def process_context_clarification(self, clarification_request: str) -> str:
        """Formats a clarification request to the user."""
        try:
            prompt = f'Translate and format this clarification request in friendly Indonesian with an emoji. Include the test phrase \n\nRequest: "{clarification_request}"'
            response = self.ai_model.generate_content(prompt)
            return response.text.strip() if hasattr(response, 'text') else str(response).strip()
        except Exception as e:
            logger.error(f"❌ Error in clarification: {e}")
            return f"Maaf, bisakah Anda memberikan informasi lebih jelas? {clarification_request} 🤔 this is answering agent test"