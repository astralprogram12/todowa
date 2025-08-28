"""
Enhanced Double-Check Agent for Error Prevention

This agent provides comprehensive validation of agent responses to catch errors
like the Indonesian time parsing issue ('ingetin 5 menit lagi buang sampah' → 'tomorrow at 9:00 AM').

Features:
- AI-powered validation of agent responses for accuracy and consistency
- Multilingual verification to detect language/context mismatches
- Time parsing validation with cross-checking
- Intent alignment verification
- Logic consistency checks
- Contextual appropriateness validation
"""

import os
import sys
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Tuple

# Add parent directories to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, parent_dir)

try:
    import google.generativeai as genai
    import config
    from ..agents.base_agent import BaseAgent
    from ...ai_text_processors.ai_time_parser import get_ai_time_parser, parse_time_with_ai
    from ...ai_text_processors.translation_agent import get_translation_agent, translate_to_english
except ImportError as e:
    logging.error(f"Failed to import required modules: {e}")
    # Fallback imports for when running standalone
    try:
        from base_agent import BaseAgent
    except:
        pass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LanguageCoherenceValidator:
    """Validator for language coherence between input and response."""
    
    def __init__(self, translator):
        self.translator = translator
    
    async def validate(self, original_input: str, response: Dict[str, Any]) -> Dict[str, Any]:
        """Validate language coherence."""
        try:
            translation_result = self.translator.detect_and_translate(original_input)
            detected_language = translation_result.get('detected_language', 'unknown')
            
            validation = {
                'is_valid': True,
                'confidence': 1.0,
                'issues': [],
                'corrections': []
            }
            
            # Check for language-specific issues
            if detected_language == 'Indonesian':
                issues = await self._check_indonesian_coherence(original_input, response)
                validation.update(issues)
            
            return validation
        except Exception as e:
            logger.error(f"Language coherence validation error: {e}")
            return {'is_valid': True, 'confidence': 0.8, 'issues': [], 'corrections': []}
    
    async def _check_indonesian_coherence(self, original_input: str, response: Dict[str, Any]) -> Dict[str, Any]:
        """Check Indonesian-specific coherence issues."""
        issues = []
        corrections = []
        
        original_lower = original_input.lower()
        response_message = response.get('message', '').lower()
        
        # Check for "ingetin" acknowledgment
        if 'ingetin' in original_lower and 'remind' not in response_message:
            issues.append("Indonesian 'ingetin' (remind me) not acknowledged")
            corrections.append({
                'type': 'language_correction',
                'suggestion': 'Acknowledge this as a reminder request',
                'reason': 'Indonesian reminder context preservation'
            })
        
        # Check for task preservation like "buang sampah"
        if 'buang sampah' in original_lower and 'buang sampah' not in response_message:
            issues.append("Indonesian task 'buang sampah' not preserved")
            corrections.append({
                'type': 'task_preservation',
                'suggestion': 'Preserve the original task description "buang sampah"',
                'reason': 'Task content should be preserved in original language'
            })
        
        return {
            'is_valid': len(issues) == 0,
            'confidence': 0.6 if issues else 1.0,
            'issues': issues,
            'corrections': corrections
        }

class TimeExpressionValidator:
    """Validator specifically for time parsing accuracy."""
    
    def __init__(self, time_parser):
        self.time_parser = time_parser
    
    async def validate(self, original_input: str, response: Dict[str, Any]) -> Dict[str, Any]:
        """Validate time expressions."""
        try:
            time_result = self.time_parser.parse_time_expression(original_input)
            
            validation = {
                'is_valid': True,
                'confidence': 1.0,
                'issues': [],
                'corrections': []
            }
            
            if time_result.get('has_time_expression', False):
                contradiction_found = self._detect_time_contradiction(
                    original_input, response.get('message', ''), time_result
                )
                
                if contradiction_found:
                    validation['is_valid'] = False
                    validation['confidence'] = 0.3
                    validation['issues'].append(
                        f"TIME MISMATCH: User said '{time_result.get('original_expression', '')}' "
                        f"but response suggests different timing"
                    )
                    
                    # Generate specific correction
                    user_friendly_time = time_result.get('user_friendly_time', 'soon')
                    task_description = time_result.get('task_description', 'task')
                    validation['corrections'].append({
                        'type': 'time_correction',
                        'suggestion': f"Got it! I'll remind you about '{task_description}' {user_friendly_time}.",
                        'reason': 'Corrected time interpretation to match user\'s original expression'
                    })
            
            return validation
        except Exception as e:
            logger.error(f"Time expression validation error: {e}")
            return {'is_valid': True, 'confidence': 0.8, 'issues': [], 'corrections': []}
    
    def _detect_time_contradiction(self, original_input: str, response_message: str, time_result: Dict[str, Any]) -> bool:
        """Detect specific time contradictions."""
        try:
            original_lower = original_input.lower()
            response_lower = response_message.lower()
            time_type = time_result.get('time_type', '')
            
            # Check for relative time vs absolute time contradictions
            if time_type == 'relative':
                # "5 menit lagi" should not become "tomorrow"
                if ('menit lagi' in original_lower or 'minutes' in original_lower):
                    if 'tomorrow' in response_lower or 'next day' in response_lower:
                        return True
                
                # "sekarang" or "now" should not become "later"
                if ('sekarang' in original_lower or 'now' in original_lower):
                    if 'tomorrow' in response_lower or 'later' in response_lower:
                        return True
            
            return False
        except Exception as e:
            logger.error(f"Time contradiction detection error: {e}")
            return False

