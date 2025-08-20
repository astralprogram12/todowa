from .base_agent import BaseAgent

class HelpAgent(BaseAgent):
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model, "HelpAgent")
        self.agent_type = "help"

    async def process(self, user_input, context, routing_info=None):
        """
        Process help and support requests.
        routing_info contains assumptions and confidence from IntentClassifierAgent.
        """
        try:
            # Use routing_info assumptions if available
            assumptions = routing_info.get('assumptions', {}) if routing_info else {}
            
            # Load prompts
            prompt_files = [
                "01_main_system_prompt.md",
                "02_help_agent_specific.md",
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
            
            # Determine help type and provide appropriate assistance
            user_prompt = f"""
User Input: {user_input}
Context: {enhanced_context}

This is a help request. Analyze what kind of help the user needs:

1. **General Help**: Overview of capabilities and features
2. **Feature Help**: How to use specific features (tasks, reminders, etc.)
3. **Troubleshooting**: Problems or errors they're experiencing
4. **Tutorial**: Step-by-step guidance
5. **FAQ**: Common questions and answers

If routing assumptions suggest specific:
- Help category
- Feature they need help with
- Problem they're facing

Incorporate these assumptions confidently and provide targeted assistance.

Provide clear, actionable help information.
"""

            response = self.ai_model.generate_response(
                system_prompt, user_prompt
            )
            
            # Determine help category and provide structured assistance
            help_category = assumptions.get('help_category', 'general')
            detailed_help = await self._provide_detailed_help(help_category, user_input, assumptions)
            
            return {
                "message": f"{response}\n\n{detailed_help}",
                "actions": ["help_provided"],
                "data": {
                    "help_category": help_category,
                    "feature": assumptions.get('feature'),
                    "problem_type": assumptions.get('problem_type')
                }
            }
            
        except Exception as e:
            return {
                "message": "I'm here to help! Here are the main things I can assist you with:\n\n🔹 **Tasks**: Create, manage, and track your to-do items\n🔹 **Reminders**: Set time-based reminders for important events\n🔹 **Information**: Get answers to your questions\n🔹 **Actions**: Perform various system operations\n\nWhat would you like help with?",
                "actions": ["help_fallback"],
                "error": str(e)
            }

    async def _provide_detailed_help(self, category, user_input, assumptions):
        """Provide detailed help based on category"""
        help_content = {
            "general": self._get_general_help(),
            "tasks": self._get_task_help(),
            "reminders": self._get_reminder_help(),
            "features": self._get_feature_help(),
            "troubleshooting": self._get_troubleshooting_help(),
            "commands": self._get_commands_help()
        }
        
        return help_content.get(category, self._get_general_help())

    def _get_general_help(self):
        return """
🤖 **Todowa - Your AI Personal Assistant**

I can help you with:

📝 **Task Management**
   • Create and manage tasks
   • Set priorities and deadlines
   • Track completion status

⏰ **Reminders**
   • Set time-based reminders
   • Recurring reminders
   • Location-based alerts

💬 **Conversation**
   • Answer questions
   • Provide information
   • General assistance

⚙️ **Settings**
   • Manage preferences
   • Configure notifications
   • Update personal info

Type "help [feature]" for specific guidance!
"""

    def _get_task_help(self):
        return """
📝 **Task Management Help**

**Creating Tasks:**
• "Add task: Buy groceries"
• "Create a task to call mom tomorrow"
• "New task: Finish project report by Friday"

**Managing Tasks:**
• "Show my tasks"
• "Mark task 1 as complete"
• "Delete task about groceries"
• "Update task priority to high"

**Task Features:**
• Set due dates and times
• Add priority levels (high, medium, low)
• Include descriptions and notes
• Set recurring tasks

Example: "Add high priority task: Submit report by 5 PM today"
"""

    def _get_reminder_help(self):
        return """
⏰ **Reminder Help**

**Setting Reminders:**
• "Remind me to call John at 3 PM"
• "Set reminder for dentist appointment tomorrow at 10 AM"
• "Remind me every Monday to submit timesheet"

**Reminder Types:**
• One-time reminders
• Recurring reminders (daily, weekly, monthly)
• Location-based reminders

**Managing Reminders:**
• "Show my reminders"
• "Cancel reminder about dentist"
• "Update reminder time to 4 PM"

Example: "Remind me to take medication every day at 8 AM"
"""

    def _get_feature_help(self):
        return """
🔧 **Feature Guide**

**Available Features:**

1. **Smart Intent Recognition**
   • I understand context and make intelligent assumptions
   • No need for exact keywords

2. **Multi-Agent Processing**
   • Different specialists handle different request types
   • Seamless handoffs between agents

3. **WhatsApp Integration**
   • Full WhatsApp message support
   • Rich formatting and media

4. **Context Awareness**
   • Remembers conversation history
   • Understands references to previous topics

5. **Flexible Communication**
   • Natural language processing
   • Confident responses even with ambiguous input

Just speak naturally - I'll understand!
"""

    def _get_troubleshooting_help(self):
        return """
🔧 **Troubleshooting Guide**

**Common Issues:**

❌ **Not Understanding Requests**
• Try rephrasing with more context
• Be specific about what you want
• Include relevant details (times, dates, names)

❌ **Tasks Not Saving**
• Check your internet connection
• Try creating the task again
• Contact support if issues persist

❌ **Reminders Not Working**
• Verify the date/time format
• Check notification settings
• Ensure permissions are granted

❌ **General Errors**
• Try restarting the conversation
• Check for system updates
• Report persistent issues

**Need More Help?**
Type "contact support" for assistance options.
"""

    def _get_commands_help(self):
        return """
⌨️ **Command Examples**

**Task Commands:**
• "Add task: [description]"
• "List my tasks"
• "Complete task [number/name]"
• "Delete task [number/name]"

**Reminder Commands:**
• "Remind me to [action] at [time]"
• "Show my reminders"
• "Cancel reminder about [topic]"

**Information Commands:**
• "What is [topic]?"
• "How do I [action]?"
• "Explain [concept]"

**Settings Commands:**
• "Change my timezone to [timezone]"
• "Set notification preferences"
• "Update my profile"

**General Commands:**
• "Help" - Show this help
• "Status" - Show current state
• "Clear" - Clear conversation

Remember: You don't need exact commands - I understand natural language!
"""