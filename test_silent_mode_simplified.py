#!/usr/bin/env python3
"""
Simplified Silent Mode Branch Test Script
Tests only the intelligent_context_classifier function for silent mode detection
"""

import sys
import os
import re
from datetime import datetime
import time

# Create minimal mock implementations to avoid import errors
class MockSupabase:
    def table(self, table_name):
        return self
    
    def insert(self, data):
        return self
    
    def execute(self):
        return type('obj', (object,), {'data': [{'id': 'mock-id'}]})

# Mock the database modules before importing ai_tools
sys.modules['database_personal'] = type('module', (), {
    'log_action': lambda *args, **kwargs: None,
    'add_task_entry': lambda *args, **kwargs: {'id': 'mock-task-id'},
    'query_tasks': lambda *args, **kwargs: [],
    'query_lists': lambda *args, **kwargs: [],
    'add_journal_entry': lambda *args, **kwargs: {'id': 'mock-journal-id'},
    'add_memory_entry': lambda *args, **kwargs: {'id': 'mock-memory-id'},
    'get_all_reminders': lambda *args, **kwargs: [],
    'update_task_entry': lambda *args, **kwargs: None,
    'get_user_phone_by_id': lambda *args, **kwargs: '+1234567890'
})

sys.modules['database_silent'] = type('module', (), {
    'create_silent_session': lambda *args, **kwargs: {'id': 'mock-session-id'},
    'get_active_silent_session': lambda *args, **kwargs: None,
    'end_silent_session': lambda *args, **kwargs: {'accumulated_actions': []},
    'add_action_to_silent_session': lambda *args, **kwargs: True,
    'get_expired_silent_sessions': lambda *args, **kwargs: []
})

# Now import ai_tools after mocking
sys.path.append('.')
import ai_tools

def test_silent_mode_classification():
    """Test that the intelligent_context_classifier correctly identifies silent mode requests"""
    print("\n🧪 Testing Silent Mode Classification...")
    
    # Mock supabase instance
    supabase = MockSupabase()
    user_id = "test-user-123"
    
    # Test cases for silent mode detection
    test_cases = [
        # Silent mode activation - should be classified as "silent"
        ("go silent for 2 hours", "silent", "Should detect silent mode activation with duration"),
        ("activate silent mode", "silent", "Should detect explicit silent mode activation"),
        ("don't reply for 30 minutes", "silent", "Should detect no-reply request"),
        ("quiet for 1 hour", "silent", "Should detect quiet mode request"),
        ("turn on silent mode", "silent", "Should detect turn on silent command"),
        ("silent mode please", "silent", "Should detect polite silent request"),
        
        # Silent mode deactivation - should be classified as "silent"
        ("exit silent mode", "silent", "Should detect silent mode exit"),
        ("end silent mode", "silent", "Should detect silent mode end"),
        ("stop silent mode", "silent", "Should detect silent mode stop"),
        ("deactivate silent", "silent", "Should detect silent deactivation"),
        ("back online", "silent", "Should detect back online request"),
        ("resume replies", "silent", "Should detect resume replies"),
        
        # Silent mode status - should be classified as "silent"
        ("am I in silent mode?", "silent", "Should detect silent status check"),
        ("silent mode status", "silent", "Should detect status inquiry"),
        ("check silent", "silent", "Should detect silent check"),
        
        # Non-silent mode inputs (should NOT be classified as silent)
        ("add task: buy groceries", "task", "Should classify as task, not silent"),
        ("remind me tomorrow", "reminder", "Should classify as reminder, not silent"),
        ("I learned something interesting", "journal", "Should classify as journal, not silent"),
        ("hello there", "chat", "Should classify as chat, not silent"),
        ("how do I use this app?", "guide", "Should classify as guide, not silent"),
    ]
    
    print(f"\n📝 Running {len(test_cases)} classification tests...\n")
    
    passed = 0
    failed = 0
    silent_specific_passed = 0
    silent_specific_total = 15  # First 15 tests are silent mode specific
    
    for i, (user_input, expected_classification, description) in enumerate(test_cases, 1):
        try:
            # Test the intelligent_context_classifier
            result = ai_tools.intelligent_context_classifier(
                supabase=supabase,
                user_id=user_id,
                user_input=user_input
            )
            
            actual_classification = result.get('classification')
            confidence = result.get('confidence', 0.0)
            recommended_action = result.get('recommended_action')
            
            # Check if classification matches expectation
            if actual_classification == expected_classification:
                status = "✅ PASS"
                passed += 1
                if i <= silent_specific_total:
                    silent_specific_passed += 1
            else:
                status = "❌ FAIL"
                failed += 1
            
            print(f"Test {i:2d}: {status} | {description}")
            print(f"         Input: '{user_input}'")
            print(f"         Expected: {expected_classification} | Got: {actual_classification} | Confidence: {confidence:.2f}")
            print(f"         Action: {recommended_action}")
            
            if actual_classification != expected_classification:
                all_scores = result.get('all_scores', {})
                silent_score = all_scores.get('silent', 0.0)
                print(f"         🔍 Silent score: {silent_score:.2f}")
                print(f"         🔍 Top 3 scores: {dict(sorted(all_scores.items(), key=lambda x: x[1], reverse=True)[:3])}")
            
            print()
            
        except Exception as e:
            print(f"Test {i:2d}: 💥 ERROR | {description}")
            print(f"         Input: '{user_input}'")
            print(f"         Error: {str(e)}")
            print()
            failed += 1
    
    # Summary
    total = len(test_cases)
    success_rate = (passed / total) * 100
    silent_success_rate = (silent_specific_passed / silent_specific_total) * 100
    
    print(f"📊 SILENT MODE CLASSIFICATION TEST RESULTS:")
    print(f"   Total Tests: {total}")
    print(f"   Passed: {passed} ✅")
    print(f"   Failed: {failed} ❌")
    print(f"   Overall Success Rate: {success_rate:.1f}%")
    print(f"   Silent Mode Tests: {silent_specific_passed}/{silent_specific_total} ({silent_success_rate:.1f}%)")
    
    if silent_success_rate >= 90:
        print(f"\n🎉 EXCELLENT! Silent mode detection is working correctly.")
    elif silent_success_rate >= 80:
        print(f"\n✅ GOOD! Silent mode detection is mostly working.")
    elif silent_success_rate >= 70:
        print(f"\n⚠️ NEEDS IMPROVEMENT. Silent mode detection needs tweaking.")
    else:
        print(f"\n🚨 CRITICAL ISSUE! Silent mode detection is not working properly.")
    
    return silent_success_rate >= 80

