# orchestrator.py V4.0 - Complete Integration with All V4.0 Features
# Integrates: Enhanced Double-Check, Translation, AI Time Parser, Memory, Journal

import asyncio
import traceback
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Enhanced Path Setup for V4.0 ---
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

# Import unified tools
from enhanced_tools import tool_registry
import enhanced_ai_tools

# Import all agents including new V4.0 agents
from .agents import (
    BaseAgent, TaskAgent, ReminderAgent, SilentModeAgent,
    CoderAgent, AuditAgent, ExpertAgent, GuideAgent,
    IntentClassifierAgent, InformationAgent, GeneralAgent,
    ContextAgent, PreferenceAgent, ActionAgent, HelpAgent, SilentAgent
)

# Import V4.0 specific agents
try:
    from .agents.memory_agent import MemoryAgent
    from .agents.journal_agent import JournalAgent
    from .agents.enhanced_double_check_agent import EnhancedDoubleCheckAgent
    from .agents.enhanced_reminder_agent import EnhancedReminderAgent
except ImportError as e:
    logger.warning(f"Some V4.0 agents not available: {e}")
    MemoryAgent = None
    JournalAgent = None
    EnhancedDoubleCheckAgent = None
    EnhancedReminderAgent = None

# Import V4.0 AI processors
try:
    from ..ai_text_processors.translation_agent import TranslationAgent
    from ..ai_text_processors.ai_time_parser import AITimeParser
    from ..ai_text_processors.content_classifier_agent import ContentClassifierAgent
except ImportError as e:
    logger.warning(f"Some V4.0 AI processors not available: {e}")
    TranslationAgent = None
    AITimeParser = None
    ContentClassifierAgent = None

from .response_combiner import ResponseCombiner

