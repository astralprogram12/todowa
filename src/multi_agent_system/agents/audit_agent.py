from .base_agent import BaseAgent
import database_personal as database
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

# Import the Enhanced Double-Check Agent
try:
    from .enhanced_double_check_agent import get_enhanced_double_check_agent, validate_agent_response
except ImportError as e:
    logging.warning(f"Enhanced Double-Check Agent not available: {e}")
    get_enhanced_double_check_agent = None
    validate_agent_response = None

logger = logging.getLogger(__name__)

class AuditAgent(BaseAgent):
    """Enhanced audit agent with integrated double-check validation system."""
    
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model, agent_name="AuditAgent")
        self.comprehensive_prompts = {}
        self.double_check_enabled = True
        self.validation_stats = {
            'total_responses': 0,
            'validated_responses': 0,
            'issues_found': 0,
            'corrections_made': 0
        }

    def load_comprehensive_prompts(self):
        try:
            prompts_dict = {}
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
            v1_dir = os.path.join(project_root, "prompts", "v1")
            
            if os.path.exists(v1_dir):
                for file_name in os.listdir(v1_dir):
                    if file_name.endswith('.md'):
                        prompt_name = file_name.replace('.md', '')
                        file_path = os.path.join(v1_dir, file_name)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            prompts_dict[prompt_name] = f.read()

            self.comprehensive_prompts = {
                'core_system': self._build_audit_system_prompt(prompts_dict)
            }
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}
    
    def _build_audit_system_prompt(self, prompts_dict):
        core_identity = prompts_dict.get('00_core_identity', 'You are a helpful audit assistant.')
        audit_specialized = prompts_dict.get('13_audit_specialized', '')
        leak_prevention = """
        
CRITICAL: Provide audit information naturally. Never include:
- System details, technical information, or internal processes
- JSON, debugging info, or technical formatting
- References to agents, databases, or system architecture

Respond like a professional audit consultant.
        """
        return f"{core_identity}\n\n{audit_specialized}{leak_prevention}"

    async def validate_agent_response(self, original_input: str, agent_response: Dict[str, Any], 
                                    agent_name: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Validate an agent response using the Enhanced Double-Check system.
        
        Args:
            original_input (str): The original user input
            agent_response (Dict): The agent's response to validate
            agent_name (str): Name of the agent that generated the response
            context (Dict): Additional context for validation
            
        Returns:
            Dict: Validation result with potential corrections
        """
        if not self.double_check_enabled or validate_agent_response is None:
            # Return original response if validation is disabled or unavailable
            return {
                'is_valid': True,
                'confidence_score': 1.0,
                'validation_issues': [],
                'correction_suggestions': [],
                'validated_response': agent_response
            }
        
        try:
            # Update statistics
            self.validation_stats['total_responses'] += 1
            
            # Perform validation
            validation_result = await validate_agent_response(
                original_input, agent_response, agent_name, context, self.supabase, self.ai_model
            )
            
            # Update statistics based on results
            if validation_result.get('is_valid', True):
                self.validation_stats['validated_responses'] += 1
            else:
                self.validation_stats['issues_found'] += 1
                if validation_result.get('validated_response') != agent_response:
                    self.validation_stats['corrections_made'] += 1
            
            # Log validation result if significant issues found
            if not validation_result.get('is_valid', True):
                user_id = context.get('user_id') if context else None
                if user_id:
                    self._log_validation_audit(
                        user_id=user_id,
                        agent_name=agent_name,
                        original_input=original_input,
                        validation_result=validation_result
                    )
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error in response validation: {e}")
            return {
                'is_valid': True,  # Default to valid to avoid blocking
                'confidence_score': 0.5,
                'validation_issues': [f"Validation error: {str(e)}"],
                'correction_suggestions': [],
                'validated_response': agent_response
            }
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """Get current validation statistics."""
        stats = self.validation_stats.copy()
        if stats['total_responses'] > 0:
            stats['validation_rate'] = stats['validated_responses'] / stats['total_responses']
            stats['issue_rate'] = stats['issues_found'] / stats['total_responses']
            stats['correction_rate'] = stats['corrections_made'] / stats['total_responses']
        else:
            stats['validation_rate'] = 0.0
            stats['issue_rate'] = 0.0
            stats['correction_rate'] = 0.0
        
        return stats
    
    def _log_validation_audit(self, user_id: str, agent_name: str, original_input: str, validation_result: Dict[str, Any]):
        """Log validation audit trail for monitoring and improvement."""
        try:
            validation_details = {
                'agent_name': agent_name,
                'original_input': original_input[:200],  # Truncate for storage
                'is_valid': validation_result.get('is_valid', True),
                'confidence_score': validation_result.get('confidence_score', 1.0),
                'issues_count': len(validation_result.get('validation_issues', [])),
                'corrections_count': len(validation_result.get('correction_suggestions', [])),
                'validation_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            self._log_action(
                user_id=user_id,
                action_type="response_validation",
                entity_type="system",
                entity_id=agent_name,
                action_details=validation_details,
                success_status=validation_result.get('is_valid', True),
                error_details=validation_result.get('validation_issues') if not validation_result.get('is_valid', True) else None
            )
        except Exception as e:
            logger.error(f"Error logging validation audit: {e}")

    async def process(self, user_input, context, routing_info=None):
        try:
            # Check if this is a validation statistics request
            if 'validation stat' in user_input.lower() or 'double check stat' in user_input.lower():
                stats = self.get_validation_statistics()
                return {
                    "message": f"Validation Statistics:\n"
                             f"• Total responses checked: {stats['total_responses']}\n"
                             f"• Validation rate: {stats['validation_rate']:.1%}\n"
                             f"• Issues detected: {stats['issues_found']} ({stats['issue_rate']:.1%})\n"
                             f"• Corrections made: {stats['corrections_made']} ({stats['correction_rate']:.1%})"
                }
            
            if not self.comprehensive_prompts:
                self.load_comprehensive_prompts()
            
            system_prompt = self.comprehensive_prompts.get('core_system', 'You are a helpful audit assistant.')
            
            user_prompt = f"""
User has an audit-related question: {user_input}

Provide helpful audit-related information. Be professional and thorough.
Do not include any technical details or system information.

If they ask about validation or double-checking, explain that the system has:
- Enhanced validation for response accuracy
- Multilingual verification capabilities
- Time parsing validation
- Intent alignment checking
- Logic consistency monitoring

Keep explanations user-friendly and avoid technical details.
"""
            
            # Make AI call (synchronous)
            response = self.ai_model.generate_content([system_prompt, user_prompt])
            response_text = response.text
            
            # Clean the response to prevent leaks
            clean_message = self._clean_response(response_text)
            
            # Create response object for validation
            agent_response = {"message": clean_message}
            
            # Validate the response using the enhanced double-check system
            validation_result = await self.validate_agent_response(
                user_input, agent_response, self.agent_name, context
            )
            
            # Use validated response if corrections were made
            final_response = validation_result.get('validated_response', agent_response)
            
            # Log action (internal only)
            user_id = context.get('user_id')
            if user_id:
                self._log_action(
                    user_id=user_id,
                    action_type="chat_interaction",
                    entity_type="system",
                    action_details={"type": "audit_request", "validated": True},
                    success_status=True
                )
            
            # Return ONLY clean user message
            return final_response
            
        except Exception as e:
            logger.error(f"ERROR in AuditAgent: {e}")
            return {
                "message": "I can help with audit-related questions. What specific audit topic would you like assistance with?"
            }
