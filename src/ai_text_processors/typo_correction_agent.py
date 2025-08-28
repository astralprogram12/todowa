"""
AI-Powered Typo Correction Agent

This module provides intelligent typo correction using Google's Gemini AI.
It handles context-aware corrections in multiple languages while preserving
original formatting and case.
"""

import os
import sys
import logging
from typing import Optional

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

class TypoCorrectionAgent:
    """AI-powered typo correction agent using Gemini AI."""
    
    def __init__(self):
        """Initialize the typo correction agent with Gemini configuration."""
        try:
            genai.configure(api_key=config.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            logger.info("Typo Correction Agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Typo Correction Agent: {e}")
            raise
    
    def correct_typos(self, text: str) -> str:
        """
        Correct spelling mistakes in the given text using AI.
        
        Args:
            text (str): The input text to correct
            
        Returns:
            str: The corrected text with typos fixed
        """
        if not text or not text.strip():
            return text
        
        try:
            prompt = f"""Please correct any spelling mistakes in the following text. 
            
IMPORTANT RULES:
1. Only correct actual spelling mistakes - do not change words that are correctly spelled
2. Preserve the exact original formatting, spacing, punctuation, and case pattern
3. Handle context-aware corrections (e.g., 'luncz at 2' should become 'lunch at 2')
4. Work with text in any language - detect the language automatically
5. Return ONLY the corrected text without any additional explanations, markup, or comments
6. If there are no spelling mistakes, return the text exactly as provided
7. Do not change proper nouns, abbreviations, or intentionally stylized text
8. Maintain the original sentence structure and meaning

Text to correct: "{text}"

Corrected text:"""

            response = self.model.generate_content(prompt)
            corrected_text = response.text.strip()
            
            logger.debug(f"Original: '{text}' -> Corrected: '{corrected_text}'")
            return corrected_text
            
        except Exception as e:
            logger.error(f"Error in typo correction: {e}")
            # Return original text if correction fails
            return text

# Global instance for efficient reuse
_typo_agent_instance: Optional[TypoCorrectionAgent] = None

def get_typo_correction_agent() -> TypoCorrectionAgent:
    """Get or create a singleton instance of the typo correction agent."""
    global _typo_agent_instance
    if _typo_agent_instance is None:
        _typo_agent_instance = TypoCorrectionAgent()
    return _typo_agent_instance

def apply_ai_typo_correction(text: str) -> str:
    """
    Apply AI-powered typo correction to user input.
    
    This function replaces the previous regex-based typo correction
    with intelligent AI-powered correction that handles multiple languages
    and context-aware corrections.
    
    Args:
        text (str): The input text to correct
        
    Returns:
        str: The corrected text
    """
    if not text:
        return text
    
    try:
        agent = get_typo_correction_agent()
        return agent.correct_typos(text)
    except Exception as e:
        logger.error(f"AI typo correction failed, returning original text: {e}")
        return text
