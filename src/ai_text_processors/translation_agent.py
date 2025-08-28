"""
AI-Powered Translation Agent for Multilingual Support

This agent handles language detection and translation to English for processing,
while preserving original context and intent. It handles informal language,
typos, and colloquialisms from various languages.
"""

import os
import sys
import logging
from typing import Optional, Dict, Tuple

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

class TranslationAgent:
    """AI-powered translation agent using Gemini AI for multilingual support."""
    
    def __init__(self):
        """Initialize the translation agent with Gemini configuration."""
        try:
            genai.configure(api_key=config.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            logger.info("Translation Agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Translation Agent: {e}")
            raise
    
    def detect_and_translate(self, text: str) -> Dict[str, any]:
        """
        Detect language and translate to English if needed.
        
        Args:
            text (str): The input text to analyze
            
        Returns:
            Dict containing:
            - original_text: The original input
            - detected_language: Detected language code/name
            - confidence: Detection confidence (0.0-1.0)
            - translated_text: English translation (if needed)
            - needs_translation: Boolean indicating if translation was needed
            - context_preserved: Boolean indicating context preservation
        """
        if not text or not text.strip():
            return {
                'original_text': text,
                'detected_language': 'unknown',
                'confidence': 0.0,
                'translated_text': text,
                'needs_translation': False,
                'context_preserved': True
            }
        
        try:
            prompt = f"""You are a multilingual language detection and translation expert.
            
Analyze the following text and provide a response in this exact JSON format:

{{
  "detected_language": "language_name_or_code",
  "confidence": 0.95,
  "needs_translation": true/false,
  "translated_text": "english_translation_if_needed",
  "context_preserved": true,
  "original_intent": "brief_description_of_what_user_wants"
}}

IMPORTANT RULES:
1. Detect language accurately (Indonesian, Spanish, French, English, etc.)
2. If the text is already in English, set needs_translation to false and copy original text
3. For non-English text, provide a natural English translation that preserves:
   - Original intent and meaning
   - Time expressions (e.g., "5 menit lagi" → "in 5 minutes")
   - Task/reminder context
   - Urgency and tone
4. Handle informal language, typos, and colloquialisms
5. For time-related expressions, be especially careful:
   - "ingetin" (Indonesian) → "remind me"
   - "menit lagi" → "minutes from now"
   - "jam" → "hour" or specific time
   - "besok" → "tomorrow"
   - "hari ini" → "today"
6. Provide confidence score based on language detection certainty
7. Return ONLY the JSON object, no additional text

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
                
                # Add original text to result
                result['original_text'] = text
                
                # Validate required fields
                required_fields = ['detected_language', 'confidence', 'needs_translation', 'translated_text']
                for field in required_fields:
                    if field not in result:
                        logger.warning(f"Missing field {field} in translation response")
                        result[field] = self._get_default_value(field, text)
                
                logger.debug(f"Translation result: {result}")
                return result
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Raw response: {response_text}")
                return self._get_fallback_result(text)
                
        except Exception as e:
            logger.error(f"Error in translation: {e}")
            return self._get_fallback_result(text)
    
    def _get_default_value(self, field: str, text: str):
        """Get default values for missing fields."""
        defaults = {
            'detected_language': 'unknown',
            'confidence': 0.5,
            'needs_translation': False,
            'translated_text': text,
            'context_preserved': True,
            'original_intent': 'user request'
        }
        return defaults.get(field, None)
    
    def _get_fallback_result(self, text: str) -> Dict[str, any]:
        """Return fallback result when translation fails."""
        return {
            'original_text': text,
            'detected_language': 'unknown',
            'confidence': 0.5,
            'translated_text': text,
            'needs_translation': False,
            'context_preserved': True,
            'original_intent': 'user request'
        }
    
    def quick_detect_language(self, text: str) -> str:
        """
        Quick language detection for simple cases.
        
        Args:
            text (str): Input text
            
        Returns:
            str: Detected language code/name
        """
        if not text:
            return 'unknown'
        
        # Quick keyword-based detection for common cases
        text_lower = text.lower()
        
        # Indonesian indicators
        indonesian_keywords = ['ingetin', 'menit', 'jam', 'hari', 'besok', 'sekarang', 'lagi', 'buang', 'sampah']
        if any(keyword in text_lower for keyword in indonesian_keywords):
            return 'Indonesian'
        
        # Spanish indicators
        spanish_keywords = ['recuérdame', 'minutos', 'hora', 'mañana', 'hoy', 'después']
        if any(keyword in text_lower for keyword in spanish_keywords):
            return 'Spanish'
        
        # French indicators
        french_keywords = ['rappelle-moi', 'minutes', 'heure', 'demain', "aujourd'hui", 'dans']
        if any(keyword in text_lower for keyword in french_keywords):
            return 'French'
        
        # Default to English if no other language detected
        return 'English'

# Global instance for efficient reuse
_translation_agent_instance: Optional[TranslationAgent] = None

def get_translation_agent() -> TranslationAgent:
    """Get or create a singleton instance of the translation agent."""
    global _translation_agent_instance
    if _translation_agent_instance is None:
        _translation_agent_instance = TranslationAgent()
    return _translation_agent_instance

def translate_to_english(text: str) -> Dict[str, any]:
    """
    Translate text to English if needed, preserving context and intent.
    
    Args:
        text (str): The input text to translate
        
    Returns:
        Dict: Translation result with language detection and context info
    """
    if not text:
        return {
            'original_text': text,
            'translated_text': text,
            'needs_translation': False
        }
    
    try:
        agent = get_translation_agent()
        return agent.detect_and_translate(text)
    except Exception as e:
        logger.error(f"Translation failed, returning original text: {e}")
        return {
            'original_text': text,
            'detected_language': 'unknown',
            'confidence': 0.0,
            'translated_text': text,
            'needs_translation': False,
            'context_preserved': True
        }
