# Silent Mode Feature Testing Guide

## Overview
This document provides comprehensive test cases for the Silent Mode feature implementation.

## Test Cases

### 1. Manual Silent Mode Activation

**Test 1.1: Basic Activation**
- Input: "go silent for 2 hours"
- Expected: 
  - Silent session created with 120 minutes duration
  - Activation message sent
  - Subsequent messages accumulated, not replied to

**Test 1.2: Different Duration Formats**
- Input: "don't reply for 30 minutes"
- Expected: 30-minute silent session
- Input: "silent for 1 hour"
- Expected: 60-minute silent session

**Test 1.3: Default Duration**
- Input: "go silent"
- Expected: 60-minute silent session (default)

**Test 1.4: Invalid Durations**
- Input: "go silent for 15 hours"
- Expected: Error message (exceeds 12-hour limit)
- Input: "go silent for 2 minutes"
- Expected: Error message (below 5-minute minimum)

### 2. Message Accumulation During Silent Mode

**Test 2.1: Message Storage**
- Setup: Activate silent mode
- Input: "add task: buy groceries"
- Expected: 
  - No immediate reply
  - Action stored in accumulated_actions
  - Action count incremented

**Test 2.2: Multiple Actions**
- Setup: Active silent mode
- Inputs: 
  - "add task: call mom"
  - "set reminder for tomorrow 3pm"
  - "add memory: great restaurant downtown"
- Expected: All actions accumulated, no replies sent

### 3. Silent Mode Deactivation

**Test 3.1: Manual Exit**
- Setup: Active silent mode with accumulated actions
- Input: "exit silent mode"
- Expected:
  - Silent session ended
  - Comprehensive summary sent
  - Normal operation resumed

**Test 3.2: Alternative Exit Commands**
- Inputs: "end silent mode", "stop silent mode", "deactivate silent"
- Expected: All should work to exit silent mode

**Test 3.3: Exit When Not Silent**
- Input: "exit silent mode" (when not in silent mode)
- Expected: "You're not currently in silent mode" message

### 4. Automatic Silent Mode Expiration

**Test 4.1: Session Expiration**
- Setup: Create 5-minute silent session
- Wait: 6 minutes
- Expected: 
  - Session automatically ended
  - Summary sent via scheduler
  - Normal operation resumed

### 5. Daily Auto Silent Mode (7-11 AM)

**Test 5.1: Auto Activation**
- Setup: User timezone at 07:00
- Expected:
  - Silent session created automatically
  - 4-hour duration (7-11 AM)
  - Activation notification sent

**Test 5.2: Auto Deactivation**
- Setup: Auto silent session active
- Time: 11:00 in user timezone
- Expected:
  - Session ended automatically
  - Summary sent

**Test 5.3: Disabled Auto Silent**
- Setup: User has auto_silent_enabled = false
- Time: 07:00 in user timezone
- Expected: No automatic activation

### 6. Silent Mode Status Checking

**Test 6.1: Status When Active**
- Setup: Active silent session with 2 hours remaining
- Input: "am I in silent mode?"
- Expected: Status message with remaining time and action count

**Test 6.2: Status When Inactive**
- Input: "silent mode status" (when not in silent mode)
- Expected: "Silent mode is currently off" message

### 7. Summary Generation

**Test 7.1: Comprehensive Summary**
- Setup: Silent session with various accumulated actions:
  - 3 tasks added
  - 2 reminders set
  - 1 memory added
- Expected: Summary showing:
  - Total duration
  - Action count by type
  - "You're back online" message

**Test 7.2: Empty Summary**
- Setup: Silent session with no accumulated actions
- Expected: "No actions were taken during this silent period" message

### 8. Edge Cases and Error Handling

**Test 8.1: Multiple Activation Attempts**
- Setup: Already in silent mode
- Input: "go silent for 1 hour"
- Expected: Previous session ended, new session created

**Test 8.2: Database Errors**
- Setup: Simulate database connection issues
- Expected: Graceful error handling, user notified

**Test 8.3: Concurrent Sessions**
- Test: Multiple users activating silent mode simultaneously
- Expected: Each user's session handled independently

### 9. Integration Tests

**Test 9.1: Scheduler Integration**
- Test: Cron job processing
- Expected: 
  - Expired sessions ended
  - Auto activations triggered
  - Summaries sent

**Test 9.2: WhatsApp Integration**
- Test: End-to-end flow via WhatsApp webhook
- Expected: All features work through messaging interface

## Test Environment Setup

### Database Schema
```sql
-- Apply migration
\i migrations/001_add_silent_mode.sql

-- Create test user
INSERT INTO user_whatsapp (user_id, phone, timezone) 
VALUES ('test-user-id', '+1234567890', 'America/New_York');
```

### Test Data
```python
# Test user configuration
test_user = {
    'user_id': 'test-user-id',
    'phone': '+1234567890',
    'timezone': 'America/New_York',
    'auto_silent_enabled': True,
    'auto_silent_start_hour': 7,
    'auto_silent_end_hour': 11
}
```

## Success Criteria

✅ All manual activation/deactivation commands work
✅ Message accumulation during silent mode
✅ Automatic session expiration
✅ Daily auto silent mode (7-11 AM)
✅ Comprehensive summary generation
✅ Status checking functionality
✅ Error handling for edge cases
✅ Scheduler integration
✅ WhatsApp webhook integration

## Performance Considerations

- Silent session queries should be optimized with indexes
- Expired session cleanup should run efficiently
- Summary generation should handle large action lists
- Concurrent user handling should not cause conflicts

## Security Considerations

- Silent sessions are user-isolated
- Accumulated actions are properly sanitized
- Exit commands are authenticated to the correct user
- Auto-activation respects user preferences
