SILENT MODE CONTEXT:

When building context for the AI, include silent mode status in the user context:

**Silent session context structure:**
```
silent_context: {
  is_active: boolean,
  session_id: string,
  start_time: ISO timestamp,
  duration_minutes: number,
  trigger_type: 'manual' | 'auto' | 'scheduled',
  action_count: number,
  remaining_minutes: number
}
```

**Context usage:**
- If silent_context.is_active is true, mention current silent status in responses
- Show remaining time and accumulated action count
- Provide exit instructions
- Do not overwhelm with silent mode info unless directly asked

**Auto silent mode preferences:**
Include in user_context:
- auto_silent_enabled: boolean
- auto_silent_start_hour: number (0-23)
- auto_silent_end_hour: number (0-23)

**Silent mode aware responses:**
When NOT in silent mode, can mention:
- "You can use silent mode if you need uninterrupted time"
- "Say 'go silent for 2 hours' to activate silent mode"
- "Your daily silent mode is set for 7-11 AM" (if enabled)
