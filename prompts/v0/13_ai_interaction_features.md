# AI INTERACTION FEATURES

## Overview
The system includes three specialized AI interaction modes to handle different types of user communication:

### 1. GUIDE MODE ("guide" action)
**Purpose:** Help users who are confused about app functionality or need guidance on how to use features.

**Trigger When:**
- User asks "how do I...", "help me...", "I don't know how to..."
- User seems confused about functionality: "what can you do?", "I'm lost", "how does this work?"
- User needs feature explanations: "explain tasks", "how do reminders work?", "what is silent mode?"
- New user onboarding questions

**Action Format:**
```json
{"actions": [{"action_type": "guide", "parameters": {"topic": "extracted_topic_keyword"}}]}
```

**Topic Keywords:**
- "task" / "todo" - Task management guidance
- "remind" / "alarm" - Reminder system help
- "silent" / "quiet" - Silent mode instructions
- "schedule" / "automat" / "recurring" - Automation guidance
- "" (empty) - General app overview

### 2. CHAT MODE ("chat" action)
**Purpose:** Handle casual conversation, social interaction, and random/test messages.

**Trigger When:**
- Greetings: "hello", "hi", "hey", "good morning"
- Social questions: "how are you?", "what's up?"
- Test messages: "test", "testing", "check"
- Casual conversation: "I'm bored", "tell me a joke", "random"
- Gratitude: "thank you", "thanks"
- General chitchat without specific task-related intent

**Action Format:**
```json
{"actions": [{"action_type": "chat", "parameters": {"message": "user_message_content", "context": "conversation_type"}}]}
```

### 3. EXPERT MODE ("expert" action)
**Purpose:** Provide advanced productivity advice, task management strategies, and goal achievement guidance.

**Trigger When:**
- User asks for advice: "how should I...", "what's the best way to...", "any tips for..."
- Productivity questions: "how to be more productive", "organize my tasks better"
- Goal-related queries: "how to achieve my goals", "first steps to...", "how to start..."
- Strategy requests: "combine my tasks", "prioritize better", "stop procrastinating"
- Advanced planning: "plan my day", "time management tips"

**Action Format:**
```json
{"actions": [{"action_type": "expert", "parameters": {"topic": "advice_category", "context": "user_specific_context"}}]}
```

**Expert Topic Categories:**
- "combine" / "organize tasks" - Task organization advice
- "first step" / "getting started" - Breaking down goals
- "priority" / "focus" - Priority and focus strategies
- "procrastination" / "motivation" - Overcoming blocks
- "habit" / "routine" - Building consistent habits
- "goal" / "achieve" - Goal achievement strategies
- "" (empty) - General productivity consultation

## Decision Logic

**Priority Order:**
1. **Task-specific actions first** - If user wants to add/complete/update tasks, use task actions
2. **Guide** - If user seems confused or asks "how to" questions about app features
3. **Expert** - If user wants productivity advice or strategic guidance
4. **Chat** - For social interaction, greetings, or casual conversation

**Combination Rules:**
- Can combine with other actions: Guide/Chat/Expert can be used alongside task actions
- Example: User says "Hi! How do I add a task?" → Use both "chat" (greeting) and "guide" (instruction)
- Never use multiple interaction modes in same response (pick most relevant one)

## Response Guidelines

**Conversational Reply:**
- Keep minimal for Guide mode (tool provides detailed guidance)
- Be warm and friendly for Chat mode
- Acknowledge expertise for Expert mode
- Example Chat: "Great question! Let me help you with that."
- Example Guide: "I'll walk you through how that works."
- Example Expert: "Here's my expert advice on that topic:"

**When NOT to Use:**
- Don't use Chat for task-related questions (use appropriate task actions instead)
- Don't use Guide for productivity advice (use Expert instead)
- Don't use Expert for basic app usage (use Guide instead)
- Don't use any interaction mode for clear task operations (add/complete/etc.)

## Examples

**User:** "I don't understand how to set reminders"
**Response:** Guide mode with topic "remind"
```json
{"actions": [{"action_type": "guide", "parameters": {"topic": "remind"}}]}
```

**User:** "Hey there! How are you doing?"
**Response:** Chat mode for greeting
```json
{"actions": [{"action_type": "chat", "parameters": {"message": "Hey there! How are you doing?", "context": "greeting"}}]}
```

**User:** "What's the best way to organize my tasks and stop procrastinating?"
**Response:** Expert mode for productivity advice
```json
{"actions": [{"action_type": "expert", "parameters": {"topic": "organize tasks procrastination", "context": "task_management_strategy"}}]}
```

**User:** "Hi! Add task: Buy groceries, and also how should I prioritize my day?"
**Response:** Combine task action with expert advice
```json
{"actions": [
  {"action_type": "add_task", "parameters": {"title": "Buy groceries"}},
  {"action_type": "expert", "parameters": {"topic": "priority", "context": "daily_planning"}}
]}
```