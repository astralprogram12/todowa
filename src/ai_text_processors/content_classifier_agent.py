"""
AI-Powered Content Classifier Agent

This agent intelligently classifies user content into different categories:
- Journal Entries: Personal experiences, thoughts, daily reflections, emotions
- Memories: Important events, milestones, achievements, meaningful relationships
- Temporary Info: Quick reminders, transient tasks, one-time events
- Knowledge: Facts, lessons learned, insights to remember

Uses context clues, emotional tone, and temporal significance for classification.
"""

import os
import sys
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime

# Add parent directories to Python path to access config
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, parent_dir)

try:
    import google.generativeai as genai
    import config
    from src.ai_text_processors.translation_agent import TranslationAgent
except ImportError as e:
    logging.error(f"Failed to import required modules: {e}")
    raise

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContentClassifierAgent:
    """AI-powered content classification agent using Gemini AI."""
    
    def __init__(self):
        """Initialize the content classifier agent."""
        try:
            genai.configure(api_key=config.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            self.translation_agent = TranslationAgent()
            logger.info("Content Classifier Agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Content Classifier Agent: {e}")
            raise
    
    def classify_content(self, text: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Classify user content into appropriate categories.
        
        Args:
            text (str): The content to classify
            user_context (Dict): Additional context about the user and their patterns
            
        Returns:
            Dict containing classification results and metadata
        """
        if not text or not text.strip():
            return self._get_empty_classification()
        
        try:
            # First, handle translation if needed
            translation_result = self.translation_agent.detect_and_translate(text)
            
            # Use translated text for classification but preserve original
            classification_text = translation_result.get('translated_text', text)
            
            # Build context-aware prompt
            prompt = self._build_classification_prompt(classification_text, user_context, translation_result)
            
            response = self.model.generate_content(prompt)
            result = self._parse_classification_response(response.text.strip())
            
            # Enhance result with translation info and metadata
            result.update({
                'original_text': text,
                'processed_text': classification_text,
                'detected_language': translation_result.get('detected_language', 'unknown'),
                'translation_confidence': translation_result.get('confidence', 0.0),
                'timestamp': datetime.now().isoformat(),
                'context_used': user_context is not None
            })
            
            logger.debug(f"Content classified: {result['primary_category']} (confidence: {result['confidence_scores'][result['primary_category']]})")
            return result
            
        except Exception as e:
            logger.error(f"Error in content classification: {e}")
            return self._get_error_classification(text, str(e))
    
    def _build_classification_prompt(self, text: str, user_context: Dict[str, Any], translation_result: Dict[str, Any]) -> str:
        """Build a context-aware classification prompt."""
        
        context_info = ""
        if user_context:
            # Add relevant user context
            recent_patterns = user_context.get('recent_patterns', {})
            if recent_patterns:
                context_info = f"\nUser Context:\n- Recent activity patterns: {recent_patterns}"
        
        translation_info = ""
        if translation_result.get('original_intent'):
            translation_info = f"\nOriginal Intent: {translation_result['original_intent']}"
        
        prompt = f"""You are an expert content classifier that analyzes text to determine its appropriate category and characteristics.

CLASSIFICATION CATEGORIES:
1. **JOURNAL_ENTRY**: Personal experiences, daily thoughts, emotions, reflections, feelings
   - Examples: "Today was amazing", "I feel stressed about work", "Had lunch with mom"
   
2. **MEMORY**: Important events, milestones, achievements, meaningful moments worth preserving
   - Examples: "Got promoted today!", "First time visiting Paris", "Graduated college"
   
3. **TEMPORARY_INFO**: Quick reminders, transient tasks, one-time events, temporary notes
   - Examples: "Buy milk tomorrow", "Call dentist at 3pm", "Meeting room 205"
   
4. **KNOWLEDGE**: Facts, lessons learned, insights, educational content, reference information
   - Examples: "Python uses indentation for blocks", "Recipe for pasta sauce", "Investment tips"

ANALYSIS FACTORS:
- Emotional tone (personal vs factual)
- Temporal significance (lasting vs temporary)
- Intent (preserve vs act upon vs learn from)
- Personal relevance (subjective experience vs objective information)
- Context clues from language patterns

{context_info}{translation_info}

Text to classify: "{text}"

Provide your analysis in this exact JSON format:
{{
  "primary_category": "JOURNAL_ENTRY|MEMORY|TEMPORARY_INFO|KNOWLEDGE",
  "confidence_scores": {{
    "JOURNAL_ENTRY": 0.85,
    "MEMORY": 0.10,
    "TEMPORARY_INFO": 0.03,
    "KNOWLEDGE": 0.02
  }},
  "reasoning": "Brief explanation of classification decision",
  "emotional_tone": "positive|negative|neutral|mixed",
  "temporal_significance": "immediate|short_term|long_term|permanent",
  "importance_score": 0.75,
  "suggested_tags": ["tag1", "tag2", "tag3"],
  "contains_personal_info": true,
  "actionable_items": ["specific action if any"],
  "relationships_mentioned": ["person1", "person2"],
  "locations_mentioned": ["location1"],
  "time_references": ["today", "tomorrow", "next week"]
}}

Return ONLY the JSON object:"""
        
        return prompt
    
    def _parse_classification_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the AI response into a structured classification result."""
        try:
            # Clean the response to extract JSON
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Parse JSON response
            result = json.loads(response_text)
            
            # Validate and normalize the result
            result = self._validate_classification_result(result)
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse classification JSON: {e}")
            logger.debug(f"Raw response: {response_text}")
            return self._get_fallback_classification(response_text)
        except Exception as e:
            logger.error(f"Error parsing classification response: {e}")
            return self._get_fallback_classification(response_text)
    
    def _validate_classification_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize classification result."""
        valid_categories = ["JOURNAL_ENTRY", "MEMORY", "TEMPORARY_INFO", "KNOWLEDGE"]
        valid_tones = ["positive", "negative", "neutral", "mixed"]
        valid_temporal = ["immediate", "short_term", "long_term", "permanent"]
        
        # Ensure primary category is valid
        if result.get('primary_category') not in valid_categories:
            result['primary_category'] = 'JOURNAL_ENTRY'  # Default fallback
        
        # Ensure confidence scores exist and sum to ~1.0
        if 'confidence_scores' not in result or not isinstance(result['confidence_scores'], dict):
            result['confidence_scores'] = {cat: 0.25 for cat in valid_categories}
        else:
            # Normalize confidence scores
            total = sum(result['confidence_scores'].values())
            if total > 0:
                result['confidence_scores'] = {
                    k: v / total for k, v in result['confidence_scores'].items()
                }
            else:
                result['confidence_scores'] = {cat: 0.25 for cat in valid_categories}
        
        # Validate other fields with defaults
        result['emotional_tone'] = result.get('emotional_tone', 'neutral')
        if result['emotional_tone'] not in valid_tones:
            result['emotional_tone'] = 'neutral'
            
        result['temporal_significance'] = result.get('temporal_significance', 'short_term')
        if result['temporal_significance'] not in valid_temporal:
            result['temporal_significance'] = 'short_term'
            
        result['importance_score'] = max(0.0, min(1.0, result.get('importance_score', 0.5)))
        result['reasoning'] = result.get('reasoning', 'Automated classification')
        result['suggested_tags'] = result.get('suggested_tags', [])
        result['contains_personal_info'] = result.get('contains_personal_info', True)
        result['actionable_items'] = result.get('actionable_items', [])
        result['relationships_mentioned'] = result.get('relationships_mentioned', [])
        result['locations_mentioned'] = result.get('locations_mentioned', [])
        result['time_references'] = result.get('time_references', [])
        
        return result
    
    def _get_empty_classification(self) -> Dict[str, Any]:
        """Return empty classification for empty input."""
        return {
            'primary_category': 'TEMPORARY_INFO',
            'confidence_scores': {
                'JOURNAL_ENTRY': 0.0,
                'MEMORY': 0.0,
                'TEMPORARY_INFO': 1.0,
                'KNOWLEDGE': 0.0
            },
            'reasoning': 'Empty or invalid input',
            'emotional_tone': 'neutral',
            'temporal_significance': 'immediate',
            'importance_score': 0.0,
            'suggested_tags': [],
            'contains_personal_info': False,
            'actionable_items': [],
            'relationships_mentioned': [],
            'locations_mentioned': [],
            'time_references': [],
            'original_text': '',
            'processed_text': '',
            'detected_language': 'unknown',
            'translation_confidence': 0.0,
            'timestamp': datetime.now().isoformat(),
            'context_used': False
        }
    
    def _get_fallback_classification(self, text: str) -> Dict[str, Any]:
        """Return fallback classification when parsing fails."""
        return {
            'primary_category': 'JOURNAL_ENTRY',
            'confidence_scores': {
                'JOURNAL_ENTRY': 0.7,
                'MEMORY': 0.1,
                'TEMPORARY_INFO': 0.1,
                'KNOWLEDGE': 0.1
            },
            'reasoning': 'Fallback classification due to parsing error',
            'emotional_tone': 'neutral',
            'temporal_significance': 'short_term',
            'importance_score': 0.5,
            'suggested_tags': ['unclassified'],
            'contains_personal_info': True,
            'actionable_items': [],
            'relationships_mentioned': [],
            'locations_mentioned': [],
            'time_references': [],
            'original_text': text,
            'processed_text': text,
            'detected_language': 'unknown',
            'translation_confidence': 0.0,
            'timestamp': datetime.now().isoformat(),
            'context_used': False
        }
    
    def _get_error_classification(self, text: str, error: str) -> Dict[str, Any]:
        """Return error classification when classification fails."""
        classification = self._get_fallback_classification(text)
        classification['reasoning'] = f'Classification error: {error}'
        classification['suggested_tags'] = ['error', 'unclassified']
        return classification

# Global instance for efficient reuse
_classifier_instance: Optional[ContentClassifierAgent] = None

def get_content_classifier() -> ContentClassifierAgent:
    """Get or create a singleton instance of the content classifier."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = ContentClassifierAgent()
    return _classifier_instance

def classify_user_content(text: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Classify user content using the AI-powered classifier.
    
    Args:
        text (str): The content to classify
        user_context (Dict): Additional user context for better classification
        
    Returns:
        Dict containing complete classification results
    """
    if not text:
        return get_content_classifier()._get_empty_classification()
    
    try:
        classifier = get_content_classifier()
        return classifier.classify_content(text, user_context)
    except Exception as e:
        logger.error(f"Content classification failed: {e}")
        return get_content_classifier()._get_error_classification(text, str(e))