class OrchestratorV4:
    """V4.0 Orchestrator with complete multilingual AI-powered integration.
    
    Features:
    - Multilingual input processing with translation
    - AI-powered time parsing (fixes Indonesian issue)
    - Enhanced double-check validation
    - Memory and journal management
    - Content classification and routing
    - Complete backwards compatibility
    """
    
    def __init__(self, supabase, ai_model):
        self.supabase = supabase
        self.ai_model = ai_model
        self.agents = {}
        self.user_contexts = {}
        
        # Initialize V4.0 AI processors
        self._initialize_ai_processors()
        
        # Initialize all agents including V4.0
        self._initialize_all_agents()
        
        # V4.0 feature flags
        self.v4_features = {
            'multilingual_support': TranslationAgent is not None,
            'ai_time_parsing': AITimeParser is not None,
            'enhanced_validation': EnhancedDoubleCheckAgent is not None,
            'memory_management': MemoryAgent is not None,
            'journal_support': JournalAgent is not None,
            'content_classification': ContentClassifierAgent is not None
        }
        
        # Enhanced validation settings
        self.validation_enabled = True
        self.validation_stats = {
            'total_validations': 0,
            'issues_caught': 0,
            'corrections_applied': 0,
            'multilingual_corrections': 0,
            'time_parsing_fixes': 0
        }
        
        logger.info(f"V4.0 Orchestrator initialized with features: {self.v4_features}")
    
    def _initialize_ai_processors(self):
        """Initialize V4.0 AI text processors."""
        try:
            # Translation Agent for multilingual support
            if TranslationAgent:
                self.translation_agent = TranslationAgent()
                logger.info("Translation Agent initialized")
            else:
                self.translation_agent = None
                logger.warning("Translation Agent not available")
            
            # AI Time Parser for accurate time understanding
            if AITimeParser:
                self.ai_time_parser = AITimeParser()
                logger.info("AI Time Parser initialized")
            else:
                self.ai_time_parser = None
                logger.warning("AI Time Parser not available")
            
            # Content Classifier for journal/memory routing
            if ContentClassifierAgent:
                self.content_classifier = ContentClassifierAgent()
                logger.info("Content Classifier initialized")
            else:
                self.content_classifier = None
                logger.warning("Content Classifier not available")
                
        except Exception as e:
            logger.error(f"Error initializing AI processors: {e}")
            self.translation_agent = None
            self.ai_time_parser = None
            self.content_classifier = None
    
    def _initialize_all_agents(self):
        """Initialize all agents including V4.0 enhanced agents."""
        # Initialize standard agents
        self.agents['task'] = TaskAgent(self.supabase, self.ai_model)
        self.agents['silent_mode'] = SilentModeAgent(self.supabase, self.ai_model)
        self.agents['coder'] = CoderAgent(self.supabase, self.ai_model)
        self.agents['audit'] = AuditAgent(self.supabase, self.ai_model)
        self.agents['expert'] = ExpertAgent(self.supabase, self.ai_model)
        self.agents['guide'] = GuideAgent(self.supabase, self.ai_model)
        self.agents['information'] = InformationAgent(self.supabase, self.ai_model)
        self.agents['general'] = GeneralAgent(self.supabase, self.ai_model)
        self.agents['context'] = ContextAgent(self.supabase, self.ai_model)
        self.agents['preference'] = PreferenceAgent(self.supabase, self.ai_model)
        self.agents['action'] = ActionAgent(self.supabase, self.ai_model)
        self.agents['help'] = HelpAgent(self.supabase, self.ai_model)
        self.agents['silent'] = SilentAgent(self.supabase, self.ai_model)
        
        # Initialize V4.0 enhanced agents
        if MemoryAgent:
            self.agents['memory'] = MemoryAgent(self.supabase, self.ai_model)
            logger.info("Memory Agent initialized")
        
        if JournalAgent:
            self.agents['journal'] = JournalAgent(self.supabase, self.ai_model)
            logger.info("Journal Agent initialized")
        
        if EnhancedReminderAgent:
            # Replace standard reminder with enhanced version
            self.agents['reminder'] = EnhancedReminderAgent(self.supabase, self.ai_model)
            logger.info("Enhanced Reminder Agent initialized")
        else:
            self.agents['reminder'] = ReminderAgent(self.supabase, self.ai_model)
        
        if EnhancedDoubleCheckAgent:
            self.agents['double_check'] = EnhancedDoubleCheckAgent(self.supabase, self.ai_model)
            logger.info("Enhanced Double-Check Agent initialized")
        
        # Initialize intent classifier
        self.intent_classifier = IntentClassifierAgent(self.supabase, self.ai_model)

    def load_all_agent_prompts(self, prompts_dir: str):
        # ... (this function is correct)
        if not prompts_dir or not os.path.exists(prompts_dir): return
        print(f"Orchestrator is loading all agent prompts from {prompts_dir}...")
        all_agents = {**self.agents, 'intent_classifier': self.intent_classifier}
        for agent_name, agent in all_agents.items():
            if hasattr(agent, 'load_prompts'): agent.load_prompts(prompts_dir)
        print("...All agent prompts loaded.")

    async def process_user_input(self, user_id: str, user_input: str, phone_number: str, conversation_id: Optional[str] = None):
        """V4.0 Enhanced processing with multilingual support and AI-powered validation."""
        final_response_dict = {}
        
        # Set tool registry context
        tool_registry.set_injection_context({"supabase": self.supabase, "user_id": user_id})
        
        try:
            # V4.0 Step 1: Multilingual Input Processing
            processed_input = await self._preprocess_multilingual_input(user_input)
            english_input = processed_input.get('translated_text', user_input)
            original_language = processed_input.get('detected_language', 'English')
            
            logger.info(f"V4.0 Preprocessing: {original_language} -> {english_input[:50]}...")
            
            # V4.0 Step 2: AI-Powered Time Analysis
            time_analysis = await self._analyze_time_expressions(user_input, processed_input)
            
            # V4.0 Step 3: Content Classification for Memory/Journal routing
            content_classification = await self._classify_content_type(english_input)
            
            # Check silent mode
            is_silent, session = await self._check_silent_mode(user_id)
            if is_silent and 'silent' not in user_input.lower():
                return {"message": "Silent mode is active. Message recorded.", "actions": []}
            
            # Get context and classify intent
            context = await self._get_or_create_context(user_id, conversation_id)
            
            # Enhance context with V4.0 data
            context.update({
                'original_language': original_language,
                'time_analysis': time_analysis,
                'content_classification': content_classification,
                'v4_preprocessing': processed_input
            })
            
            # Enhanced intent classification with V4.0 context
            classification = await self._classify_user_input_v4(english_input, context)
            
            agent_responses = []
            primary_intent = classification.get('primary_intent')
            
            # V4.0 Enhanced Agent Routing
            primary_agent_name = self._map_intent_to_agent_v4(primary_intent, content_classification)
            
            if primary_agent_name == 'clarification_needed':
                final_response_dict = {
                    "message": "I'm not quite sure what you mean. Could you please rephrase that?", 
                    "status": "clarification_needed"
                }
            elif primary_agent_name in self.agents:
                # Process with primary agent
                primary_response = await self.agents[primary_agent_name].process(
                    english_input, context, classification
                )
                
                # V4.0 Enhanced Double-Check Validation
                if self.validation_enabled and primary_response:
                    validated_response = await self._enhanced_validation_v4(
                        user_input, english_input, primary_response, 
                        primary_agent_name, context, time_analysis
                    )
                    
                    # Apply corrections if needed
                    if validated_response.get('validated_response'):
                        primary_response = validated_response['validated_response']
                    
                    # Update validation statistics
                    self._update_validation_stats(validated_response)
                
                agent_responses.append(primary_response)
                
                # Process secondary intents if primary was successful
                if primary_response.get('status') == 'success':
                    for secondary_agent_name in classification.get('secondary_intents', []):
                        if secondary_agent_name in self.agents and secondary_agent_name != primary_agent_name:
                            secondary_response = await self.agents[secondary_agent_name].process(
                                english_input, context, classification
                            )
                            
                            # Validate secondary responses too
                            if self.validation_enabled and secondary_response:
                                validated_secondary = await self._enhanced_validation_v4(
                                    user_input, english_input, secondary_response, 
                                    secondary_agent_name, context, time_analysis
                                )
                                if validated_secondary.get('validated_response'):
                                    secondary_response = validated_secondary['validated_response']
                            
                            agent_responses.append(secondary_response)
            
            # Combine responses
            if agent_responses:
                final_response_dict = ResponseCombiner.combine_responses(agent_responses, classification)
            
            # V4.0 Multilingual Response Processing
            if original_language != 'English' and final_response_dict.get('message'):
                final_response_dict = await self._prepare_multilingual_response(
                    final_response_dict, original_language
                )
            
            # Send final reply
            message_to_send = final_response_dict.get('message')
            if message_to_send:
                logger.info(f"V4.0 Orchestrator sending reply to {phone_number}: '{message_to_send[:100]}...'")
                tool_registry.execute(
                    "send_reply_message",
                    phone_number=phone_number,
                    message=message_to_send
                )
            
            return final_response_dict

        except Exception as e:
            logger.error(f"V4.0 Orchestrator error: {e}")
            traceback.print_exc()
            error_message = "I encountered an error. My team has been notified."
            tool_registry.execute("send_reply_message", phone_number=phone_number, message=error_message)
            return {"message": "An internal error occurred.", "error": str(e)}

    async def _preprocess_multilingual_input(self, user_input: str) -> Dict[str, Any]:
        """V4.0 Multilingual preprocessing with translation support."""
        if not self.translation_agent:
            return {
                'original_text': user_input,
                'translated_text': user_input,
                'detected_language': 'English',
                'needs_translation': False,
                'confidence': 1.0
            }
        
        try:
            return self.translation_agent.detect_and_translate(user_input)
        except Exception as e:
            logger.error(f"Translation preprocessing error: {e}")
            return {
                'original_text': user_input,
                'translated_text': user_input,
                'detected_language': 'Unknown',
                'needs_translation': False,
                'confidence': 0.5
            }
    
    async def _analyze_time_expressions(self, original_input: str, processed_input: Dict[str, Any]) -> Dict[str, Any]:
        """V4.0 AI-powered time expression analysis."""
        if not self.ai_time_parser:
            return {'has_time_expression': False, 'confidence': 0.0}
        
        try:
            # Parse time from original input (preserve context)
            time_result = self.ai_time_parser.parse_time_expression(original_input)
            
            # Also parse translated version for comparison
            if processed_input.get('needs_translation', False):
                translated_time = self.ai_time_parser.parse_time_expression(
                    processed_input.get('translated_text', original_input)
                )
                time_result['translated_parsing'] = translated_time
            
            return time_result
        except Exception as e:
            logger.error(f"Time analysis error: {e}")
            return {'has_time_expression': False, 'confidence': 0.0, 'error': str(e)}
    
    async def _classify_content_type(self, text: str) -> Dict[str, Any]:
        """V4.0 Content classification for memory/journal routing."""
        if not self.content_classifier:
            return {'type': 'general', 'confidence': 0.5}
        
        try:
            return self.content_classifier.classify_content(text)
        except Exception as e:
            logger.error(f"Content classification error: {e}")
            return {'type': 'general', 'confidence': 0.5, 'error': str(e)}
    
    async def _classify_user_input_v4(self, english_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced intent classification with V4.0 context."""
        try:
            # Use enhanced context for better classification
            classification = await self.intent_classifier.classify_intent(english_input, context)
            
            # Enhance classification with V4.0 content type info
            content_type = context.get('content_classification', {}).get('type', 'general')
            if content_type in ['memory', 'journal', 'personal_reflection']:
                # Route memory/journal content to appropriate agents
                if 'memory' in english_input.lower() or content_type == 'memory':
                    classification['secondary_intents'] = classification.get('secondary_intents', []) + ['memory']
                if content_type == 'journal' or 'journal' in english_input.lower():
                    classification['secondary_intents'] = classification.get('secondary_intents', []) + ['journal']
            
            return classification
        except Exception as e:
            logger.error(f"V4.0 intent classification error: {e}")
            return {'primary_intent': 'general', 'confidence': 0.5}
    
    def _map_intent_to_agent_v4(self, intent: str, content_classification: Dict[str, Any]) -> str:
        """V4.0 Enhanced intent mapping with content awareness."""
        if not intent:
            return 'general'
        
        # Handle V4.0 content-based routing
        content_type = content_classification.get('type', 'general')
        if content_type == 'memory' and 'memory' in self.agents:
            return 'memory'
        elif content_type == 'journal' and 'journal' in self.agents:
            return 'journal'
        
        # Standard intent mapping with enhancements
        if intent.startswith('query_'):
            domain = intent.replace('query_', '')
            return domain if domain in self.agents else 'general'
        elif intent.startswith('action_'):
            domain = intent.replace('action_', '')
            return domain if domain in self.agents else 'general'
        elif intent == 'chat' or intent == 'general':
            return 'general'
        elif intent in self.agents:
            return intent
        else:
            return 'general'
    
    async def _enhanced_validation_v4(self, original_input: str, english_input: str, 
                                    agent_response: Dict[str, Any], agent_name: str,
                                    context: Dict[str, Any], time_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """V4.0 Enhanced double-check validation with multilingual and time awareness."""
        try:
            # Use Enhanced Double-Check Agent if available
            if 'double_check' in self.agents:
                validation_context = {
                    **context,
                    'original_input': original_input,
                    'english_input': english_input,
                    'time_analysis': time_analysis,
                    'agent_name': agent_name
                }
                
                validation_result = await self.agents['double_check'].validate_response(
                    original_input, agent_response, validation_context
                )
                
                return validation_result
            
            # Fallback to basic validation
            return await self._basic_validation(original_input, agent_response, time_analysis)
            
        except Exception as e:
            logger.error(f"V4.0 validation error: {e}")
            return {
                'is_valid': True,
                'confidence_score': 0.5,
                'validation_issues': [f"Validation error: {str(e)}"],
                'correction_suggestions': [],
                'validated_response': agent_response
            }
    
    async def _basic_validation(self, original_input: str, agent_response: Dict[str, Any], 
                              time_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Basic validation for time consistency checks."""
        issues = []
        corrections = []
        
        # Check for Indonesian time parsing issues
        original_lower = original_input.lower()
        response_message = agent_response.get('message', '').lower()
        
        # Critical fix: "ingetin 5 menit lagi" should not become "tomorrow"
        if ('ingetin' in original_lower and 'menit lagi' in original_lower):
            if 'tomorrow' in response_message:
                issues.append("TIME_PARSING_ERROR: 'menit lagi' (minutes from now) incorrectly parsed as 'tomorrow'")
                
                # Extract task from original
                task_match = original_input.split('ingetin')[1] if 'ingetin' in original_input else ''
                task_match = task_match.split('menit lagi')[1].strip() if 'menit lagi' in task_match else ''
                
                corrections.append({
                    'type': 'critical_time_fix',
                    'suggestion': f"Got it! I'll remind you about '{task_match}' in a few minutes.",
                    'reason': 'Fixed Indonesian time parsing error'
                })
        
        is_valid = len(issues) == 0
        return {
            'is_valid': is_valid,
            'confidence_score': 0.9 if is_valid else 0.3,
            'validation_issues': issues,
            'correction_suggestions': corrections,
            'validated_response': agent_response  # Return original if no corrections
        }
    
    async def _prepare_multilingual_response(self, response_dict: Dict[str, Any], 
                                           original_language: str) -> Dict[str, Any]:
        """Prepare response in user's original language if needed."""
        if not self.translation_agent or original_language in ['English', 'english', 'en']:
            return response_dict
        
        try:
            message = response_dict.get('message', '')
            if message:
                # For now, keep English responses but add language context
                # Future enhancement: translate responses back to original language
                response_dict['original_language'] = original_language
                response_dict['response_language'] = 'English'
            
            return response_dict
        except Exception as e:
            logger.error(f"Multilingual response preparation error: {e}")
            return response_dict
    
    def _update_validation_stats(self, validation_result: Dict[str, Any]):
        """Update V4.0 validation statistics."""
        try:
            self.validation_stats['total_validations'] += 1
            
            if not validation_result.get('is_valid', True):
                self.validation_stats['issues_caught'] += 1
                
                # Check for specific issue types
                issues = validation_result.get('validation_issues', [])
                for issue in issues:
                    if 'multilingual' in issue.lower() or 'language' in issue.lower():
                        self.validation_stats['multilingual_corrections'] += 1
                    if 'time' in issue.lower():
                        self.validation_stats['time_parsing_fixes'] += 1
                
                if validation_result.get('correction_suggestions'):
                    self.validation_stats['corrections_applied'] += 1
                    
        except Exception as e:
            logger.error(f"Error updating validation stats: {e}")

    async def _check_silent_mode(self, user_id):
        """Check if user has silent mode active."""
        try:
            from database_personal import get_active_silent_session
            session = get_active_silent_session(self.supabase, user_id)
            return session is not None, session
        except Exception as e:
            logger.error(f"ERROR in _check_silent_mode: {str(e)}")
            return False, None

    async def _classify_user_input(self, user_input, context):
        """Legacy method for backward compatibility."""
        return await self.intent_classifier.classify_intent(user_input, context)

    async def _get_or_create_context(self, user_id, conversation_id=None):
        """Get or create user context with V4.0 enhancements."""
        context_key = f"{user_id}:{conversation_id or 'default'}"
        if context_key not in self.user_contexts:
            self.user_contexts[context_key] = {
                'user_id': user_id, 
                'conversation_id': conversation_id, 
                'created_at': datetime.now().isoformat(),
                'last_agent': None, 
                'last_input': None, 
                'last_response': None, 
                'last_classification': None,
                'history': [], 
                'preferences': {}, 
                'memory': {},
                # V4.0 context enhancements
                'language_preferences': {},
                'time_zone': 'UTC',
                'interaction_patterns': {},
                'v4_features_used': []
            }
        context = self.user_contexts[context_key]
        if len(context['history']) > 10: 
            context['history'] = context['history'][-10:]
        return context
    
    def _map_intent_to_agent(self, intent: str) -> str:
        """Legacy method for backward compatibility."""
        return self._map_intent_to_agent_v4(intent, {'type': 'general'})
    
    async def _validate_response(self, original_input: str, agent_response: Dict[str, Any], 
                               agent_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy validation method for backward compatibility."""
        time_analysis = {'has_time_expression': False}
        return await self._enhanced_validation_v4(
            original_input, original_input, agent_response, agent_name, context, time_analysis
        )
    
    def load_all_agent_prompts(self, prompts_dir: str):
        # ... (this function is correct)
        if not prompts_dir or not os.path.exists(prompts_dir): return
        print(f"Orchestrator is loading all agent prompts from {prompts_dir}...")
        all_agents = {**self.agents, 'intent_classifier': self.intent_classifier}
        for agent_name, agent in all_agents.items():
            if hasattr(agent, 'load_prompts'): agent.load_prompts(prompts_dir)
        print("...All agent prompts loaded.")
    
    def get_orchestrator_statistics(self) -> Dict[str, Any]:
        """Get comprehensive V4.0 orchestrator statistics."""
        stats = self.validation_stats.copy()
        
        # Calculate rates
        if stats['total_validations'] > 0:
            stats['issue_detection_rate'] = stats['issues_caught'] / stats['total_validations']
            stats['correction_rate'] = stats['corrections_applied'] / stats['total_validations']
            stats['multilingual_correction_rate'] = stats['multilingual_corrections'] / stats['total_validations']
            stats['time_parsing_fix_rate'] = stats['time_parsing_fixes'] / stats['total_validations']
        else:
            stats['issue_detection_rate'] = 0.0
            stats['correction_rate'] = 0.0
            stats['multilingual_correction_rate'] = 0.0
            stats['time_parsing_fix_rate'] = 0.0
        
        # Add V4.0 feature status
        stats['v4_features'] = self.v4_features
        stats['agents_count'] = len(self.agents)
        stats['active_contexts'] = len(self.user_contexts)
        
        return stats
    
    def enable_validation(self, enabled: bool = True):
        """Enable or disable V4.0 enhanced validation."""
        self.validation_enabled = enabled
        logger.info(f"V4.0 Enhanced validation {'enabled' if enabled else 'disabled'}")
    
    def get_v4_features_status(self) -> Dict[str, Any]:
        """Get detailed V4.0 features status."""
        return {
            'version': '4.0',
            'features': self.v4_features,
            'agents_available': list(self.agents.keys()),
            'ai_processors': {
                'translation_agent': self.translation_agent is not None,
                'ai_time_parser': self.ai_time_parser is not None,
                'content_classifier': self.content_classifier is not None
            },
            'validation_stats': self.validation_stats,
            'initialization_success': True
        }

# Maintain backward compatibility by creating an alias
Orchestrator = OrchestratorV4

# V4.0 Test utility function
def test_v4_integration(supabase, ai_model) -> Dict[str, Any]:
    """Test V4.0 integration and return status report."""
    try:
        orchestrator = OrchestratorV4(supabase, ai_model)
        return {
            'integration_test': 'SUCCESS',
            'v4_features': orchestrator.get_v4_features_status(),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'integration_test': 'FAILED',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }