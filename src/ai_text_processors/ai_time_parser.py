"""
AI-Powered Time Parser for Natural Language Understanding

This parser replaces all regex-based time parsing with AI natural language
understanding to parse time expressions in any language with context awareness.
"""

import os
import sys
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Tuple, Union

# Add parent directories to Python path to access config
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, parent_dir)

try:
    import google.generativeai as genai
    import config
except ImportError as e:
    logging.error(f"Failed to import required modules: {e}")
    raise

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AITimeParser:
    """AI-powered time parser using Gemini AI for natural language understanding."""
    
    def __init__(self):
        """Initialize the AI time parser with Gemini configuration."""
        try:
            genai.configure(api_key=config.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            logger.info("AI Time Parser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AI Time Parser: {e}")
            raise
    
    def parse_time_expression(self, text: str, current_time: Optional[datetime] = None, user_timezone: str = "UTC") -> Dict[str, any]:
        """
        Parse time expressions using AI natural language understanding.
        
        Args:
            text (str): The text containing time expression
            current_time (datetime): Current time reference (defaults to now)
            user_timezone (str): User's timezone (e.g., 'Asia/Jakarta')
            
        Returns:
            Dict containing:
            - parsed_datetime: datetime object in UTC
            - confidence: parsing confidence (0.0-1.0)
            - time_type: 'relative', 'absolute', 'ambiguous'
            - original_expression: extracted time expression
            - user_friendly_time: human readable time in user timezone
            - is_reminder: boolean indicating if this is a reminder request
            - task_description: extracted task/reminder description
        """
        if not text or not text.strip():
            return self._get_fallback_result(text, current_time)
        
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        try:
            # Format current time for AI context
            current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S UTC")
            
            prompt = f"""You are an expert time parsing AI that understands natural language time expressions in multiple languages.

Current time reference: {current_time_str}
User timezone: {user_timezone}

Analyze the following text and extract time information. Return a JSON response with this exact format:

{{
  "has_time_expression": true/false,
  "time_type": "relative/absolute/ambiguous",
  "parsed_datetime_utc": "2025-08-21T21:41:07Z",
  "confidence": 0.95,
  "original_expression": "5 menit lagi",
  "user_friendly_time": "in 5 minutes",
  "is_reminder": true/false,
  "task_description": "buang sampah",
  "language_detected": "Indonesian",
  "parsing_notes": "explanation of parsing logic"
}}

IMPORTANT PARSING RULES:
1. **Relative Time Examples:**
   - "5 menit lagi" → current_time + 5 minutes
   - "in 10 mins" → current_time + 10 minutes
   - "dalam 1 jam" → current_time + 1 hour
   - "besok" (tomorrow) → next day at reasonable time (15:00)
   - "hari ini" (today) → today at reasonable time

2. **Absolute Time Examples:**
   - "tomorrow at 3" → next day at 15:00
   - "Friday 2pm" → next Friday at 14:00
   - "jam 9 pagi" → today or tomorrow at 09:00

3. **Language-Specific Keywords:**
   - Indonesian: "ingetin", "menit", "jam", "lagi", "besok", "hari ini"
   - Spanish: "recuérdame", "minutos", "hora", "mañana"
   - French: "rappelle-moi", "minutes", "heure", "demain", "dans"
   - English: "remind me", "in", "at", "tomorrow", "today"

4. **Task Description Extraction:**
   - Extract the main task/reminder content
   - Remove time expressions and reminder keywords
   - Examples: "ingetin 5 menit lagi buang sampah" → "buang sampah"

5. **Confidence Scoring:**
   - 0.9+ : Clear time expression with specific duration/time
   - 0.7-0.9 : Reasonable interpretation with some ambiguity
   - 0.5-0.7 : Ambiguous but parseable
   - <0.5 : Very uncertain or no clear time

6. **Time Zone Handling:**
   - Always return parsed_datetime_utc in UTC format
   - Consider user_timezone for relative time calculations
   - Format: "2025-08-21T21:41:07Z"

7. **Special Cases:**
   - If no clear time expression, set has_time_expression to false
   - For ambiguous times, use reasonable defaults (e.g., 15:00 for "tomorrow")
   - Handle informal expressions like "mins", "hrs", etc.

Text to analyze: "{text}"

JSON Response:"""

            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean the response to extract JSON
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Parse JSON response
            import json
            try:
                result = json.loads(response_text)
                
                # Validate and process the result
                result = self._validate_and_process_result(result, text, current_time)
                
                logger.debug(f"Time parsing result: {result}")
                return result
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Raw response: {response_text}")
                return self._get_fallback_result(text, current_time)
                
        except Exception as e:
            logger.error(f"Error in time parsing: {e}")
            return self._get_fallback_result(text, current_time)
    
    def _validate_and_process_result(self, result: Dict, original_text: str, current_time: datetime) -> Dict:
        """Validate and process the AI parsing result."""
        # Ensure required fields exist
        required_fields = {
            'has_time_expression': False,
            'time_type': 'ambiguous',
            'parsed_datetime_utc': None,
            'confidence': 0.5,
            'original_expression': '',
            'user_friendly_time': '',
            'is_reminder': True,
            'task_description': original_text,
            'language_detected': 'unknown',
            'parsing_notes': ''
        }
        
        for field, default_value in required_fields.items():
            if field not in result:
                result[field] = default_value
        
        # Process datetime
        if result.get('parsed_datetime_utc'):
            try:
                # Parse the datetime string
                if isinstance(result['parsed_datetime_utc'], str):
                    # Handle various datetime formats
                    datetime_str = result['parsed_datetime_utc']
                    if datetime_str.endswith('Z'):
                        parsed_dt = datetime.fromisoformat(datetime_str[:-1]).replace(tzinfo=timezone.utc)
                    else:
                        parsed_dt = datetime.fromisoformat(datetime_str).replace(tzinfo=timezone.utc)
                    
                    result['parsed_datetime'] = parsed_dt
                else:
                    result['parsed_datetime'] = current_time
            except Exception as e:
                logger.error(f"Error parsing datetime: {e}")
                result['parsed_datetime'] = current_time
                result['confidence'] = max(0.1, result.get('confidence', 0.5) - 0.3)
        else:
            result['parsed_datetime'] = current_time
        
        # Add original text
        result['original_text'] = original_text
        
        return result
    
    def _get_fallback_result(self, text: str, current_time: datetime) -> Dict[str, any]:
        """Return fallback result when parsing fails."""
        return {
            'original_text': text,
            'has_time_expression': False,
            'time_type': 'ambiguous',
            'parsed_datetime': current_time,
            'parsed_datetime_utc': current_time.isoformat().replace('+00:00', 'Z'),
            'confidence': 0.1,
            'original_expression': '',
            'user_friendly_time': 'now',
            'is_reminder': True,
            'task_description': text,
            'language_detected': 'unknown',
            'parsing_notes': 'Fallback result due to parsing error'
        }
    
    def parse_relative_time(self, text: str, current_time: Optional[datetime] = None) -> Dict[str, any]:
        """
        Specialized parser for relative time expressions.
        
        Args:
            text (str): Text with relative time expression
            current_time (datetime): Current time reference
            
        Returns:
            Dict: Parsed time result
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        # Use the main parsing method with focus on relative times
        result = self.parse_time_expression(text, current_time)
        
        # If it's not detected as relative, try to force relative interpretation
        if result.get('time_type') != 'relative' and result.get('confidence', 0) < 0.7:
            # Try to extract common relative patterns
            text_lower = text.lower()
            
            # Indonesian relative patterns
            if 'menit lagi' in text_lower or 'menit' in text_lower:
                import re
                match = re.search(r'(\d+)\s*menit', text_lower)
                if match:
                    minutes = int(match.group(1))
                    new_time = current_time + timedelta(minutes=minutes)
                    result.update({
                        'parsed_datetime': new_time,
                        'parsed_datetime_utc': new_time.isoformat().replace('+00:00', 'Z'),
                        'time_type': 'relative',
                        'confidence': 0.85,
                        'user_friendly_time': f'in {minutes} minutes',
                        'original_expression': match.group(0)
                    })
        
        return result

# Global instance for efficient reuse
_time_parser_instance: Optional[AITimeParser] = None

def get_ai_time_parser() -> AITimeParser:
    """Get or create a singleton instance of the AI time parser."""
    global _time_parser_instance
    if _time_parser_instance is None:
        _time_parser_instance = AITimeParser()
    return _time_parser_instance

def parse_time_with_ai(text: str, current_time: Optional[datetime] = None, user_timezone: str = "UTC") -> Dict[str, any]:
    """
    Parse time expressions using AI with natural language understanding.
    
    Args:
        text (str): The input text containing time expressions
        current_time (datetime): Current time reference
        user_timezone (str): User's timezone
        
    Returns:
        Dict: Comprehensive time parsing result
    """
    if not text:
        return {
            'original_text': text,
            'has_time_expression': False,
            'parsed_datetime': current_time or datetime.now(timezone.utc)
        }
    
    try:
        parser = get_ai_time_parser()
        return parser.parse_time_expression(text, current_time, user_timezone)
    except Exception as e:
        logger.error(f"AI time parsing failed, returning fallback: {e}")
        fallback_time = current_time or datetime.now(timezone.utc)
        return {
            'original_text': text,
            'has_time_expression': False,
            'time_type': 'ambiguous',
            'parsed_datetime': fallback_time,
            'confidence': 0.1,
            'is_reminder': True,
            'task_description': text
        }
