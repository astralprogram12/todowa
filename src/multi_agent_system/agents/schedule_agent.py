#!/usr/bin/env python3
"""
Schedule Agent - Intelligent Scheduler for Future and Recurring Actions (V4 - Querying & Summaries)

This agent serves as a unified, intelligent scheduler for any conceivable
time-based action, from simple reminders to complex, recurring AI-driven tasks.

### NEW IN THIS VERSION ###
- **Find Specific Schedules**: Now supports a 'find_schedule' intent to answer user
  queries about specific schedules (e.g., "when is my swimming lesson?").
- **Daily Summary Action**: Added a new 'daily_summary' action type that can be scheduled
  to provide the user with a daily overview of their tasks and schedules.
- **Full Schedule Management (CRUD)**: Supports creating, listing, finding, updating, and deleting schedules.
- **Intelligent Search**: For find/update/delete commands, the agent fetches all of the user's
  schedules and uses a targeted AI call to find the best match for a natural language query.
- **Hardcoded Safety Limit**: To prevent abuse, the agent is hardcoded to allow a
  maximum of 10 active schedules per user.

### CORE FEATURES ###
- **Hybrid Parsing Engine**: Uses a fast, local library for simple dates and falls back to
  a powerful AI call for complex, recurring schedules.
- **Flexible Action System**: Schedules actions like `send_notification`, `create_task`,
  `daily_summary`, and the powerful `execute_prompt`.
- **Timezone Aware**: All schedule parsing is done with respect to the user's local timezone.
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

# This library is used for the fast, manual parsing of simple dates.
import dateparser

logger = logging.getLogger(__name__)

ISO_UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
MAX_SCHEDULES_PER_USER = 10

class ScheduleAgent:
    def __init__(self, ai_model=None, supabase=None, api_key_manager=None):
        self.ai_model = ai_model
        self.supabase = supabase # The agent needs direct Supabase access for internal checks
        self.api_key_manager = api_key_manager
        self.last_api_call = 0
        self.rate_limit_seconds = 2

    def process_command(self, user_command: str, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.ai_model or not self.supabase:
            return self._error_response("Schedule Agent is not properly initialized.")

        try:
            user_id = user_context.get('user_info', {}).get('user_id')
            if not user_id: return self._error_response("User ID is required.")

            intent_details = self._determine_schedule_intent(user_command, user_context)
            intent = intent_details.get('intent', 'unknown')

            if intent == 'create_schedule':
                return self._handle_create_schedule(user_id, intent_details, user_context)
            elif intent == 'list_schedules':
                return self._handle_list_schedules()
            elif intent == 'find_schedule':
                return self._handle_find_schedule(user_id, intent_details)
            elif intent == 'update_schedule':
                return self._handle_schedule_modification(user_id, intent_details, 'update')
            elif intent == 'delete_schedule':
                return self._handle_schedule_modification(user_id, intent_details, 'delete')
            else:
                return self._error_response("I'm not sure how to handle that schedule request. Please try creating, listing, or canceling a schedule.")

        except Exception as e:
            logger.exception(f"Schedule Agent processing failed: {e}")
            return self._error_response("An error occurred while managing your schedules.")

    # --- Intent Handling Methods ---

    def _handle_create_schedule(self, user_id: str, intent_details: Dict, user_context: Dict) -> Dict:
        active_schedules = self._get_all_user_schedules(user_id)
        if len(active_schedules) >= MAX_SCHEDULES_PER_USER:
            return self._error_response(f"You have reached the maximum of {MAX_SCHEDULES_PER_USER} active schedules.")

        if not intent_details.get("is_valid", True):
            return self._error_response(intent_details.get("reason", "That schedule is not valid."))

        schedule_data = self._parse_schedule_string(intent_details['schedule_str'], user_context)
        if not schedule_data:
            return self._error_response("I couldn't figure out the exact time for that schedule.")

        action = {
            'type': 'create_schedule',
            'action_type': intent_details['action_type'],
            'action_payload': intent_details['action_payload'],
            'schedule_type': schedule_data['schedule_type'],
            'schedule_value': schedule_data['schedule_value'],
            'timezone': user_context.get('user_info', {}).get('timezone', 'UTC'),
            'next_run_at': schedule_data['next_run_at']
        }
        
        return {'success': True, 'actions': [action], 'response': "Okay, I've scheduled that for you!"}

    def _handle_list_schedules(self) -> Dict:
        action = {'type': 'get_schedules', 'status': 'active'}
        return {'success': True, 'actions': [action], 'response': "Let me get a list of your active schedules..."}

    def _handle_find_schedule(self, user_id: str, intent_details: Dict) -> Dict:
        """Finds a single schedule and returns its details in a friendly format."""
        query = intent_details.get('schedule_description')
        if not query:
            return self._error_response("Which schedule are you looking for?")

        schedules = self._get_all_user_schedules(user_id)
        if not schedules:
            return self._error_response("You don't have any active schedules to look for.")

        match_id = self._find_best_schedule_match(query, schedules)
        if not match_id:
            return self._error_response(f"I couldn't find a schedule matching '{query}'.")

        matched_schedule = next((s for s in schedules if s['id'] == match_id), None)

        if matched_schedule:
            payload = matched_schedule.get('action_payload', {})
            action_desc = payload.get('message', payload.get('title', matched_schedule.get('action_type', 'unnamed')))
            status = matched_schedule.get('status', 'unknown')

            if matched_schedule.get('schedule_type') == 'cron':
                time_desc = f"It's a recurring schedule set to: `{matched_schedule.get('schedule_value')}`."
            else:
                time_desc = f"It's a one-time schedule set for {matched_schedule.get('next_run_at')} (UTC)."

            response_message = f"I found it! Your schedule for '{action_desc}'.\n{time_desc}\nIts status is currently '{status}'."
            return {'success': True, 'actions': [], 'response': response_message}

        return self._error_response(f"I found a match but couldn't retrieve the details for '{query}'.")

    def _handle_schedule_modification(self, user_id: str, intent_details: Dict, mode: str) -> Dict:
        query = intent_details.get('schedule_description')
        if not query: return self._error_response(f"Which schedule would you like to {mode}?")

        schedules = self._get_all_user_schedules(user_id)
        if not schedules: return self._error_response("You don't have any active schedules to modify.")

        match_id = self._find_best_schedule_match(query, schedules)
        if not match_id: return self._error_response(f"I couldn't find a schedule matching '{query}'.")

        if mode == 'delete':
            action = {'type': 'delete_schedule', 'schedule_id': match_id}
            return {'success': True, 'actions': [action], 'response': "Okay, I've cancelled that schedule."}
        
        if mode == 'update':
            patch = intent_details.get('patch', {})
            if not patch: return self._error_response("What would you like to change about the schedule?")
            action = {'type': 'update_schedule', 'schedule_id': match_id, 'patch': patch}
            return {'success': True, 'actions': [action], 'response': "Okay, I'll update that schedule."}
        
        return self._error_response("Unknown modification request.")

    # --- AI-Powered, Hybrid, and DB Helper Methods ---

    def _determine_schedule_intent(self, user_command: str, user_context: Dict) -> Optional[Dict]:
        prompt = self._build_schedule_intent_prompt(user_command)
        response_text = self._make_ai_request_sync(prompt)
        try:
            return json.loads(response_text.strip().replace('```json', '').replace('```', ''))
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Could not parse schedule intent. Response: {response_text}")
            return {'intent': 'unknown'}

    def _parse_schedule_string(self, schedule_str: str, user_context: Dict) -> Optional[Dict]:
        user_timezone = user_context.get('user_info', {}).get('timezone', 'UTC')
        try:
            recurring_keywords = ['every', 'each', 'daily', 'weekly', 'monthly', 'annually']
            if not any(keyword in schedule_str.lower() for keyword in recurring_keywords):
                parsed_date = dateparser.parse(schedule_str, settings={'TIMEZONE': user_timezone, 'RETURN_AS_TIMEZONE_AWARE': True})
                if parsed_date:
                    utc_date = parsed_date.astimezone(timezone.utc)
                    timestamp_str = utc_date.strftime(ISO_UTC_FORMAT)
                    return {"schedule_type": "one_time", "schedule_value": timestamp_str, "next_run_at": timestamp_str}
        except Exception:
            pass # Fallback to AI

        prompt = self._build_schedule_parsing_prompt(schedule_str, user_context)
        response_text = self._make_ai_request_sync(prompt)
        try:
            data = json.loads(response_text.strip().replace('```json', '').replace('```', ''))
            return data if 'schedule_value' in data and 'next_run_at' in data else None
        except (json.JSONDecodeError, TypeError):
            return None

    def _find_best_schedule_match(self, query: str, schedules: List[Dict]) -> Optional[str]:
        prompt = self._build_find_schedule_prompt(query, schedules)
        response_text = self._make_ai_request_sync(prompt)
        try:
            data = json.loads(response_text.strip().replace('```json', '').replace('```', ''))
            return data.get('match_id')
        except (json.JSONDecodeError, TypeError):
            return None

    def _get_all_user_schedules(self, user_id: str) -> List[Dict]:
        try:
            res = self.supabase.table("scheduled_actions").select("*").eq("user_id", user_id).eq("status", "active").execute()
            return res.data if res.data else []
        except Exception as e:
            logger.error(f"Failed to fetch user schedules internally: {e}")
            return []

    # --- Shared Helper Methods ---
    def _make_ai_request_sync(self, prompt: str) -> Optional[str]:
        if not self.ai_model: return None
        try:
            self._enforce_rate_limit()
            response = self.ai_model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.exception(f"AI request failed in ScheduleAgent: {e}")
            return None

    def _enforce_rate_limit(self):
        time_since_call = time.time() - self.last_api_call
        if time_since_call < self.rate_limit_seconds:
            time.sleep(self.rate_limit_seconds - time_since_call)
        self.last_api_call = time.time()
        
    def _error_response(self, message: str) -> Dict[str, Any]:
        return {'success': False, 'actions': [], 'response': f"❌ {message}", 'error': message}

    # --- Prompt Templates ---

    def _build_schedule_intent_prompt(self, user_command: str) -> str:
        return f"""You are an expert at analyzing user commands for a scheduling system. Your goal is to determine the user's intent and extract all necessary details into a single, structured JSON object.

