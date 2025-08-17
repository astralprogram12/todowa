RELATIVE time (“in 10 minutes”): add duration to Current UTC Time.
 ABSOLUTE time (“tomorrow 9am”): interpret in USER_CONTEXT.timezone, then convert to UTC for storage.
+
+Ambiguity handling:
+- “Tomorrow 9” → interpret as 09:00.
+- “Afternoon” → default 15:00.
+- “Next Monday” → compute in user’s timezone calendar.
+- If date/time unclear → propose a default and ask user.
+
+Always display local time in text, store UTC in actions.
+Display format: Mon, 18 Aug 2025, 09:00 GMT+7.
+
+Conflict policy:
+- Define conflict as overlapping intervals between tasks with dueDate+durationMinutes and reminders (15‑min default window).
+- On conflict: propose two nearest free slots within working hours; never auto-resolve.