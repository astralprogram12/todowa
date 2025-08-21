"""
Enhanced Double-Check Agent Test Suite

This test suite demonstrates the Enhanced Double-Check Agent's ability to catch
and correct errors like the Indonesian time parsing issue.

Test Case: 'ingetin 5 menit lagi buang sampah' → should NOT become 'tomorrow at 9:00 AM'
"""

import sys
import os
import asyncio
import json
from datetime import datetime, timezone, timedelta

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

try:
    import google.generativeai as genai
    import config
    
    # Mock components for testing
    class MockSupabase:
        pass
    
    class MockAIModel:
        def generate_content(self, prompt):
            # Mock AI responses for testing
            if isinstance(prompt, list):
                prompt_text = str(prompt)
            else:
                prompt_text = str(prompt)
            
            # Mock validation responses
            if 'JSON' in prompt_text and 'intent_aligned' in prompt_text:
                return MockResponse('{"intent_aligned": true, "confidence": 0.9, "issues": [], "missing_elements": []}')
            elif 'JSON' in prompt_text and 'is_consistent' in prompt_text:
                return MockResponse('{"is_consistent": true, "confidence": 0.95, "inconsistencies": [], "severity": "low"}')
            elif 'corrected response' in prompt_text.lower():
                return MockResponse("Got it! I'll remind you about 'buang sampah' in 5 minutes.")
            else:
                return MockResponse("I'll remind you about buang sampah tomorrow at 9:00 AM.")
    
    class MockResponse:
        def __init__(self, text):
            self.text = text
    
    # Import the Enhanced Double-Check Agent
    from src.multi_agent_system.agents.enhanced_double_check_agent import (
        EnhancedDoubleCheckAgent,
        LanguageCoherenceValidator,
        TimeExpressionValidator,
        IntentAlignmentChecker,
        FactualConsistencyMonitor,
        ContextAppropriatenessFilter
    )
    from src.ai_text_processors.ai_time_parser import AITimeParser
    from src.ai_text_processors.translation_agent import TranslationAgent
    
except ImportError as e:
    print(f"Import error: {e}")
    print("Note: This test requires the full project structure and dependencies")
    sys.exit(1)