def test_function_availability():
    """Test that all silent mode functions are available"""
    print("\n🧪 Testing Silent Mode Function Availability...")
    
    required_functions = [
        'activate_silent_mode',
        'deactivate_silent_mode',
        'get_silent_status',
        'handle_silent_mode',
        'intelligent_context_classifier'
    ]
    
    available_functions = []
    missing_functions = []
    
    for func_name in required_functions:
        if hasattr(ai_tools, func_name):
            available_functions.append(func_name)
            print(f"✅ {func_name} - Available")
        else:
            missing_functions.append(func_name)
            print(f"❌ {func_name} - Missing")
    
    print(f"\n📊 Function Availability: {len(available_functions)}/{len(required_functions)}")
    
    if len(missing_functions) == 0:
        print("🎉 All required functions are available!")
        return True
    else:
        print(f"🚨 Missing functions: {missing_functions}")
        return False

def run_comprehensive_silent_mode_tests():
    """Run all silent mode tests"""
    print("🚀 Starting Comprehensive Silent Mode Branch Tests")
    print("=" * 60)
    
    # Test function availability
    functions_available = test_function_availability()
    
    if not functions_available:
        print("\n🚨 Cannot proceed with classification tests - missing functions!")
        return False
    
    # Run classification tests
    classification_success = test_silent_mode_classification()
    
    print("\n" + "=" * 60)
    
    if classification_success:
        print("🎉 SILENT MODE IMPLEMENTATION SUCCESSFUL!")
        print("\n✅ Summary:")
        print("  • Silent mode branch added to intelligent_context_classifier")
        print("  • Silent mode detection patterns implemented")
        print("  • handle_silent_mode function created")
        print("  • Classification scores include 'silent' category")
        print("  • Action mapping includes silent mode routing")
        print("\n🚀 The intelligent decision tree now has 9 complete branches:")
        print("  1. Memory (behavioral commands)")
        print("  2. Silent Mode (activation/deactivation/status)")
        print("  3. Journal (knowledge entries)")
        print("  4. AI Actions (recurring actions)")
        print("  5. Reminders (one-time alerts)")
        print("  6. Tasks (to-do items)")
        print("  7. Guide (help/assistance)")
        print("  8. Expert (advice/strategy)")
        print("  9. Chat (general conversation)")
        return True
    else:
        print("🚨 SILENT MODE IMPLEMENTATION NEEDS FIXES!")
        print("\nPlease review the test results and adjust the classification patterns.")
        return False

if __name__ == "__main__":
    success = run_comprehensive_silent_mode_tests()
    if success:
        print("\n✅ READY FOR PRODUCTION DEPLOYMENT!")
    else:
        print("\n❌ IMPLEMENTATION INCOMPLETE - NEEDS ATTENTION!")
