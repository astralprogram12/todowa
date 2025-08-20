# SILENT MODE SYSTEM

## INTEGRATION WITH DECISION TREE

**Classification Priority:** Silent mode is **Branch 2** in the intelligent decision tree (HIGH PRIORITY)

**Smart Routing Function:** `handle_silent_mode` automatically determines intent:
- **Activation patterns** → routes to `activate_silent_mode`
- **Deactivation patterns** → routes to `deactivate_silent_mode`  
- **Status patterns** → routes to `get_silent_status`
- **Duration extraction** → automatically parses time from user input

**Detection Patterns:**
```regex
# Activation
\b(go\s+silent|activate\s+silent|turn\s+on\s+silent)\b
\b(silent\s+mode|quiet\s+mode)\b
\b(don't\s+reply|stop\s+replying|no\s+replies?)\b

# Deactivation  
\b(exit\s+silent|end\s+silent|stop\s+silent)\b
\b(back\s+online|resume\s+replies?)\b

# Status
\b(silent\s+status|am\s+i\s+silent|in\s+silent\s+mode)\b
```

## Commands Recognition

### Activation Commands
- "go silent for [duration]"
- "don't reply for [duration]"
- "silent mode for [duration]"
- "activate silent mode"

### Deactivation Commands
- "exit silent mode"
- "end silent mode"
- "stop silent mode"
- "deactivate silent mode"

### Status Commands
- "am I in silent mode?"
- "silent mode status"
- "check silent mode"

## Duration Handling

**Supported Formats:**
- "2 hours", "30 minutes", "1 hour", "90 minutes"
- "for 2h", "for 30m", "for 1.5 hours"

**Defaults & Limits:**
- **Default:** 1 hour if no duration specified
- **Minimum:** 5 minutes
- **Maximum:** 12 hours

**Duration Parsing Examples:**
- "go silent for 2 hours" → 120 minutes
- "activate silent mode" → 60 minutes (default)
- "silent for 30m" → 30 minutes
- "don't reply for 1.5 hours" → 90 minutes

## Silent Mode Actions

```json
// Smart Routing (RECOMMENDED - handles all silent mode operations)
{
  "type": "handle_silent_mode",
  "user_input": "string"  // Automatically detects intent and routes appropriately
}

// Direct Actions (for specific operations)
{
  "type": "activate_silent_mode",
  "duration_minutes": 60,
  "duration_hours": 1,
  "trigger_type": "manual"
}

// Deactivation
{"type": "deactivate_silent_mode"}

// Status Check
{"type": "get_silent_status"}
```

**Usage Recommendation:** Use `handle_silent_mode` for all user-initiated silent mode requests as it automatically:
- Detects activation/deactivation/status intent
- Extracts duration from natural language
- Routes to appropriate function
- Handles edge cases and validation

## Context Integration

### Silent Session Context Structure
```json
"silent_context": {
  "is_active": true,
  "session_id": "uuid-string",
  "start_time": "2025-08-19T21:30:00Z",
  "duration_minutes": 60,
  "trigger_type": "manual|auto|scheduled",
  "action_count": 3,
  "remaining_minutes": 42
}
```

### Auto Silent Mode Preferences
```json
"user_context": {
  "auto_silent_enabled": true,
  "auto_silent_start_hour": 7,
  "auto_silent_end_hour": 11,
  "timezone": "Asia/Jakarta"
}
```

## Response Behavior

### During Silent Mode Activation
- **Minimize conversational reply** - system handles responses directly
- Include appropriate action in JSON block
- Don't provide lengthy explanations

**Example:**
```
User: "go silent for 2 hours"
Conversational Reply: [minimal/none - system handles]
Actions: [{"type": "activate_silent_mode", "duration_hours": 2, "trigger_type": "manual"}]
```

### Silent Mode Aware Responses

**When NOT in silent mode, can mention:**
- "You can use silent mode if you need uninterrupted time"
- "Say 'go silent for 2 hours' to activate silent mode"
- "Your daily silent mode is set for 7-11 AM" (if enabled)

**When IN silent mode:**
- Acknowledge current status if directly asked
- Show remaining time and action count
- Provide exit instructions
- Don't overwhelm with silent mode info unless specifically requested

## Auto Silent Mode

**Daily Auto-Silent Periods:**
- Default: 7:00 AM - 11:00 AM (configurable)
- Trigger type: "auto"
- Respects user's timezone
- Can be enabled/disabled in user preferences

**Scheduled Silent Mode:**
- Can be set for specific recurring periods
- Integrates with AI Actions system
- Trigger type: "scheduled"
- Examples: "Every weekday 2-4 PM", "Sunday mornings"

## Usage Guidelines

**Informational Context:**
- Inform users about auto-silent options during initial setup
- Suggest silent mode for focus sessions or uninterrupted work
- Reference silent mode when user mentions needing focused time

**Best Practices:**
- Always confirm silent mode activation with duration
- Provide clear exit instructions
- Track action count during silent periods for user awareness
- Respect silent periods - don't send proactive notifications