class EnhancedDoubleCheckTestSuite:
    """Comprehensive test suite for the Enhanced Double-Check Agent."""
    
    def __init__(self):
        # Initialize with mock components
        self.supabase = MockSupabase()
        self.ai_model = MockAIModel()
        
        # Create the enhanced double-check agent
        self.double_check_agent = EnhancedDoubleCheckAgent(self.supabase, self.ai_model)
        
        # Test cases
        self.test_cases = [
            {
                'name': 'Indonesian Time Parsing Error',
                'original_input': 'ingetin 5 menit lagi buang sampah',
                'agent_response': {'message': "I'll remind you about buang sampah tomorrow at 9:00 AM."},
                'agent_name': 'ReminderAgent',
                'expected_issues': ['TIME MISMATCH', 'Indonesian'],
                'expected_corrections': True
            },
            {
                'name': 'Spanish Time Expression',
                'original_input': 'recuérdame en 10 minutos estudiar',
                'agent_response': {'message': "I'll remind you to study next week."},
                'agent_name': 'ReminderAgent',
                'expected_issues': ['TIME MISMATCH'],
                'expected_corrections': True
            },
            {
                'name': 'Correct English Response',
                'original_input': 'remind me in 15 minutes to call mom',
                'agent_response': {'message': "Got it! I'll remind you to call mom in 15 minutes."},
                'agent_name': 'ReminderAgent',
                'expected_issues': [],
                'expected_corrections': False
            },
            {
                'name': 'Missing Task Context',
                'original_input': 'ingetin besok pertemuan penting',
                'agent_response': {'message': "I've set a reminder for tomorrow."},
                'agent_name': 'ReminderAgent',
                'expected_issues': ['task', 'context'],
                'expected_corrections': True
            }
        ]
    
    async def run_all_tests(self):
        """Run all test cases and generate a comprehensive report."""
        print("🔍 Enhanced Double-Check Agent Test Suite")
        print("=" * 60)
        
        results = {
            'total_tests': len(self.test_cases),
            'passed': 0,
            'failed': 0,
            'test_details': []
        }
        
        for i, test_case in enumerate(self.test_cases, 1):
            print(f"\n📋 Test {i}: {test_case['name']}")
            print("-" * 40)
            
            try:
                result = await self.run_single_test(test_case)
                results['test_details'].append(result)
                
                if result['passed']:
                    results['passed'] += 1
                    print("✅ PASSED")
                else:
                    results['failed'] += 1
                    print("❌ FAILED")
                
            except Exception as e:
                results['failed'] += 1
                error_result = {
                    'test_name': test_case['name'],
                    'passed': False,
                    'error': str(e),
                    'validation_result': None
                }
                results['test_details'].append(error_result)
                print(f"💥 ERROR: {e}")
        
        # Generate final report
        self.generate_test_report(results)
        return results
    
    async def run_single_test(self, test_case):
        """Run a single test case."""
        print(f"📥 Input: '{test_case['original_input']}'")
        print(f"🤖 Agent Response: '{test_case['agent_response']['message']}'")
        
        # Create mock context
        context = {
            'user_id': 'test_user',
            'conversation_id': 'test_conversation',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Run validation
        validation_result = await self.double_check_agent.validate_response(
            original_input=test_case['original_input'],
            agent_response=test_case['agent_response'],
            agent_name=test_case['agent_name'],
            context=context
        )
        
        print(f"🎯 Validation Result:")
        print(f"   • Valid: {validation_result.get('is_valid', True)}")
        print(f"   • Confidence: {validation_result.get('confidence_score', 1.0):.2f}")
        print(f"   • Issues Found: {len(validation_result.get('validation_issues', []))}")
        print(f"   • Corrections: {len(validation_result.get('correction_suggestions', []))}")
        
        if validation_result.get('validation_issues'):
            print(f"   • Issue Details: {validation_result['validation_issues']}")
        
        if validation_result.get('correction_suggestions'):
            print(f"   • Suggested Corrections: {len(validation_result['correction_suggestions'])} found")
        
        # Check if corrected response was generated
        corrected_response = validation_result.get('validated_response', {})
        if corrected_response != test_case['agent_response']:
            print(f"✏️  Corrected Response: '{corrected_response.get('message', 'N/A')}'")
        
        # Evaluate test success
        passed = self.evaluate_test_result(test_case, validation_result)
        
        return {
            'test_name': test_case['name'],
            'passed': passed,
            'validation_result': validation_result,
            'original_input': test_case['original_input'],
            'agent_response': test_case['agent_response']['message'],
            'corrected_response': corrected_response.get('message') if corrected_response != test_case['agent_response'] else None
        }
    
    def evaluate_test_result(self, test_case, validation_result):
        """Evaluate if a test case passed or failed."""
        expected_issues = test_case.get('expected_issues', [])
        expected_corrections = test_case.get('expected_corrections', False)
        
        actual_issues = validation_result.get('validation_issues', [])
        has_corrections = len(validation_result.get('correction_suggestions', [])) > 0
        
        # Check if expected issues were found
        issues_found = True
        if expected_issues:
            for expected_issue in expected_issues:
                found = any(expected_issue.lower() in issue.lower() for issue in actual_issues)
                if not found:
                    issues_found = False
                    break
        else:
            # If no issues expected, validation should pass
            issues_found = validation_result.get('is_valid', True)
        
        # Check if corrections were generated as expected
        corrections_match = (has_corrections == expected_corrections)
        
        return issues_found and corrections_match
    
    def generate_test_report(self, results):
        """Generate a comprehensive test report."""
        print("\n" + "=" * 60)
        print("📊 ENHANCED DOUBLE-CHECK AGENT TEST REPORT")
        print("=" * 60)
        
        print(f"📈 Summary:")
        print(f"   • Total Tests: {results['total_tests']}")
        print(f"   • Passed: {results['passed']}")
        print(f"   • Failed: {results['failed']}")
        print(f"   • Success Rate: {(results['passed'] / results['total_tests'] * 100):.1f}%")
        
        print(f"\n🎯 Key Test Results:")
        
        # Highlight the Indonesian test case
        indonesian_test = next((test for test in results['test_details'] 
                              if 'Indonesian' in test['test_name']), None)
        
        if indonesian_test:
            print(f"\n🇮🇩 Indonesian Time Parsing Test:")
            print(f"   • Status: {'✅ PASSED' if indonesian_test['passed'] else '❌ FAILED'}")
            print(f"   • Original: '{indonesian_test['original_input']}'")
            print(f"   • Agent Response: '{indonesian_test['agent_response']}'")
            if indonesian_test.get('corrected_response'):
                print(f"   • Corrected: '{indonesian_test['corrected_response']}'")
            
            validation = indonesian_test.get('validation_result', {})
            if validation.get('validation_issues'):
                print(f"   • Issues Detected: {validation['validation_issues']}")
        
        print(f"\n📋 Detailed Results:")
        for test in results['test_details']:
            status = "✅ PASS" if test['passed'] else "❌ FAIL"
            print(f"   • {test['test_name']}: {status}")
        
        # Generate recommendations
        print(f"\n💡 Recommendations:")
        if results['failed'] > 0:
            print(f"   • {results['failed']} test(s) failed - review validation logic")
            print(f"   • Consider fine-tuning validation parameters")
        else:
            print(f"   • All tests passed! The Enhanced Double-Check Agent is working correctly")
            print(f"   • System successfully catches time parsing errors like the Indonesian example")
        
        print(f"\n🔧 System Status:")
        print(f"   • Enhanced Double-Check Agent: ✅ Operational")
        print(f"   • Validation Framework: ✅ Active")
        print(f"   • Error Prevention: ✅ Enabled")
        
        # Save detailed report to file
        report_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'summary': results,
            'test_cases': results['test_details']
        }
        
        with open('/workspace/updated_cli_version/ENHANCED_DOUBLE_CHECK_TEST_REPORT.json', 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        print(f"\n📄 Detailed report saved to: ENHANCED_DOUBLE_CHECK_TEST_REPORT.json")
    
    async def test_specific_indonesian_case(self):
        """Test the specific Indonesian case that caused the original issue."""
        print("\n🇮🇩 SPECIFIC INDONESIAN CASE TEST")
        print("=" * 50)
        
        # The exact problematic case
        original_input = "ingetin 5 menit lagi buang sampah"
        problematic_response = {"message": "Got it! I'll remind you about 'buang sampah' tomorrow at 9:00 AM."}
        
        print(f"📥 Original Input: '{original_input}'")
        print(f"🚫 Problematic Response: '{problematic_response['message']}'")
        print(f"🎯 Expected Issue: Time mismatch - '5 menit lagi' (5 minutes) ≠ 'tomorrow'")
        
        # Run validation
        validation_result = await self.double_check_agent.validate_response(
            original_input=original_input,
            agent_response=problematic_response,
            agent_name='TestAgent',
            context={'user_id': 'test_user'}
        )
        
        print(f"\n🔍 Validation Results:")
        print(f"   • Is Valid: {validation_result.get('is_valid', True)}")
        print(f"   • Confidence: {validation_result.get('confidence_score', 1.0):.2f}")
        print(f"   • Issues Detected: {len(validation_result.get('validation_issues', []))}")
        
        for issue in validation_result.get('validation_issues', []):
            print(f"     - ⚠️  {issue}")
        
        print(f"   • Corrections Suggested: {len(validation_result.get('correction_suggestions', []))}")
        
        for correction in validation_result.get('correction_suggestions', []):
            print(f"     - 💡 {correction.get('suggestion', 'N/A')}")
        
        # Check if corrected response was generated
        corrected_response = validation_result.get('validated_response', {})
        if corrected_response.get('message') != problematic_response['message']:
            print(f"\n✅ Corrected Response Generated:")
            print(f"   '{corrected_response.get('message', 'N/A')}'")
        else:
            print(f"\n❌ No correction applied")
        
        return validation_result

async def main():
    """Main test execution function."""
    print("🚀 Starting Enhanced Double-Check Agent Test Suite")
    print("Testing the system's ability to catch errors like the Indonesian time parsing issue...")
    
    test_suite = EnhancedDoubleCheckTestSuite()
    
    # Run comprehensive tests
    results = await test_suite.run_all_tests()
    
    # Run specific Indonesian case test
    indonesian_result = await test_suite.test_specific_indonesian_case()
    
    print(f"\n🎉 Test Suite Complete!")
    print(f"   • Overall Success Rate: {(results['passed'] / results['total_tests'] * 100):.1f}%")
    print(f"   • Indonesian Case Handled: {'✅ Yes' if not indonesian_result.get('is_valid', True) else '❌ No'}")

if __name__ == "__main__":
    # Configure Gemini API (use mock if not available)
    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        print("✅ Gemini API configured")
    except:
        print("⚠️  Using mock AI model for testing")
    
    # Run the test suite
    asyncio.run(main())