**User Command:** "{user_command}"

---
### 1. Possible Intents
You must choose one of the following for the `intent` key:
- `create_schedule`: For any new one-time or recurring action.
- `list_schedules`: When the user wants to see their existing schedules.
- `find_schedule`: When the user is asking for details about a specific schedule.
- `update_schedule`: When the user wants to change an existing schedule.
- `delete_schedule`: When the user wants to cancel or remove an existing schedule.

---
### 2. CRITICAL SAFETY RULE FOR RECURRING SCHEDULES
- This rule **ONLY** applies to schedules that repeat (using words like 'every', 'each', 'daily').
- If a **recurring** schedule is more frequent than once per day (e.g., "every hour"), you **MUST** set `"is_valid": false` and provide a clear reason.
- **One-time schedules (e.g., "in 20 minutes") are ALWAYS valid.**

---
### 3. Extraction Logic & Details

**A. For `intent: "create_schedule"`:**
- `is_valid`: (boolean) Must be `false` if the safety rule is violated.
- `reason`: (string) If invalid, explain why.
- `action_type`: (string) Choose ONE of `send_notification`, `create_task`, `execute_prompt`, or `daily_summary`.
- `action_payload`: (JSON object) The payload for the action. For `daily_summary`, this is an empty object `{{}}`.
- `schedule_str`: (string) The natural language description of the schedule (e.g., "every morning at 8am").

