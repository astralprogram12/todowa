from .base_agent import BaseAgent
import database_personal  # Fix #4: Proper database import
import os

class HelpAgent(BaseAgent):
    def __init__(self, supabase, ai_model):  # Fix #1: Correct constructor
        super().__init__(supabase, ai_model, "HelpAgent")
        self.agent_type = "help"
        self.comprehensive_prompts = {}

    async def process(self, user_input, context, routing_info=None):
        """
        Process help and support requests.
        routing_info contains assumptions and confidence from IntentClassifierAgent.
        """
        try:
            # Use routing_info assumptions if available
            assumptions = routing_info.get('assumptions', {}) if routing_info else {}
            
            # Load comprehensive prompts
            if not self.comprehensive_prompts:
                self.load_comprehensive_prompts()
            
            system_prompt = self.comprehensive_prompts.get('core_system', "You are a helpful support agent.")
            
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

            # Fix #2: Correct AI model call with array parameter
            response = await self.ai_model.generate_content([
                system_prompt, user_prompt
            ])
            response_text = response.text
            
            # Determine help category and provide structured assistance
            help_category = assumptions.get('help_category', 'general')
            detailed_help = await self._provide_detailed_help(help_category, user_input, assumptions)
            
            # Log the help request
            user_id = context.get('user_id')
            if user_id:
                database_personal.log_action(
                    supabase=self.supabase,
                    user_id=user_id,
                    action_type="help_request",
                    entity_type="help",
                    action_details={
                        "help_category": help_category,
                        "feature": assumptions.get('feature'),
                        "problem_type": assumptions.get('problem_type')
                    },
                    success_status=True
                )
            
            return {
                "message": f"{response_text}\n\n{detailed_help}",
                "actions": ["help_provided"],
                "data": {
                    "help_category": help_category,
                    "feature": assumptions.get('feature'),
                    "problem_type": assumptions.get('problem_type')
                }
            }
            
        except Exception as e:
            return {
                "message": "I'm here to help! Please let me know what specific assistance you need and I'll do my best to guide you.",
                "actions": ["help_error"],
                "error": str(e)
            }

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
            
            # Create comprehensive system prompt for help agent
            self.comprehensive_prompts = {
                'core_system': self._build_help_system_prompt(prompts_dict),
                'core_identity': prompts_dict.get('00_core_identity', ''),
                'templates': prompts_dict.get('08_templates', ''),
                'ai_interactions': prompts_dict.get('04_ai_interactions', ''),
                'requirements': prompts_dict.get('requirements', ''),
                'all_prompts': prompts_dict
            }
            
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}
    
    def _build_help_system_prompt(self, prompts_dict):
        """Build comprehensive system prompt for help agent."""
        core_identity = prompts_dict.get('00_core_identity', '')
        templates = prompts_dict.get('08_templates', '')
        ai_interactions = prompts_dict.get('04_ai_interactions', '')
        requirements = prompts_dict.get('requirements', '')
        
        return f"""{core_identity}

## HELP AGENT SPECIALIZATION
You are specifically focused on providing assistance and support:
- Providing clear guidance on system features and capabilities
- Offering step-by-step tutorials and instructions
- Troubleshooting common problems and errors
- Categorizing help requests for targeted assistance
- Maintaining a helpful and supportive tone

{templates}

{ai_interactions}

## REQUIREMENTS COMPLIANCE
{requirements}

## HELP AGENT BEHAVIOR
- ALWAYS provide clear, actionable guidance
- Use structured help categories for better organization
- Apply comprehensive templates for consistent responses
- Follow comprehensive prompt system for enhanced assistance"""

    async def _provide_detailed_help(self, help_category, user_input, assumptions):
        """Provide detailed help based on category"""
        
        if help_category == 'general':
            return self._get_general_help()
        elif help_category == 'features':
            feature = assumptions.get('feature', 'tasks')
            return self._get_feature_help(feature)
        elif help_category == 'troubleshooting':
            problem = assumptions.get('problem_type', 'general')
            return self._get_troubleshooting_help(problem)
        elif help_category == 'tutorial':
            topic = assumptions.get('tutorial_topic', 'getting_started')
            return self._get_tutorial_help(topic)
        else:
            return self._get_faq_help()
    
    def _get_general_help(self):
        """Provide general help information"""
        return """
**What I can help you with:**

🎯 **Task Management**: Create, update, and track your tasks
📅 **Reminders**: Set up time-based and location-based reminders  
💬 **Conversations**: Have natural conversations and get information
🔍 **Information**: Get answers to questions and explanations
⚙️ **Preferences**: Customize your experience and settings
📊 **Activity**: View your activity history and logs

**Getting Started:**
- Try saying: "Add a task to buy groceries"
- Or: "Remind me to call John tomorrow at 2pm"
- Or: "What's my recent activity?"

Need specific help? Just ask about any feature!
"""
    
    def _get_feature_help(self, feature):
        """Provide feature-specific help"""
        help_content = {
            'tasks': """
**Task Management Help:**

📝 **Creating Tasks:**
- "Add task: [description]"
- "Remind me to [action]"
- "I need to [task]"

✏️ **Managing Tasks:**
- "Show my tasks"
- "Complete task [name/number]"
- "Update task [name] to [new description]"
- "Delete task [name]"

🏷️ **Task Categories:**
Tasks are automatically categorized (work, personal, health, shopping)
""",
            'reminders': """
**Reminder Help:**

⏰ **Time-based Reminders:**
- "Remind me at 3pm to call the dentist"
- "Set reminder for tomorrow morning: take medication"

📍 **Location-based Reminders:** 
- "Remind me when I get home to feed the cat"
- "When I'm at the store, remind me to buy milk"

🔔 **Managing Reminders:**
- "Show my reminders"
- "Cancel reminder about [topic]"
""",
            'preferences': """
**Preferences Help:**

⚙️ **Customization Options:**
- Set your timezone and location
- Choose notification preferences
- Customize response styles
- Set default categories for tasks

💬 **Usage:**
- "Update my preferences"
- "Change my notification settings"
- "Set my timezone to [timezone]"
"""
        }
        
        return help_content.get(feature, f"Help for {feature} feature is being developed.")
    
    def _get_troubleshooting_help(self, problem):
        """Provide troubleshooting help"""
        troubleshooting = {
            'notifications': """
**Notification Issues:**

📱 Check your phone's notification settings
🔔 Ensure the app has notification permissions
⏰ Verify your timezone is set correctly
📍 For location reminders, check location permissions
""",
            'tasks': """
**Task Issues:**

❌ If tasks aren't saving: Check your internet connection
🔄 If tasks seem outdated: Try refreshing or restarting
📝 If tasks aren't being created: Check your input format
""",
            'general': """
**General Troubleshooting:**

🔌 Check your internet connection
🔄 Try restarting the application
📱 Ensure you have the latest updates
💾 Check if you're running out of storage space

Still having issues? Describe the specific problem you're experiencing.
"""
        }
        
        return troubleshooting.get(problem, troubleshooting['general'])
    
    def _get_tutorial_help(self, topic):
        """Provide tutorial help"""
        tutorials = {
            'getting_started': """
**Getting Started Tutorial:**

1️⃣ **First Steps:**
   - Say "Hello" to start a conversation
   - Try creating your first task: "Add task: test task"

2️⃣ **Basic Commands:**
   - Task creation: "I need to [action]"  
   - Information: "Tell me about [topic]"
   - Help: "Help with [feature]"

3️⃣ **Advanced Features:**
   - Set reminders with specific times
   - View your activity history
   - Customize your preferences
""",
            'task_management': """
**Task Management Tutorial:**

1️⃣ **Creating Tasks:**
   - Basic: "Add task: [description]"
   - With category: "Add work task: finish report"
   - With priority: "Add urgent task: call client"

2️⃣ **Managing Tasks:**
   - View: "Show my tasks" or "What's on my todo list?"
   - Complete: "Mark [task] as done"
   - Delete: "Remove task [name]"

3️⃣ **Organization:**
   - Tasks are auto-categorized by content
   - Set priorities with words like "urgent" or "low priority"
   - Add due dates: "by tomorrow" or "next week"
"""
        }
        
        return tutorials.get(topic, "Tutorial coming soon!")
    
    def _get_faq_help(self):
        """Provide FAQ help"""
        return """
**Frequently Asked Questions:**

❓ **How do I create a task?**
   Simply say "Add task: [your task]" or "I need to [do something]"

❓ **Can I set reminders for specific times?** 
   Yes! Say "Remind me at [time] to [do something]"

❓ **How do I see my task history?**
   Ask "Show my activity" or "What have I done recently?"

❓ **Can I categorize my tasks?**
   Tasks are automatically categorized, but you can specify: "Add work task: [description]"

❓ **How do I cancel a reminder?**
   Say "Cancel reminder about [topic]" or "Remove my reminder for [task]"

❓ **Is my data private?**
   Yes, all your data is encrypted and securely stored.
"""
