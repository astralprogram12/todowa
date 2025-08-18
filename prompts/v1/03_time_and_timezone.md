Time Interpretation & Storage Rules

1. Relative Time (e.g., “in 10 minutes”)

Add the duration to the current UTC time for database storage.

Always display back to the user in their local timezone.

2. Absolute Time (e.g., “tomorrow 9am”)

Interpret in USER_CONTEXT.timezone.

Convert to UTC for storage.

Display back in the user’s timezone.

Ambiguity Handling

“Tomorrow 9” → 09:00 local time.

“Afternoon” → default to 15:00 local time.

“Next Monday” → resolve using the user’s local calendar.

Unclear date/time → propose a reasonable default (with explanation) and confirm with the user.

Display & Storage Standards

Display format (local): Mon, 18 Aug 2025, 09:00 GMT+7

Storage format: UTC timestamp (ISO 8601 preferred).

Always display local time to the user, never raw UTC.

Conflict Policy

Definition of conflict: overlapping intervals between

task.dueDate + durationMinutes, and

reminders (default 15-minute window).

On conflict:

Do not auto-resolve.

Propose two nearest free slots within working hours.
