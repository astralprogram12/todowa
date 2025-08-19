# COMPLETE ACTION SCHEMA

## Classification (Always First)
```json
{
  "type": "classification",
  "label": "task|reminder|memory|journal|guide|chat|expert",
  "confidence": 0.0,
  "precedence_note": "user > explicit context > stored memory > inference"
}
```

## Task Management
```json
// Create new task
{
  "type": "add_task",
  "title": "string",
  "notes?": "string",
  "dueDate?": "YYYY-MM-DDTHH:MM:SSZ",
  "priority?": "low|medium|high",
  "category?": "string",
  "tags?": ["string"],
  "url?": "string",
  "difficulty?": "easy|medium|hard",
  "estimateMinutes?": 0
}

// Update existing task
{
  "type": "update_task",
  "titleMatch": "string",
  "idMatch?": "string",
  "patch": {
    "title?": "string",
    "notes?": "string",
    "dueDate?": "YYYY-MM-DDTHH:MM:SSZ",
    "priority?": "low|medium|high",
    "category?": "string",
    "tags?": ["string"],
    "estimateMinutes?": 0,
    "difficulty?": "easy|medium|hard"
  }
}

// Task completion and deletion
{ "type": "complete_task", "titleMatch": "string" }
{ "type": "delete_task", "titleMatch": "string", "requiresConfirmation?": true }
```

## Reminder Management
```json
// Reminders are now FULLY AUTOMATED - system automatically creates task if needed!
// ENHANCED: If no matching task exists, these actions will automatically:
// 1. Create the task first using the titleMatch as the task title
// 2. Then set/update the reminder on that newly created task

{ "type": "set_reminder", "titleMatch": "string", "reminderTime": "YYYY-MM-DDTHH:MM:SSZ" }
{ "type": "update_reminder", "titleMatch": "string", "newReminderTime": "YYYY-MM-DDTHH:MM:SSZ" }
{ "type": "delete_reminder", "titleMatch": "string" }
{ "type": "snooze_reminder", "titleMatch": "string", "newReminderTime": "YYYY-MM-DDTHH:MM:SSZ" }

// SIMPLIFIED WORKFLOW: No need to manually check task existence!
// Old complex pattern (NO LONGER NEEDED):
// ❌ 1. Check if task exists
// ❌ 2. If not found: add_task first
// ❌ 3. Then: set_reminder
//
// New simplified pattern (RECOMMENDED):
// ✅ Just use set_reminder directly - it handles everything automatically!
```

## Knowledge Management
```json
// Memories (user-specific, always loaded)
{ "type": "add_memory", "title": "string", "content": "string?", "category": "string?" }
{ "type": "search_memories", "query": "string" }
{ "type": "update_memory", "titleMatch": "string", "patch": { "title?": "string", "content?": "string" } }
{ "type": "delete_memory", "titleMatch": "string" }

// Journal (general knowledge, contextually loaded)
{ "type": "add_journal", "title": "string", "content": "string?", "category": "string?" }
{ "type": "search_journals", "query": "string" }
{ "type": "update_journal", "titleMatch": "string", "patch": { "title?": "string", "content?": "string", "category?": "string" } }
{ "type": "delete_journal", "titleMatch": "string" }
```

## AI Automation
```json
{
  "type": "schedule_ai_action",
  "action_type": ["create_recurring_task", "task_for_day", "summary_of_day", "ai_action_helper"],
  "description": "string",
  "schedule": {
    "frequency": ["DAILY", "WEEKLY", "MONTHLY", "HOURLY"],
    "by_day?": ["MO"],
    "at_time": "HH:MM",
    "timezone?": "string",
    "start_date?": "YYYY-MM-DD",
    "end_date?": "YYYY-MM-DD"
  },
  "payload?": { "title?": "string" }
}
{ "type": "update_ai_action", "descriptionMatch": "string", "patch": { "description?": "string", "schedule?": {} } }
{ "type": "delete_ai_action", "descriptionMatch": "string" }
```

## Silent Mode
```json
{ "type": "activate_silent_mode", "duration_minutes?": "number", "duration_hours?": "number", "trigger_type?": "manual|auto" }
{ "type": "deactivate_silent_mode" }
{ "type": "get_silent_status" }
```

## AI Interactions
```json
{ "type": "guide", "topic?": "string" }
{ "type": "chat", "message": "string", "context?": "string" }
{ "type": "expert", "topic?": "string", "context?": "string" }
```

## Utility Functions
```json
// NEW: Timezone conversion for user-friendly time display
// Use this when displaying times to ensure they appear in user's local timezone
{ "type": "convert_utc_to_user_timezone", "utc_time_str": "YYYY-MM-DDTHH:MM:SSZ" }

// NEW: AI confusion helper - Use ONLY when genuinely confused about content classification
// This tool helps determine whether content should be stored as task, memory, journal, etc.
// IMPORTANT: Only call this when the AI cannot clearly determine the appropriate storage type
{
  "type": "ai_confusion_helper",
  "content_description": "string",
  "user_input?": "string",
  "context_hint?": "string"
}
```