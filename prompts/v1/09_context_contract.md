# Context Differentiation Documentation

## Types of Information in the System

### Context Provided to the Agent

When interacting with users, the agent has access to different types of information stored in the system:

```
**CONTEXT PROVIDED**
- `Current UTC Time`: {datetime.now(timezone.utc).isoformat()}
- `USER_CONTEXT`: Contains the user's preferences, including their timezone.
- `TASK_CONTEXT` & `LIST_CONTEXT`: The user's current tasks and lists.
- `MEMORY_CONTEXT`: User-related information that must be recalled in conversations.
- `JOURNAL_CONTEXT`: Non-user-related information like notes and facts.
- `AI_ACTIONS_CONTEXT`: Scheduled automated actions.
- `CONVERSATION HISTORY`: The recent chat messages.
```

### Different Types of User Information

1. **Memories**
   - Purpose: Store information specifically about the user
   - Examples: Preferences, personal details, likes/dislikes
   - Access: Automatically included in every conversation
   - Characteristics: Personal and user-centric
   - Definition: "Memory is something related to the user that must be initiated in every conversation."

2. **Journal Entries**
   - Purpose: Store general information not specifically about the user
   - Examples: Meeting summaries, trivia facts, research notes, ideas
   - Access: Available when relevant to the conversation
   - Characteristics: General and topic-centric
   - Definition: "Journal can be anything that is unrelated to the user, like meeting summaries, random trivia facts, etc."

3. **AI Actions**
   - Purpose: Scheduled automated tasks
   - Examples: Daily task summaries, weekly reports, reminders
   - Access: Run on a schedule defined by cron expressions
   - Characteristics: Temporal and service-oriented
   - Definition: "AI actions are automated tasks that run on a predefined schedule without requiring user initiation."

### Categorization

Both memories and journal entries support automatic categorization based on their content:

#### Memory Categories
- personal: Information about the user themselves
- preference: User preferences and settings
- contact: Contact information for people the user knows
- work: Work-related information
- note: General user-related notes
- conversation_history: Special category for storing chat history

#### Journal Categories
- meeting_notes: Notes from meetings or discussions
- ideas: Creative concepts and brainstorming
- research: Facts, information, and knowledge
- planning: Goals, objectives, and strategies
- reference: Links, books, articles, and resources
- general: Miscellaneous information

These categories help organize and retrieve information efficiently when needed.
