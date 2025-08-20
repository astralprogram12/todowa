# Guide Agent - provides how-to instructions and procedural guidance

from .base_agent import BaseAgent

class GuideAgent(BaseAgent):
    """Agent for providing how-to instructions and procedural guidance."""
    
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model, "GuideAgent")
    
    async def process(self, user_input, context):
        """Process guide requests and return a response.
        
        Args:
            user_input: The input text from the user
            context: The context of the conversation
            
        Returns:
            A response to the user input
        """
        user_id = context.get('user_id')
        
        # Determine the topic for the guide
        topic = self._determine_topic(user_input)
        
        # Generate guide based on the topic and user input
        return await self._generate_guide(user_id, user_input, topic, context)
    
    def _determine_topic(self, user_input):
        """Determine the topic for the guide from the user input."""
        user_input_lower = user_input.lower()
        
        # Extract the topic from the user input
        topic_indicators = ['how to', 'guide for', 'steps to', 'instructions for', 'process for']
        
        for indicator in topic_indicators:
            if indicator in user_input_lower:
                parts = user_input_lower.split(indicator, 1)
                if len(parts) > 1:
                    return parts[1].strip()
        
        # If no specific topic is found, use the entire input
        return user_input
    
    async def _generate_guide(self, user_id, user_input, topic, context):
        """Generate a guide based on the topic and user input."""
        try:
            # Use the AI model to generate a guide
            prompt = f"Create a step-by-step guide for: {topic}\n\nProvide clear, detailed instructions with examples where helpful."
            
            # In a real implementation, we would use the AI model to generate the guide
            # For now, let's provide a sample response
            guide = self._get_sample_guide(topic)
            
            # Log the action
            self._log_action(
                user_id=user_id,
                action_type="generate_guide",
                entity_type="guide",
                action_details={
                    "topic": topic,
                    "query": user_input
                },
                success_status=True
            )
            
            return {
                "status": "ok",
                "message": f"Here's a step-by-step guide for '{topic}':",
                "guide": guide,
                "topic": topic
            }
            
        except Exception as e:
            error_msg = str(e)
            
            # Log the error
            self._log_action(
                user_id=user_id,
                action_type="generate_guide",
                entity_type="guide",
                action_details={
                    "topic": topic,
                    "query": user_input
                },
                success_status=False,
                error_details=error_msg
            )
            
            return {
                "status": "error",
                "message": f"Failed to generate guide: {error_msg}"
            }
    
    def _get_sample_guide(self, topic):
        """Get a sample guide based on common topics."""
        # Sample guides for common topics
        topic_lower = topic.lower()
        
        if 'reminder' in topic_lower or 'set reminder' in topic_lower:
            return """**How to Set a Reminder:**

**Step 1: Choose the Task**
• Decide what task needs a reminder
• Be specific about what needs to be done

**Step 2: Specify the Time**
• Choose when you need to be reminded
• Format examples: "tomorrow at 3pm" or "Monday at 9am"

**Step 3: Set the Reminder**
• Type: "Remind me to [task] at [time]"
• Example: "Remind me to call Sarah tomorrow at 2pm"

**Step 4: Confirm Details**
• Check that the task and time are correct
• Make adjustments if needed

**Examples:**
• "Remind me to take medication every day at 9am"
• "Set a reminder for my dentist appointment on Thursday at 10am"
• "Remind me to review project notes in 3 hours"""
        
        elif 'task' in topic_lower or 'add task' in topic_lower:
            return """**How to Add a Task:**

**Step 1: Define the Task**
• Decide what needs to be accomplished
• Be specific and actionable

**Step 2: Categorize the Task**
• Choose an appropriate category
• Use existing categories or create a new one

**Step 3: Set Due Date (Optional)**
• Decide when the task needs to be completed
• Format examples: "today", "tomorrow", "next Monday"

**Step 4: Add the Task**
• Type: "Add task: [task description] in category [category] due [date]"
• Example: "Add task: prepare quarterly report in category Work due Friday"

**Step 5: Add Details (Optional)**
• Include additional notes or context
• Specify priority or time estimates

**Examples:**
• "Add task: buy groceries in category Shopping"
• "Create task: finish project presentation due tomorrow at 5pm"
• "Add task: schedule doctor appointment with notes: annual checkup"""
        
        elif 'silent mode' in topic_lower or 'activate silent' in topic_lower:
            return """**How to Use Silent Mode:**

**Step 1: Decide on Duration**
• Determine how long you need silent mode
• Common durations: 30 minutes, 1 hour, 2 hours

**Step 2: Activate Silent Mode**
• Type: "Go silent for [duration]"
• Example: "Go silent for 1 hour"
• Alternatives: "Activate silent mode" or "Turn on silent mode"

**Step 3: Confirm Activation**
• Check the confirmation message
• Note the exact end time

**Step 4: Use During Focus Time**
• Work without interruptions
• The system will collect messages without notifying you

**Step 5: Exit Silent Mode**
• Wait for automatic expiration, or
• Type: "Exit silent mode" to end early

**Examples:**
• "Go silent for 30 minutes while I'm in a meeting"
• "Activate silent mode for 2 hours"
• "Turn on silent mode until 5pm"""
        
        elif 'category' in topic_lower or 'categorize' in topic_lower:
            return """**How to Use Task Categories:**

**Step 1: View Existing Categories**
• Type: "Show my categories"
• Review your most-used categories

**Step 2: Create a New Category**
• When adding a task, specify a new category
• Example: "Add task: research suppliers in category Vendors"

**Step 3: Assign Tasks to Categories**
• Always include a category when creating tasks
• Format: "in category [name]"

**Step 4: Update Task Categories**
• Type: "Update task [task name] category to [new category]"
• Example: "Update task quarterly report category to Finance"

**Step 5: Filter Tasks by Category**
• Type: "Show my Work tasks" or "List tasks in Shopping category"
• Use for focused review of specific areas

**Examples:**
• "Add task: schedule meeting in category Work"
• "Show all tasks in Personal category"
• "Create new task: gym session in category Health"""
        
        else:
            # Generic guide template for any topic
            return f"""**How to {topic}:**

**Step 1: Prepare**
• Gather necessary information and resources
• Ensure you have everything needed to complete the task

**Step 2: Plan Your Approach**
• Break down the process into manageable steps
• Decide on the order of operations

**Step 3: Execute the Main Steps**
• Follow the process step by step
• Pay attention to details as you progress

**Step 4: Review and Refine**
• Check your work for errors or improvements
• Make adjustments as needed

**Step 5: Complete and Confirm**
• Finalize the task
• Verify that everything is working as expected

**Examples:**
• Example approach for beginners
• Alternative method for different circumstances
• Advanced technique for experienced users"""