class IntentAlignmentChecker:
    """Checker for intent alignment between input and response."""
    
    def __init__(self, ai_model):
        self.ai_model = ai_model
    
    async def validate(self, original_input: str, response: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Check intent alignment."""
        try:
            prompt = f"""Analyze if the response properly addresses the user's intent.

Original Input: "{original_input}"
Response: "{response.get('message', '')}"

Return JSON:
{{
  "intent_aligned": true/false,
  "confidence": 0.95,
  "issues": ["list of issues"],
  "missing_elements": ["missing elements"]
}}"""
            
            ai_response = self.ai_model.generate_content(prompt)
            response_text = ai_response.text.strip()
            
            if response_text.startswith('```json'):
                response_text = response_text[7:-3]
            
            import json
            result = json.loads(response_text)
            
            return {
                'is_valid': result.get('intent_aligned', True),
                'confidence': result.get('confidence', 1.0),
                'issues': result.get('issues', []),
                'corrections': [{'type': 'intent_correction', 'suggestion': f"Address: {', '.join(result.get('missing_elements', []))}", 'reason': 'Missing elements'}] if result.get('missing_elements') else []
            }
        except Exception as e:
            logger.error(f"Intent alignment validation error: {e}")
            return {'is_valid': True, 'confidence': 0.8, 'issues': [], 'corrections': []}

class FactualConsistencyMonitor:
    """Monitor for factual consistency in responses."""
    
    def __init__(self, ai_model):
        self.ai_model = ai_model
    
    async def validate(self, original_input: str, response: Dict[str, Any]) -> Dict[str, Any]:
        """Check factual consistency."""
        try:
            prompt = f"""Check for logical inconsistencies in the response.

Input: "{original_input}"
Response: "{response.get('message', '')}"

Return JSON:
{{
  "is_consistent": true/false,
  "confidence": 0.95,
  "inconsistencies": ["list of issues"],
  "severity": "low/medium/high"
}}"""
            
            ai_response = self.ai_model.generate_content(prompt)
            response_text = ai_response.text.strip()
            
            if response_text.startswith('```json'):
                response_text = response_text[7:-3]
            
            import json
            result = json.loads(response_text)
            
            return {
                'is_valid': result.get('is_consistent', True),
                'confidence': result.get('confidence', 1.0),
                'issues': result.get('inconsistencies', []),
                'corrections': [{'type': 'consistency_correction', 'suggestion': 'Fix logical inconsistencies', 'reason': f"Detected {result.get('severity', 'medium')}-severity issues"}] if not result.get('is_consistent', True) else []
            }
        except Exception as e:
            logger.error(f"Factual consistency validation error: {e}")
            return {'is_valid': True, 'confidence': 0.8, 'issues': [], 'corrections': []}

class ContextAppropriatenessFilter:
    """Filter for contextual appropriateness of responses."""
    
    def __init__(self):
        pass
    
    async def validate(self, original_input: str, response: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Check contextual appropriateness."""
        try:
            validation = {
                'is_valid': True,
                'confidence': 1.0,
                'issues': [],
                'corrections': []
            }
            
            response_message = response.get('message', '')
            
            # Check response length
            if len(response_message.strip()) < 10:
                validation['issues'].append("Response too brief")
                validation['confidence'] = 0.7
            
            # Check for reminder acknowledgment
            if 'remind' in original_input.lower() and 'remind' not in response_message.lower():
                validation['issues'].append("Reminder request not acknowledged")
                validation['confidence'] = 0.6
                validation['corrections'].append({
                    'type': 'context_correction',
                    'suggestion': 'Acknowledge the reminder request explicitly',
                    'reason': 'User requested a reminder'
                })
            
            return validation
        except Exception as e:
            logger.error(f"Context appropriateness validation error: {e}")
            return {'is_valid': True, 'confidence': 0.8, 'issues': [], 'corrections': []}

class EnhancedDoubleCheckAgent(BaseAgent):
    """Enhanced double-check validation agent for error prevention."""
    
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model, agent_name="EnhancedDoubleCheckAgent")
        self.validation_model = ai_model
        self.time_parser = None
        self.translator = None
        self.validation_cache = {}
        
        # Initialize validation framework components
        self.language_validator = None
        self.time_validator = None
        self.intent_checker = None
        self.consistency_monitor = None
        self.context_filter = None
        
    def initialize_components(self):
        """Initialize time parser, translator, and validation components."""
        try:
            self.time_parser = get_ai_time_parser()
            self.translator = get_translation_agent()
            
            # Initialize validation framework components
            self.language_validator = LanguageCoherenceValidator(self.translator)
            self.time_validator = TimeExpressionValidator(self.time_parser)
            self.intent_checker = IntentAlignmentChecker(self.validation_model)
            self.consistency_monitor = FactualConsistencyMonitor(self.validation_model)
            self.context_filter = ContextAppropriatenessFilter()
            
            logger.info("Enhanced Double-Check Agent components initialized")
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
    
    async def validate_response(self, original_input: str, agent_response: Dict[str, Any], 
                              agent_name: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Validate an agent response for accuracy, consistency, and appropriateness.
        
        Args:
            original_input (str): The original user input
            agent_response (Dict): The agent's response to validate
            agent_name (str): Name of the agent that generated the response
            context (Dict): Additional context for validation
            
        Returns:
            Dict: Validation result with corrections and suggestions
        """
        if not self.language_validator:
            self.initialize_components()
        
        validation_result = {
            'is_valid': True,
            'confidence_score': 1.0,
            'validation_issues': [],
            'correction_suggestions': [],
            'original_input': original_input,
            'original_response': agent_response,
            'validated_response': agent_response,
            'validation_timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Run all validation checks using framework components
            language_check = await self.language_validator.validate(original_input, agent_response)
            time_check = await self.time_validator.validate(original_input, agent_response)
            intent_check = await self.intent_checker.validate(original_input, agent_response, context)
            consistency_check = await self.consistency_monitor.validate(original_input, agent_response)
            context_check = await self.context_filter.validate(original_input, agent_response, context)
            
            # Aggregate validation results
            all_checks = [language_check, time_check, intent_check, consistency_check, context_check]
            
            for check in all_checks:
                if not check.get('is_valid', True):
                    validation_result['is_valid'] = False
                    validation_result['validation_issues'].extend(check.get('issues', []))
                    validation_result['correction_suggestions'].extend(check.get('corrections', []))
                
                # Adjust confidence score
                check_confidence = check.get('confidence', 1.0)
                validation_result['confidence_score'] = min(validation_result['confidence_score'], check_confidence)
            
            # Generate corrected response if issues found
            if not validation_result['is_valid']:
                corrected_response = await self._generate_corrected_response(
                    original_input, agent_response, validation_result['correction_suggestions']
                )
                validation_result['validated_response'] = corrected_response
            
            # Log validation results
            self._log_validation_result(original_input, agent_name, validation_result)
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error in response validation: {e}")
            validation_result.update({
                'is_valid': False,
                'confidence_score': 0.0,
                'validation_issues': [f"Validation error: {str(e)}"],
                'correction_suggestions': ['Please try again with clearer input']
            })
            return validation_result
    
    async def _validate_language_coherence(self, original_input: str, response: Dict[str, Any]) -> Dict[str, Any]:
        """Validate language coherence between input and response."""
        try:
            # Translate original input to detect language and get context
            translation_result = self.translator.detect_and_translate(original_input)
            
            detected_language = translation_result.get('detected_language', 'unknown')
            needs_translation = translation_result.get('needs_translation', False)
            
            validation = {
                'is_valid': True,
                'confidence': 1.0,
                'issues': [],
                'corrections': []
            }
            
            # Check if non-English input was properly understood
            if needs_translation and detected_language != 'English':
                # Validate that the response context makes sense for the original language
                response_message = response.get('message', '')
                
                # Specific check for Indonesian time expressions
                if detected_language == 'Indonesian':
                    indonesian_issues = await self._check_indonesian_context(original_input, response_message)
                    validation['issues'].extend(indonesian_issues.get('issues', []))
                    validation['corrections'].extend(indonesian_issues.get('corrections', []))
                    if indonesian_issues.get('issues'):
                        validation['is_valid'] = False
                        validation['confidence'] = 0.6
            
            return validation
            
        except Exception as e:
            logger.error(f"Language coherence validation error: {e}")
            return {'is_valid': True, 'confidence': 0.8, 'issues': [], 'corrections': []}
    
    async def _validate_time_expressions(self, original_input: str, response: Dict[str, Any]) -> Dict[str, Any]:
        """Validate time expressions for accuracy across languages."""
        try:
            # Parse time from original input
            time_parsing_result = self.time_parser.parse_time_expression(original_input)
            
            validation = {
                'is_valid': True,
                'confidence': 1.0,
                'issues': [],
                'corrections': []
            }
            
            if time_parsing_result.get('has_time_expression', False):
                # Check for specific time parsing issues
                original_expression = time_parsing_result.get('original_expression', '')
                parsed_time_type = time_parsing_result.get('time_type', '')
                response_message = response.get('message', '')
                
                # Check for the Indonesian "5 minutes" vs "tomorrow" issue
                if self._detect_time_contradiction(original_input, response_message, time_parsing_result):
                    validation['is_valid'] = False
                    validation['confidence'] = 0.3
                    validation['issues'].append(
                        f"TIME MISMATCH: User said '{original_expression}' but response suggests different timing"
                    )
                    
                    # Generate correction based on parsed time
                    if parsed_time_type == 'relative':
                        user_friendly_time = time_parsing_result.get('user_friendly_time', 'soon')
                        task_description = time_parsing_result.get('task_description', 'task')
                        validation['corrections'].append({
                            'type': 'time_correction',
                            'suggestion': f"Got it! I'll remind you about '{task_description}' {user_friendly_time}.",
                            'reason': 'Corrected time interpretation to match user\'s original expression'
                        })
            
            return validation
            
        except Exception as e:
            logger.error(f"Time expression validation error: {e}")
            return {'is_valid': True, 'confidence': 0.8, 'issues': [], 'corrections': []}
    
    async def _validate_intent_alignment(self, original_input: str, response: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Validate that response aligns with user intent."""
        try:
            # Use AI to analyze intent alignment
            prompt = f"""Analyze if the agent response properly addresses the user's original intent.

Original User Input: "{original_input}"
Agent Response: "{response.get('message', '')}"

Check for:
1. Does the response address what the user actually requested?
2. Is the task/reminder content preserved correctly?
3. Are there any missing elements from the user's request?

Return JSON format:
{{
  "intent_aligned": true/false,
  "confidence": 0.95,
  "issues": ["list of alignment issues"],
  "missing_elements": ["elements not addressed"],
  "preserved_elements": ["elements correctly preserved"]
}}
"""
            
            ai_response = self.validation_model.generate_content(prompt)
            response_text = ai_response.text.strip()
            
            # Clean and parse JSON
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            import json
            result = json.loads(response_text)
            
            validation = {
                'is_valid': result.get('intent_aligned', True),
                'confidence': result.get('confidence', 1.0),
                'issues': result.get('issues', []),
                'corrections': []
            }
            
            # Generate corrections for missing elements
            missing_elements = result.get('missing_elements', [])
            if missing_elements:
                validation['corrections'].append({
                    'type': 'intent_correction',
                    'suggestion': f"Please ensure to address: {', '.join(missing_elements)}",
                    'reason': 'Missing elements from user request'
                })
            
            return validation
            
        except Exception as e:
            logger.error(f"Intent alignment validation error: {e}")
            return {'is_valid': True, 'confidence': 0.8, 'issues': [], 'corrections': []}
    
    async def _validate_factual_consistency(self, original_input: str, response: Dict[str, Any]) -> Dict[str, Any]:
        """Check for logical inconsistencies and contradictions."""
        try:
            # Use AI to check for logical consistency
            prompt = f"""Analyze the response for logical inconsistencies, contradictions, or impossible scenarios.

Original Input: "{original_input}"
Response: "{response.get('message', '')}"

Check for:
1. Internal contradictions in the response
2. Impossible or illogical scenarios
3. Factual inconsistencies
4. Time-related impossibilities

Return JSON:
{{
  "is_consistent": true/false,
  "confidence": 0.95,
  "inconsistencies": ["list of logical issues"],
  "severity": "low/medium/high"
}}
"""
            
            ai_response = self.validation_model.generate_content(prompt)
            response_text = ai_response.text.strip()
            
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            import json
            result = json.loads(response_text)
            
            inconsistencies = result.get('inconsistencies', [])
            severity = result.get('severity', 'low')
            
            validation = {
                'is_valid': result.get('is_consistent', True),
                'confidence': result.get('confidence', 1.0),
                'issues': inconsistencies,
                'corrections': []
            }
            
            if not result.get('is_consistent', True) and severity in ['medium', 'high']:
                validation['corrections'].append({
                    'type': 'consistency_correction',
                    'suggestion': 'Response contains logical inconsistencies that need correction',
                    'reason': f"Detected {severity}-severity logical issues"
                })
            
            return validation
            
        except Exception as e:
            logger.error(f"Factual consistency validation error: {e}")
            return {'is_valid': True, 'confidence': 0.8, 'issues': [], 'corrections': []}
    
    async def _validate_contextual_appropriateness(self, original_input: str, response: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Validate contextual appropriateness of the response."""
        try:
            validation = {
                'is_valid': True,
                'confidence': 1.0,
                'issues': [],
                'corrections': []
            }
            
            # Check response length and complexity
            response_message = response.get('message', '')
            if len(response_message) < 10:
                validation['issues'].append("Response too brief for the request")
                validation['confidence'] = 0.7
            
            # Check for generic responses to specific requests
            if 'remind' in original_input.lower() and 'remind' not in response_message.lower():
                validation['issues'].append("Response doesn't acknowledge reminder request")
                validation['confidence'] = 0.6
            
            return validation
            
        except Exception as e:
            logger.error(f"Contextual appropriateness validation error: {e}")
            return {'is_valid': True, 'confidence': 0.8, 'issues': [], 'corrections': []}
    
    async def _check_indonesian_context(self, original_input: str, response_message: str) -> Dict[str, Any]:
        """Specific validation for Indonesian language contexts."""
        issues = []
        corrections = []
        
        # Check for common Indonesian time expression misunderstandings
        original_lower = original_input.lower()
        response_lower = response_message.lower()
        
        # "menit lagi" should not become "tomorrow"
        if 'menit lagi' in original_lower and ('tomorrow' in response_lower or 'besok' in response_lower):
            issues.append("Indonesian 'menit lagi' (minutes from now) misinterpreted as tomorrow")
            corrections.append({
                'type': 'language_correction',
                'suggestion': 'Interpret "menit lagi" as minutes from now, not tomorrow',
                'reason': 'Indonesian time expression correction'
            })
        
        # "ingetin" should be preserved as reminder context
        if 'ingetin' in original_lower and 'remind' not in response_lower:
            issues.append("Indonesian 'ingetin' (remind me) context not preserved")
            corrections.append({
                'type': 'language_correction',
                'suggestion': 'Acknowledge this as a reminder request',
                'reason': 'Indonesian reminder context preservation'
            })
        
        return {'issues': issues, 'corrections': corrections}
    
    def _detect_time_contradiction(self, original_input: str, response_message: str, time_result: Dict[str, Any]) -> bool:
        """Detect contradictions between original time expression and response timing."""
        try:
            original_lower = original_input.lower()
            response_lower = response_message.lower()
            time_type = time_result.get('time_type', '')
            
            # Check for relative time vs absolute time contradictions
            if time_type == 'relative':
                # If user said "minutes from now" but response says "tomorrow"
                if ('menit lagi' in original_lower or 'in' in original_lower and ('minute' in original_lower or 'hour' in original_lower)):
                    if 'tomorrow' in response_lower or 'next day' in response_lower:
                        return True
                
                # If user said "now" or "soon" but response suggests much later
                if ('sekarang' in original_lower or 'now' in original_lower):
                    if 'tomorrow' in response_lower or 'later' in response_lower:
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Time contradiction detection error: {e}")
            return False
    
    async def _generate_corrected_response(self, original_input: str, original_response: Dict[str, Any], corrections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a corrected response based on validation issues."""
        try:
            # Create a prompt to generate corrected response
            correction_notes = "\n".join([f"- {corr.get('suggestion', '')}: {corr.get('reason', '')}" for corr in corrections])
            
            prompt = f"""Generate a corrected response based on the validation issues found.

Original User Input: "{original_input}"
Original Agent Response: "{original_response.get('message', '')}"

Validation Issues and Corrections Needed:
{correction_notes}

Generate a corrected response that:
1. Properly addresses the user's original intent
2. Fixes any time parsing errors
3. Preserves the task/reminder context
4. Uses appropriate language understanding
5. Is contextually appropriate

Return only the corrected message text:"""
            
            ai_response = self.validation_model.generate_content(prompt)
            corrected_message = ai_response.text.strip()
            
            # Clean the response
            corrected_message = self._clean_response(corrected_message)
            
            # Create corrected response dict
            corrected_response = original_response.copy()
            corrected_response['message'] = corrected_message
            corrected_response['validation_corrected'] = True
            corrected_response['correction_timestamp'] = datetime.now(timezone.utc).isoformat()
            
            return corrected_response
            
        except Exception as e:
            logger.error(f"Error generating corrected response: {e}")
            return original_response
    
    def _log_validation_result(self, original_input: str, agent_name: str, validation_result: Dict[str, Any]):
        """Log validation results for monitoring and improvement."""
        try:
            if not validation_result.get('is_valid', True):
                logger.warning(f"Validation failed for {agent_name}")
                logger.warning(f"Input: {original_input}")
                logger.warning(f"Issues: {validation_result.get('validation_issues', [])}")
                logger.warning(f"Confidence: {validation_result.get('confidence_score', 0.0)}")
            else:
                logger.info(f"Validation passed for {agent_name} (confidence: {validation_result.get('confidence_score', 1.0)})")
                
        except Exception as e:
            logger.error(f"Error logging validation result: {e}")
    
    async def process(self, user_input: str, context: Dict[str, Any], routing_info=None):
        """Process method for compatibility with base agent interface."""
        return {
            "message": "Enhanced Double-Check Agent is ready for response validation.",
            "status": "ready"
        }

# Global instance for efficient reuse
_double_check_agent_instance: Optional[EnhancedDoubleCheckAgent] = None

def get_enhanced_double_check_agent(supabase=None, ai_model=None) -> EnhancedDoubleCheckAgent:
    """Get or create a singleton instance of the enhanced double-check agent."""
    global _double_check_agent_instance
    if _double_check_agent_instance is None and supabase is not None and ai_model is not None:
        _double_check_agent_instance = EnhancedDoubleCheckAgent(supabase, ai_model)
    return _double_check_agent_instance

async def validate_agent_response(original_input: str, agent_response: Dict[str, Any], 
                                agent_name: str, context: Dict[str, Any] = None,
                                supabase=None, ai_model=None) -> Dict[str, Any]:
    """
    Validate an agent response using the Enhanced Double-Check Agent.
    
    Args:
        original_input (str): The original user input
        agent_response (Dict): The agent's response to validate
        agent_name (str): Name of the agent that generated the response
        context (Dict): Additional context for validation
        supabase: Supabase client (if not using global instance)
        ai_model: AI model (if not using global instance)
        
    Returns:
        Dict: Validation result with corrections and suggestions
    """
    try:
        validator = get_enhanced_double_check_agent(supabase, ai_model)
        if validator is None:
            # Create temporary instance if global not available
            if supabase and ai_model:
                validator = EnhancedDoubleCheckAgent(supabase, ai_model)
            else:
                raise Exception("Enhanced Double-Check Agent not initialized and no parameters provided")
        
        return await validator.validate_response(original_input, agent_response, agent_name, context)
    except Exception as e:
        logger.error(f"Enhanced validation failed, returning original response: {e}")
        return {
            'is_valid': True,  # Default to valid to avoid blocking
            'confidence_score': 0.5,
            'validation_issues': [f"Validation system error: {str(e)}"],
            'correction_suggestions': [],
            'validated_response': agent_response
        }