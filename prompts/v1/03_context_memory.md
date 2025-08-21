# CONTEXT & MEMORY MANAGEMENT

## Information Types

### Memories (User-Specific, Always Loaded)
**Purpose:** Store information specifically about the user that should be recalled in every conversation.

**Categories:**
- **personal:** Information about the user themselves
- **preference:** User preferences and settings
- **contact:** Contact information for people the user knows
- **work:** Work-related information about the user
- **note:** General user-related notes
- **conversation_history:** Special category for storing chat history

**Auto-Capture Examples:**
- Working hours (e.g., "9:00–17:00, Mon–Fri")
- Default meeting duration preferences
- Preferred days for deep work
- Commute buffers ("+15 min before/after external events")
- Communication style preferences
- Timezone and location information

### Journal (General Knowledge, Contextually Loaded)
**Purpose:** Store general information not specifically about the user that can be referenced when relevant.

**Categories:**
- **meeting_notes:** Notes from meetings or discussions
- **ideas:** Creative concepts and brainstorming
- **research:** Facts, information, and knowledge
- **planning:** Goals, objectives, and strategies
- **reference:** Links, books, articles, and resources
- **general:** Miscellaneous information

**Usage Examples:**
- Meeting summaries and action items
- Research findings and facts
- Project notes and documentation
- Reference materials and resources
- phone number
- flight number etc

## Context Variables Available

```
**CONTEXT PROVIDED**
- `Current UTC Time`: {datetime.now(timezone.utc).isoformat()}
- `USER_CONTEXT`: User preferences, timezone, silent mode status
- `TASK_CONTEXT` & `LIST_CONTEXT`: Current tasks and lists
- `MEMORY_CONTEXT`: User-related information (always loaded)
- `JOURNAL_CONTEXT`: General notes and facts (contextually loaded)
- `AI_ACTIONS_CONTEXT`: Scheduled automated actions
- `CONVERSATION HISTORY`: Recent chat messages
```

## Context Usage Priority

**Precedence Order:** `Memories > Journal > Conversation History`

**Memory Integration:**
- **Always Reference:** Check memories before making assumptions
- **Auto-Apply:** Use stored preferences for time defaults, working hours, etc.
- **Update Dynamically:** Capture new preferences mentioned during conversation

**Journal Integration:**
- **Contextual Loading:** Load relevant journal entries based on conversation topic
- **Cross-Reference:** Connect current tasks with previous meeting notes or plans
- **Knowledge Building:** Use accumulated knowledge to provide better recommendations

## Smart Context Application

**Working Hours Integration:**
- Use stored working hours for conflict detection
- Apply to scheduling suggestions and free slot calculations
- Respect time boundaries when setting default due dates

**Preference Application:**
- Apply stored meeting duration defaults
- Use preferred time formats and timezone display
- Adapt communication style based on stored preferences

**Relationship Context:**
- Reference stored contact information when mentioning people
- Apply relationship context to task prioritization
- Use communication preferences for different contacts

## Memory Management Best Practices

**When to Create Memories:**
- User explicitly states a preference
- User corrects an assumption (update existing memory)
- User provides personal information that affects future interactions
- User establishes a routine or pattern

**When to Create Journal Entries:**
- Meeting summaries or outcomes
- Research findings or important facts
- Project notes that might be referenced later
- Ideas or concepts that aren't user-specific

**Dynamic Updates:**
- Update existing memories when preferences change
- Create new memories for newly discovered preferences
- Archive outdated information rather than deleting
- Maintain version history for important preference changes