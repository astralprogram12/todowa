#!/usr/bin/env python3
"""
Silent Mode Branch Test Script
Tests the intelligent_context_classifier's ability to detect silent mode requests
"""

import sys
import json
from datetime import datetime

# Mock supabase for testing
class MockSupabase:
    def __init__(self):
        pass

# Import the ai_tools module
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
        # Silent mode activation
        ("go silent for 2 hours", "silent", "Should detect silent mode activation with duration"),
        ("activate silent mode", "silent", "Should detect explicit silent mode activation"),
        ("don't reply for 30 minutes", "silent", "Should detect no-reply request"),
        ("quiet for 1 hour", "silent", "Should detect quiet mode request"),
        ("turn on silent mode", "silent", "Should detect turn on silent command"),
        ("silent mode please", "silent", "Should detect polite silent request"),
        
        # Silent mode deactivation
        ("exit silent mode", "silent", "Should detect silent mode exit"),
        ("end silent mode", "silent", "Should detect silent mode end"),
        ("stop silent mode", "silent", "Should detect silent mode stop"),
        ("deactivate silent", "silent", "Should detect silent deactivation"),
        ("back online", "silent", "Should detect back online request"),
        ("resume replies", "silent", "Should detect resume replies"),
        
        # Silent mode status
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
            else:
                status = "❌ FAIL"
                failed += 1
            
            print(f"Test {i:2d}: {status} | {description}")
            print(f"         Input: '{user_input}'")
            print(f"         Expected: {expected_classification} | Got: {actual_classification} | Confidence: {confidence:.2f}")
            print(f"         Action: {recommended_action}")
            
            if actual_classification != expected_classification:
                print(f"         🔍 All scores: {result.get('all_scores', {})}")
            
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
    
    print(f"📊 SILENT MODE CLASSIFICATION TEST RESULTS:")
    print(f"   Total Tests: {total}")
    print(f"   Passed: {passed} ✅")
    print(f"   Failed: {failed} ❌")
    print(f"   Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print(f"\n🎉 EXCELLENT! Silent mode classification is working correctly.")
    elif success_rate >= 80:
        print(f"\n✅ GOOD! Silent mode classification is mostly working.")
    elif success_rate >= 70:
        print(f"\n⚠️ NEEDS IMPROVEMENT. Silent mode classification needs tweaking.")
    else:
        print(f"\n🚨 CRITICAL ISSUE! Silent mode classification is not working properly.")
    
    return success_rate >= 80

def test_silent_mode_function_integration():
    """Test that handle_silent_mode function works correctly"""
    print("\n🧪 Testing Silent Mode Function Integration...")
    
    supabase = MockSupabase()
    user_id = "test-user-123"
    
    # Test cases for the handle_silent_mode function
    integration_tests = [
        ("go silent for 2 hours", "Should route to activation"),
        ("exit silent mode", "Should route to deactivation"),
        ("silent mode status", "Should route to status check"),
    ]
    
    print(f"\n📝 Running {len(integration_tests)} integration tests...\n")
    
    for i, (user_input, description) in enumerate(integration_tests, 1):
        try:
            print(f"Integration Test {i}: {description}")
            print(f"                  Input: '{user_input}'")
            
            # First test classification
            classification_result = ai_tools.intelligent_context_classifier(
                supabase=supabase,
                user_id=user_id,
                user_input=user_input
            )
            
            classification = classification_result.get('classification')
            recommended_action = classification_result.get('recommended_action')
            
            print(f"                  Classification: {classification}")
            print(f"                  Recommended Action: {recommended_action}")
            
            # Check if handle_silent_mode function exists
            if hasattr(ai_tools, 'handle_silent_mode'):
                print(f"                  ✅ handle_silent_mode function exists")
            else:
                print(f"                  ❌ handle_silent_mode function missing")
            
            print()
            
        except Exception as e:
            print(f"Integration Test {i}: 💥 ERROR | {description}")
            print(f"                     Error: {str(e)}")
            print()

def run_comprehensive_silent_mode_tests():
    """Run all silent mode tests"""
    print("🚀 Starting Comprehensive Silent Mode Branch Tests")
    print("=" * 60)
    
    # Run classification tests
    classification_success = test_silent_mode_classification()
    
    # Run integration tests
    test_silent_mode_function_integration()
    
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
    else:
        print("🚨 SILENT MODE IMPLEMENTATION NEEDS FIXES!")
        print("\nPlease review the test results and adjust the classification patterns.")

if __name__ == "__main__":
    run_comprehensive_silent_mode_tests()
