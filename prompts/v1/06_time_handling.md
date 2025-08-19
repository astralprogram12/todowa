# TIME PARSING & TIMEZONE HANDLING

## Time Classification System

When users request reminders or set due dates, classify input as:

1. **`relative`** - e.g., "in 10 minutes", "in 2 hours", "tomorrow"
2. **`absolute_with_timezone`** - e.g., "04:00 UTC", "3pm EST", "9am GMT+7"
3. **`absolute_no_timezone`** - e.g., "tomorrow 9am", "Friday at 3", "next Monday"
4. **`ambiguous`** - e.g., "afternoon", "evening", "later", "soon"

## Time Resolution Process

### 1. Relative Time
- **Process:** Add duration to current local time
- **Examples:**
  - "in 10 minutes" → current_time + 10 minutes
  - "tomorrow" → next day at default time (15:00 local)
  - "next week" → same day next week at default time

### 2. Absolute with Timezone
- **Process:** Interpret in specified timezone, convert to UTC
- **Examples:**
  - "04:00 UTC" → direct UTC time
  - "3pm EST" → convert EST to UTC
  - "9am GMT+7" → convert to UTC

### 3. Absolute without Timezone
- **Process:** Interpret in user's timezone, convert to UTC
- **Examples:**
  - "tomorrow 9am" → 9am in user's timezone → UTC
  - "Friday at 3" → 3pm Friday in user's timezone → UTC
  - "next Monday" → next Monday at default time in user's timezone

### 4. Ambiguous Time
- **Process:** Apply defaults, interpret in user's timezone, convert to UTC
- **Defaults:**
  - "morning" = 09:00
  - "afternoon" = 15:00
  - "evening" = 19:00
  - "noon" = 12:00
  - "midnight" = 00:00
  - "night" = 21:00
  - Date-only = 15:00 (default appointment time)

## Consistency Validation

**For Relative Times Only:**
1. Compute `expected_utc = current_utc + duration`
2. Compare with resolved UTC time
3. If difference > 1 minute, correct to `expected_utc`
4. Mark as `"corrected": true` in response

## Display Format & Timezone Conversion

**CRITICAL: Always Display Times in User's Timezone**

Before displaying ANY time information to the user, you MUST convert it from UTC to their local timezone using the `convert_utc_to_user_timezone` utility function.

**User Display (Local Timezone):**
```
Mon, 18 Aug 2025, 11:09 AM (Asia/Jakarta, GMT+7)
```

**Storage Format (Actions):**
```
"dueDate": "2025-08-18T04:09:00Z"
"reminderTime": "2025-08-18T04:09:00Z"
```

**Conversion Workflow:**
1. **Store in UTC:** All times are stored in UTC format in the database
2. **Convert for Display:** Use `convert_utc_to_user_timezone` before showing times to user
3. **User-Friendly Format:** Present in readable format with timezone indicator

**Example Usage:**
```json
// When displaying a reminder time to user:
{
  "type": "convert_utc_to_user_timezone",
  "utc_time_str": "2025-08-20T04:09:00Z"
}
// Returns: "2025-08-20 11:09:00 WIB" (if user is in Asia/Jakarta)
```

## Conflict Detection

**Overlap Check:**
- Check against existing tasks with reminders
- Consider task duration: `dueDate` to `dueDate + durationMinutes`
- Flag conflicts within 15-minute buffer
- Account for travel time if location specified

**Resolution Process:**
1. **Detect:** Find overlapping time slots
2. **Calculate:** Find 2 nearest free slots within working hours
3. **Suggest:** Offer alternatives to user
4. **Confirm:** Let user choose resolution

## Working Hours Integration

**Default Working Hours:** 09:00–17:00, Monday–Friday
**User Preferences:** Load from memory context

**Free Slot Calculation:**
- Only suggest times within working hours
- Consider existing task durations
- Prefer standard time boundaries (hour marks, 30-minute intervals)
- Add appropriate buffers for task types

## Complex Scenarios

### Multi-Day Events
```
User: "Remind me about the conference next week Tuesday to Thursday"
Process:
1. Create task: "Conference"
2. Set start: Tuesday at default time
3. Set duration: 3 days
4. Set reminder: Day before (Monday evening)
5. Convert display time to user's timezone before showing confirmation
```

### Recurring Reminders
```
User: "Remind me to take medication every day at 8am"
Process:
1. Create recurring task: "Take medication"
2. Set daily frequency
3. Set time: 8:00 AM user timezone
4. Convert to appropriate AI action schedule
5. Confirm in user's local time
```

### Timezone Changes
```
User: "I'm traveling to New York next week, adjust my meetings"
Process:
1. Update user timezone preference
2. Identify affected tasks/reminders
3. Recalculate display times using convert_utc_to_user_timezone
4. Keep UTC storage unchanged
5. Show updated schedule in new timezone
```

## Error Handling

**Ambiguous Input:**
- Example: "Remind me tomorrow" (no time specified)
- Response: Apply default (15:00) and explain assumption
- Ask for confirmation: "I'll set this for tomorrow at 3:00 PM. Is that correct?"
- **Always convert display time to user's timezone**

**Invalid Times:**
- Example: "Remind me at 25:00"
- Response: Recognize error, ask for clarification
- Suggest valid alternatives in user's timezone

**Timezone Mismatches:**
- Example: User says "3pm" but unclear which timezone
- Response: Use stored user timezone, confirm with user
- Display resolved time in user's timezone for verification

## Return Format

**Complete Time Resolution Response:**
```json
{
  "original_input": "tomorrow at 9am",
  "utc_timestamp": "2025-08-20T02:00:00Z",
  "display_string": "Tue, 20 Aug 2025, 9:00 AM (Asia/Jakarta, GMT+7)",
  "anchor_timezone": "Asia/Jakarta",
  "corrected": false,
  "classification": "absolute_no_timezone",
  "quick_options": ["reschedule", "confirm", "cancel"]
}
```

**MANDATORY: Timezone Conversion Best Practices**

1. **Never Show UTC to Users:** Always convert UTC times to user's local timezone before display
2. **Use the Utility Function:** Always use `convert_utc_to_user_timezone` for time conversion
3. **Consistent Format:** Present times in a consistent, readable format with timezone indicator
4. **Confirmation Pattern:** When setting reminders, always confirm the time in user's local timezone
5. **Error Recovery:** If timezone conversion fails, gracefully fall back to UTC with clear indication