**B. For `intent: "list_schedules"`:**
- No other details are needed.

**C. For `intent: "find_schedule"`, `intent: "update_schedule"`, or `intent: "delete_schedule"`:**
- `schedule_description`: (string) The user's description of the schedule to find.
- `patch`: (JSON object) For `update_schedule` only, this contains the changes.

---
### 4. EXAMPLES (Follow these patterns closely)

- **Command:** "remind me to take a bath in 1 hour"
  **Response:** `{{"intent": "create_schedule", "is_valid": true, "action_type": "send_notification", "action_payload": {{"message": "Take a bath"}}, "schedule_str": "in 1 hour"}}`

- **Command:** "schedule a work task to prepare the weekly report every Friday morning"
  **Response:** `{{"intent": "create_schedule", "is_valid": true, "action_type": "create_task", "action_payload": {{"title": "Prepare Weekly Report", "description": "Compile and send the weekly performance report.", "category": "work", "priority": "medium"}}, "schedule_str": "every Friday morning"}}`

- **Command:** "send me my daily summary every morning at 8am"
  **Response:** `{{"intent": "create_schedule", "is_valid": true, "action_type": "daily_summary", "action_payload": {{}}, "schedule_str": "every morning at 8am"}}`

- **Command:** "when is my swimming schedule?"
  **Response:** `{{"intent": "find_schedule", "schedule_description": "swimming schedule"}}`

