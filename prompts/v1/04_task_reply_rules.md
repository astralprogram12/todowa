 If user omits category/tags/difficulty/notes when adding a task, infer them and tell the user.
+
+Inference rules:
+- Auto-assign category using classification keywords (Meeting, Finance, Writing, Errand, Personal).
+- Auto-assign default durationMinutes (Meeting=30, Call=25, Errand=45, Deep work=90).
+- Set priority=high if deadline is within 24h.
+- Always summarize what was inferred and offer undo.