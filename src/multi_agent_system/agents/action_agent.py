from .base_agent import BaseAgent

class ActionAgent(BaseAgent):
    def __init__(self, supabase, ai_model):
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
            
            # Load prompts
            prompt_files = [
                "01_main_system_prompt.md",
                "02_action_agent_specific.md",
                "03_context_understanding.md",
                "04_response_formatting.md",
                "05_datetime_handling.md",
                "06_error_handling.md",
                "07_conversation_flow.md",
                "08_whatsapp_integration.md",
                "09_intelligent_decision_tree.md"
            ]
            
            system_prompt = await self.load_prompts(prompt_files)
            
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

            response = await self.ai_model.generate_content(
                system_prompt, user_prompt
            )
            
            # Parse and execute the action
            action_result = await self._execute_action(response, user_input, enhanced_context, assumptions)
            
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
            
            if 'send' in action_plan.lower() or action_type == 'send':
                return await self._handle_send_action(action_plan, context)
            elif 'schedule' in action_plan.lower() or action_type == 'schedule':
                return await self._handle_schedule_action(action_plan, context)
            elif 'update' in action_plan.lower() or action_type == 'update':
                return await self._handle_update_action(action_plan, context)
            elif 'cancel' in action_plan.lower() or action_type == 'cancel':
                return await self._handle_cancel_action(action_plan, context)
            else:
                return {
                    "message": action_plan,
                    "actions": ["action_planned"],
                    "requires_confirmation": True
                }
                
        except Exception as e:
            return {
                "message": f"Action execution failed: {str(e)}",
                "actions": ["action_failed"],
                "error": str(e)
            }

    async def _handle_send_action(self, action_plan, context):
        """Handle sending messages or communications"""
        return {
            "message": "📤 Message sending functionality would be implemented here.",
            "actions": ["send_message"],
            "data": {"action_plan": action_plan}
        }

    async def _handle_schedule_action(self, action_plan, context):
        """Handle scheduling future actions"""
        return {
            "message": "📅 Scheduling functionality would be implemented here.",
            "actions": ["schedule_action"],
            "data": {"action_plan": action_plan}
        }

    async def _handle_update_action(self, action_plan, context):
        """Handle updating settings or preferences"""
        return {
            "message": "⚙️ Update functionality would be implemented here.",
            "actions": ["update_settings"],
            "data": {"action_plan": action_plan}
        }

    async def _handle_cancel_action(self, action_plan, context):
        """Handle canceling existing actions or schedules"""
        return {
            "message": "❌ Cancellation functionality would be implemented here.",
            "actions": ["cancel_action"],
            "data": {"action_plan": action_plan}
        }