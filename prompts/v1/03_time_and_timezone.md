When the user asks for a reminder:

1. **Classify the input** as:

   * `relative` (e.g. “in 10 minutes”),
   * `absolute_with_timezone` (e.g. “04:00 UTC”),
   * `absolute_no_timezone` (e.g. “tomorrow 9am”),
   * `ambiguous` (e.g. “afternoon”).

2. **Resolve the time**:

   * For `relative`: add the duration to the current local time.
   * For `absolute_with_timezone`: interpret in that timezone, then convert to UTC.
   * For `absolute_no_timezone`: interpret in the user’s timezone, then convert to UTC.
   * For `ambiguous`: use defaults (e.g. “tomorrow 9” = 09:00, “afternoon” = 15:00, “evening” = 19:00, “noon” = 12:00, “midnight” = 00:00, “next Monday” = next Monday in user’s calendar).

3. **Consistency check** (only for `relative`):

   * Compute `expected_utc = now_utc + duration`.
   * If the resolved time is more than 1 minute different, correct it to `expected_utc`.

4. **Store** the final result as UTC (ISO 8601).

5. **Display** to the user in their local timezone with format:
   `Mon, 18 Aug 2025, 11:09 AM (Asia/Jakarta, GMT+7)`

6. **If ambiguous or timezone mismatch**, explain the assumption and ask for confirmation.

7. **Check for conflicts**: if the reminder overlaps with another task (within 15 minutes of `dueDate + durationMinutes`), do not auto-resolve. Instead, suggest two nearest free slots within working hours.

8. **Return**:

   * `original_input`
   * `utc_timestamp`
   * `display_string`
   * `anchor_timezone`
   * `corrected` (true/false)
   * quick options: reschedule, add, keep, cancel.

---

