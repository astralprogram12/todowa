from .base_agent import BaseAgent
import database_personal  # Fix #4: Proper database import
import os

class ActionAgent(BaseAgent):
    def __init__(self, supabase, ai_model):  # Fix #1: Correct constructor
        super().__init__(supabase, ai_model, agent_name="ActionAgent")
        self.agent_type = "action"
        self.comprehensive_prompts = {}

    def load_comprehensive_prompts(self):
        """Load ALL prompts from the prompts/v1/ directory and requirements."""
        try:
            prompts_dict = {}
            
            # Load all prompts from v1 directory
            v1_dir = "/workspace/user_input_files/todowa/prompts/v1"
            if os.path.exists(v1_dir):
                for file_name in os.listdir(v1_dir):
                    if file_name.endswith('.md'):
                        prompt_name = file_name.replace('.md', '')
                        file_path = os.path.join(v1_dir, file_name)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            prompts_dict[prompt_name] = f.read()
            
            # Load requirements
            requirements_path = "/workspace/user_input_files/99_requirements.md"
            if os.path.exists(requirements_path):
                with open(requirements_path, 'r', encoding='utf-8') as f:
                    prompts_dict['requirements'] = f.read()
            
            # Create comprehensive system prompt for action management
            self.comprehensive_prompts = {
                'core_system': self._build_action_system_prompt(prompts_dict),
                'action_schema': prompts_dict.get('01_action_schema', ''),
                'ai_interactions': prompts_dict.get('04_ai_interactions', ''),
                'safety_validation': prompts_dict.get('07_safety_validation', ''),
                'templates': prompts_dict.get('08_templates', ''),
                'requirements': prompts_dict.get('requirements', ''),
                'all_prompts': prompts_dict
            }
            
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}
    
    def _build_action_system_prompt(self, prompts_dict):
        """Build comprehensive system prompt for action agent."""
        core_identity = prompts_dict.get('00_core_identity', '')
        action_schema = prompts_dict.get('01_action_schema', '')
        ai_interactions = prompts_dict.get('04_ai_interactions', '')
        safety_validation = prompts_dict.get('07_safety_validation', '')
        templates = prompts_dict.get('08_templates', '')
        requirements = prompts_dict.get('requirements', '')
        
        return f"""{core_identity}

## ACTION AGENT SPECIALIZATION
You are specifically focused on action execution and management including:
- Processing system operations and external actions
- Managing AI actions and recurring tasks
- Handling scheduled operations and automation
- Executing safe action sequences with validation
- Managing user preferences and system configurations

{action_schema}

{ai_interactions}

{safety_validation}

{templates}

## REQUIREMENTS COMPLIANCE
{requirements}

## ACTION AGENT BEHAVIOR
- Follow complete action schema for all operations
- Apply safety validation for destructive actions
- Use structured templates for action confirmations
- Implement proper action logging and error handling
- Ensure all actions follow safety measures and validation protocols"""

    async def process(self, user_input, context, routing_info=None):
        """
        Process action requests with comprehensive prompt system.
        routing_info contains assumptions and confidence from IntentClassifierAgent.
        """
        try:
            # Load comprehensive prompts
            if not self.comprehensive_prompts:
                self.load_comprehensive_prompts()
            
            # Use routing_info assumptions if available
            assumptions = routing_info.get('assumptions', {}) if routing_info else {}
            
            # Add routing info to context if available
            enhanced_context = context.copy()
            if routing_info:
                enhanced_context['routing_info'] = routing_info
                enhanced_context['intent_assumptions'] = assumptions
            
            # Use comprehensive prompt system
            return await self._process_with_comprehensive_prompts(user_input, enhanced_context, routing_info)
            
        except Exception as e:
            return {
                "message": f"I encountered an error while trying to perform that action: {str(e)}",
                "actions": ["action_error"],
                "error": str(e)
            }
    
    async def _process_with_comprehensive_prompts(self, user_input, context, routing_info):
        """Process action with comprehensive prompt system."""
        assumptions = routing_info.get('assumptions', {}) if routing_info else {}
        
        # Build comprehensive prompt using all relevant prompts
        system_prompt = self.comprehensive_prompts.get('core_system', 'You are a helpful action agent.')
        
        # Include specific prompt sections for enhanced processing
        action_schema = self.comprehensive_prompts.get('action_schema', '')
        safety_validation = self.comprehensive_prompts.get('safety_validation', '')
        templates = self.comprehensive_prompts.get('templates', '')
        
        user_prompt = f"""
User Input: {user_input}
Context: {context}
Routing Info: {routing_info}

USING COMPREHENSIVE PROMPTS:
1. Follow complete action schema for proper JSON response format
2. Apply safety validation protocols for all operations
3. Use structured templates for action confirmations
4. Ensure proper action logging and error handling
5. Execute actions following all safety measures

Determine what action needs to be performed:
- Action type (send, call, schedule, cancel, etc.)
- Target (person, system, service)
- Parameters or details
- Safety considerations

Available actions:
- Send WhatsApp messages
- Schedule future actions
- Update user preferences
- Manage notifications
- System operations

Generate comprehensive action plan following all prompt guidelines.
"""
        
        # Enhanced AI model call with comprehensive prompts
        full_prompt = f"{system_prompt}\n\nSPECIFIC GUIDANCE:\n{action_schema}\n{safety_validation}\n{templates}\n\nUSER REQUEST:\n{user_prompt}"
        
        response = self.ai_model.generate_content([
            full_prompt
        ])
        response_text = response.text
        
        # Parse and execute the action
        action_result = await self._execute_action(response_text, user_input, context, assumptions)
        
        return action_result

    async def _execute_action(self, action_plan, original_input, context, assumptions):
        """Execute the determined action based on the plan"""
        try:
            # Parse the action plan to determine specific actions
            action_type = assumptions.get('action_type', 'general')
            user_id = context.get('user_id')
            
            # Log the action using the correct database function
            if user_id:
                database_personal.log_action(
                    supabase=self.supabase,
                    user_id=user_id,
                    action_type=action_type,
                    entity_type="action_execution",
                    action_details={"original_input": original_input},
                    success_status=True
                )
            
            if action_type == 'send_message':
                return await self._handle_send_message(original_input, context, assumptions)
            elif action_type == 'schedule':
                return await self._handle_schedule_action(original_input, context, assumptions)
            else:
                return {
                    "message": "I've analyzed your request. What specific action would you like me to help you with?",
                    "actions": ["action_analyzed"]
                }
                
        except Exception as e:
            return {
                "message": f"Error executing action: {str(e)}",
                "actions": ["action_error"],
                "error": str(e)
            }
    
    async def _handle_send_message(self, user_input, context, assumptions):
        """Handle message sending actions"""
        return {
            "message": "I can help you send a message. What would you like to send and to whom?",
            "actions": ["message_prompt"]
        }
    
    async def _handle_schedule_action(self, user_input, context, assumptions):
        """Handle scheduling actions"""
        return {
            "message": "I can help you schedule an action. When would you like it to happen?",
            "actions": ["schedule_prompt"]
        }