- **Command:** "cancel my daily poem reminder"
  **Response:** `{{"intent": "delete_schedule", "schedule_description": "my daily poem reminder"}}`

- **Command:** "show me my schedules"
  **Response:** `{{"intent": "list_schedules"}}`

- **Command:** "run a check every hour"
  **Response:** `{{"intent": "create_schedule", "is_valid": false, "reason": "For your safety, I can only schedule actions that occur daily or less frequently."}}`

---
Now, analyze the "{user_command}" and respond with ONLY a valid JSON object.
"""

    def _build_schedule_parsing_prompt(self, schedule_str: str, user_context: Dict) -> str:
        current_utc = datetime.now(timezone.utc).isoformat()
        user_timezone = user_context.get('user_info', {}).get('timezone', 'UTC')
        return f"""You are a schedule parsing expert. Convert the user's natural language schedule into a structured JSON object.

**User's Schedule Request:** "{schedule_str}"
**Current UTC Time:** {current_utc}
**User's Timezone:** {user_timezone}

**Instructions:**
1.  **Determine `schedule_type`**: `one_time` or `cron`.
2.  **Determine `schedule_value`**: A UTC timestamp for `one_time`, or a CRON string for `cron`.
3.  **Calculate `next_run_at`**: The next UTC timestamp this schedule should run.

Respond with ONLY a valid JSON object with `schedule_type`, `schedule_value`, and `next_run_at` keys.
"""

    def _build_find_schedule_prompt(self, query: str, schedules: List[Dict]) -> str:
        formatted_schedules = []
        for s in schedules:
            payload_desc = json.dumps(s.get('action_payload', {}))
            schedule_desc = s.get('schedule_value', '')
            if s.get('schedule_type') == 'cron':
                schedule_desc = f"repeats on a schedule of '{schedule_desc}'"
            else:
                schedule_desc = f"runs once at '{schedule_desc}'"

            formatted_schedules.append(
                f"ID: {s['id']}\nAction: {s['action_type']}\nPayload: {payload_desc}\nSchedule: {schedule_desc}"
            )
        
        schedule_list_str = "\n---\n".join(formatted_schedules)

        return f"""You are an expert at matching a user's request to a list of their existing schedules.

**User's Request:** "I want to find the schedule related to: {query}"

**List of User's Active Schedules:**
---
{schedule_list_str}
---

**Your Task:**
Analyze the user's request and the list of schedules. Identify the single best match. Consider the action, the payload content, and the schedule description.

Respond with ONLY a valid JSON object with a single key, "match_id", containing the exact ID of the best matching schedule. If no schedule is a good match, the value should be null.

Example Response:
`{{"match_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef"}}`
"""