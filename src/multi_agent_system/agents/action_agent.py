from .base_agent import BaseAgent
import database_personal  # Fix #4: Proper database import

class ActionAgent(BaseAgent):
    def __init__(self, supabase, ai_model):  # Fix #1: Correct constructor
        super().__init__(supabase, ai_model, agent_name="ActionAgent")
        self.agent_type = "action"

    async def process(self, user_input, context, routing_info=None):
        """
        Process action requests that require system operations or external actions.
        routing_info contains assumptions and confidence from IntentClassifierAgent.
        """
        try:
            # Use routing_info assumptions if available
            assumptions = routing_info.get('assumptions', {}) if routing_info else {}
            
            # Fix #3: Load prompts synchronously (no await)
            prompts_dict = self.load_prompts("prompts")
            system_prompt = prompts_dict.get("01_main_system_prompt", "You are a helpful action agent.")
            
            # Add routing info to context if available
            enhanced_context = context.copy()
            if routing_info:
                enhanced_context['routing_info'] = routing_info
                enhanced_context['intent_assumptions'] = assumptions
            
            # Analyze the action request
            user_prompt = f"""
User Input: {user_input}
Context: {enhanced_context}

This is an action request. Determine what action needs to be performed.

If routing assumptions suggest specific:
- Action type (send, call, schedule, cancel, etc.)
- Target (person, system, service)
- Parameters or details

Incorporate these assumptions confidently.

Available actions:
- Send WhatsApp messages
- Schedule future actions
- Update user preferences
- Manage notifications
- System operations

Respond with the action plan and any confirmations needed.
"""

            # Fix #2: Correct AI model call with array parameter
            response = await self.ai_model.generate_content([
                system_prompt, user_prompt
            ])
            response_text = response.text
            
            # Parse and execute the action
            action_result = await self._execute_action(response_text, user_input, enhanced_context, assumptions)
            
            return action_result
            
        except Exception as e:
            return {
                "message": f"I encountered an error while trying to perform that action: {str(e)}",
                "actions": ["action_error"],
                "error": str(e)
            }

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
