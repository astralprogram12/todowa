#!/usr/bin/env python3
# test_runner.py
# Comprehensive Test Runner for Todowa CLI Application
# Tests response quality, typo correction, and human-like behavior

import os
import sys
import asyncio
import json
from datetime import datetime
import traceback

# Add project directories to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
src_dir = os.path.join(current_dir, 'src')
if src_dir not in sys.path:
    sys.path.append(src_dir)

import google.generativeai as genai
from supabase import create_client, Client

import config
import database_personal
from src.multi_agent_system.orchestrator import Orchestrator

# Test configuration
CLI_TEST_USER_ID = "e4824ec3-c9c4-4563-91f8-56077aa64d63"
CLI_TEST_PHONE = "CLI_TEST_USER"

class TodowaTestRunner:
    def __init__(self):
        self.supabase = None
        self.model = None
        self.multi_agent_system = None
        self.test_results = []
        
    def initialize_system(self):
        """Initialize the Todowa system for testing"""
        try:
            print("🚀 Initializing Todowa Test System...")
            
            # Initialize Google AI
            print("  🔧 Setting up Google Generative AI...")
            genai.configure(api_key=config.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            
            # Initialize Supabase
            print("  🔧 Connecting to Supabase...")
            self.supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
            
            # Initialize Orchestrator
            print("  🔧 Loading Multi-Agent System...")
            self.multi_agent_system = Orchestrator(self.supabase, self.model)
            
            # Load prompts
            print("  🔧 Loading agent prompts...")
            prompts_dir = os.path.join(current_dir, 'prompts')
            self.multi_agent_system.load_all_agent_prompts(prompts_dir)
            
            print("✅ Initialization complete!")
            return True
            
        except Exception as e:
            print(f"❌ FATAL: Failed to initialize system: {str(e)}")
            traceback.print_exc()
            return False
    
    async def process_test_input(self, test_input):
        """Process a test input and return the response"""
        try:
            print(f"\n🔄 Testing: '{test_input}'")
            
            # Call the orchestrator
            response = await self.multi_agent_system.process_user_input(
                user_id=CLI_TEST_USER_ID,
                user_input=test_input,
                phone_number=CLI_TEST_PHONE
            )
            
            return response
            
        except Exception as e:
            print(f"❌ ERROR processing '{test_input}': {str(e)}")
            traceback.print_exc()
            return None
    
    def analyze_response_quality(self, test_case, user_input, response):
        """Analyze the quality of the response"""
        analysis = {
            'test_case': test_case,
            'user_input': user_input,
            'response': response,
            'quality_score': 0,
            'details_included': False,
            'human_like': False,
            'typo_corrected': False,
            'category_mentioned': False,
            'priority_mentioned': False,
            'confirmation_clear': False,
            'issues': [],
            'strengths': []
        }
        
        if isinstance(response, dict):
            response_text = response.get('message', str(response))
        else:
            response_text = str(response)
        
        response_lower = response_text.lower()
        
        # Check for detailed response
        detail_keywords = ['category', 'priority', 'deadline', 'created', 'task id', 'uuid']
        if any(keyword in response_lower for keyword in detail_keywords):
            analysis['details_included'] = True
            analysis['quality_score'] += 20
            analysis['strengths'].append('Detailed response with metadata')
        else:
            analysis['issues'].append('Missing task details (category, priority, etc.)')
        
        # Check for category mention
        if 'category' in response_lower:
            analysis['category_mentioned'] = True
            analysis['quality_score'] += 15
        
        # Check for priority mention
        if 'priority' in response_lower:
            analysis['priority_mentioned'] = True
            analysis['quality_score'] += 15
        
        # Check for human-like language
        human_phrases = ['great!', 'perfect!', 'done!', 'got it', 'sure', 'alright', 'wonderful']
        if any(phrase in response_lower for phrase in human_phrases):
            analysis['human_like'] = True
            analysis['quality_score'] += 20
            analysis['strengths'].append('Human-like conversational tone')
        else:
            analysis['issues'].append('Robotic or formal tone')
        
        # Check for clear confirmation
        confirmation_words = ['created', 'added', 'saved', 'completed', 'updated', 'deleted']
        if any(word in response_lower for word in confirmation_words):
            analysis['confirmation_clear'] = True
            analysis['quality_score'] += 15
            analysis['strengths'].append('Clear action confirmation')
        else:
            analysis['issues'].append('Unclear action confirmation')
        
        # Check for typo correction (specific test cases)
        typo_tests = {
            'luncz': 'lunch',
            'grocerys': 'groceries',
            'meetng': 'meeting',
            'tomorow': 'tomorrow'
        }
        
        input_lower = user_input.lower()
        for typo, correct in typo_tests.items():
            if typo in input_lower and correct in response_lower:
                analysis['typo_corrected'] = True
                analysis['quality_score'] += 25
                analysis['strengths'].append(f'Auto-corrected "{typo}" to "{correct}"')
                break
        
        # Final quality assessment
        if analysis['quality_score'] >= 80:
            analysis['overall_rating'] = 'Excellent'
        elif analysis['quality_score'] >= 60:
            analysis['overall_rating'] = 'Good'
        elif analysis['quality_score'] >= 40:
            analysis['overall_rating'] = 'Fair'
        else:
            analysis['overall_rating'] = 'Poor'
        
        return analysis
    
    def run_test_case(self, test_case, user_input, expected_behavior):
        """Run a single test case"""
        print(f"\n{'='*80}")
        print(f"🧪 TEST CASE: {test_case}")
        print(f"📝 INPUT: {user_input}")
        print(f"🎯 EXPECTED: {expected_behavior}")
        print(f"{'='*80}")
        
        # Process the input
        response = asyncio.run(self.process_test_input(user_input))
        
        if response:
            if isinstance(response, dict):
                response_text = response.get('message', str(response))
            else:
                response_text = str(response)
            
            print(f"\n🤖 RESPONSE:")
            print(f"─" * 50)
            print(response_text)
            print(f"─" * 50)
            
            # Analyze response quality
            analysis = self.analyze_response_quality(test_case, user_input, response)
            
            print(f"\n📊 QUALITY ANALYSIS:")
            print(f"  Overall Rating: {analysis['overall_rating']} ({analysis['quality_score']}/100)")
            print(f"  Details Included: {'✅' if analysis['details_included'] else '❌'}")
            print(f"  Human-like Tone: {'✅' if analysis['human_like'] else '❌'}")
            print(f"  Clear Confirmation: {'✅' if analysis['confirmation_clear'] else '❌'}")
            print(f"  Category Mentioned: {'✅' if analysis['category_mentioned'] else '❌'}")
            print(f"  Priority Mentioned: {'✅' if analysis['priority_mentioned'] else '❌'}")
            
            if analysis['strengths']:
                print(f"\n💪 STRENGTHS:")
                for strength in analysis['strengths']:
                    print(f"  ✅ {strength}")
            
            if analysis['issues']:
                print(f"\n⚠️  ISSUES:")
                for issue in analysis['issues']:
                    print(f"  ❌ {issue}")
            
            self.test_results.append(analysis)
            return analysis
        else:
            print("❌ Test failed - no response received")
            failed_analysis = {
                'test_case': test_case,
                'user_input': user_input,
                'response': None,
                'overall_rating': 'Failed',
                'quality_score': 0,
                'issues': ['No response received']
            }
            self.test_results.append(failed_analysis)
            return failed_analysis
    
    def run_basic_task_creation_tests(self):
        """Run TC001-TC005: Basic Task Creation Tests"""
        print(f"\n{'🚀'*20} BASIC TASK CREATION TESTS {'🚀'*20}")
        
        test_cases = [
            ("TC001", "Add task: Buy groceries", "Task created with category and priority details"),
            ("TC002", "Create task: Meeting with John at 3pm", "Task created with time parsing and details"),
            ("TC003", "New task: Call dentist tomorrow", "Task created with date parsing and details"),
            ("TC004", "Task: Finish project report by Friday", "Task created with deadline parsing and details"),
            ("TC005", "Add: Review quarterly budget", "Task created with short command and details")
        ]
        
        for test_case, user_input, expected in test_cases:
            self.run_test_case(test_case, user_input, expected)
    
    def run_typo_correction_tests(self):
        """Run typo correction and human-like response tests"""
        print(f"\n{'🔤'*20} TYPO CORRECTION TESTS {'🔤'*20}")
        
        test_cases = [
            ("TYPO001", "remind me for luncz at 2", "Auto-correct 'luncz' to 'lunch' and create reminder"),
            ("TYPO002", "add task buy grocerys", "Auto-correct 'grocerys' to 'groceries' and create task"),
            ("TYPO003", "create meetng with boss tomorow", "Auto-correct 'meetng' to 'meeting' and 'tomorow' to 'tomorrow'"),
            ("TYPO004", "Add task: Finsh homework by sunday", "Auto-correct 'Finsh' to 'Finish' and create task")
        ]
        
        for test_case, user_input, expected in test_cases:
            self.run_test_case(test_case, user_input, expected)
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        print(f"\n{'📊'*20} COMPREHENSIVE TEST REPORT {'📊'*20}")
        
        total_tests = len(self.test_results)
        if total_tests == 0:
            print("No tests were run.")
            return
        
        # Calculate overall statistics
        total_score = sum(result['quality_score'] for result in self.test_results)
        average_score = total_score / total_tests
        
        excellent_count = sum(1 for r in self.test_results if r['overall_rating'] == 'Excellent')
        good_count = sum(1 for r in self.test_results if r['overall_rating'] == 'Good')
        fair_count = sum(1 for r in self.test_results if r['overall_rating'] == 'Fair')
        poor_count = sum(1 for r in self.test_results if r['overall_rating'] == 'Poor')
        failed_count = sum(1 for r in self.test_results if r['overall_rating'] == 'Failed')
        
        print(f"\n📈 OVERALL STATISTICS:")
        print(f"  Total Tests: {total_tests}")
        print(f"  Average Score: {average_score:.1f}/100")
        print(f"  Excellent: {excellent_count} ({excellent_count/total_tests*100:.1f}%)")
        print(f"  Good: {good_count} ({good_count/total_tests*100:.1f}%)")
        print(f"  Fair: {fair_count} ({fair_count/total_tests*100:.1f}%)")
        print(f"  Poor: {poor_count} ({poor_count/total_tests*100:.1f}%)")
        print(f"  Failed: {failed_count} ({failed_count/total_tests*100:.1f}%)")
        
        # Feature analysis
        details_count = sum(1 for r in self.test_results if r.get('details_included', False))
        human_count = sum(1 for r in self.test_results if r.get('human_like', False))
        category_count = sum(1 for r in self.test_results if r.get('category_mentioned', False))
        priority_count = sum(1 for r in self.test_results if r.get('priority_mentioned', False))
        typo_count = sum(1 for r in self.test_results if r.get('typo_corrected', False))
        
        print(f"\n🎯 FEATURE ANALYSIS:")
        print(f"  Detailed Responses: {details_count}/{total_tests} ({details_count/total_tests*100:.1f}%)")
        print(f"  Human-like Tone: {human_count}/{total_tests} ({human_count/total_tests*100:.1f}%)")
        print(f"  Category Mentions: {category_count}/{total_tests} ({category_count/total_tests*100:.1f}%)")
        print(f"  Priority Mentions: {priority_count}/{total_tests} ({priority_count/total_tests*100:.1f}%)")
        print(f"  Typo Corrections: {typo_count}/{total_tests} ({typo_count/total_tests*100:.1f}%)")
        
        # Save detailed report
        report_file = f"/workspace/todowa_cli_updated/TEST_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'total_tests': total_tests,
                    'average_score': average_score,
                    'ratings': {
                        'excellent': excellent_count,
                        'good': good_count,
                        'fair': fair_count,
                        'poor': poor_count,
                        'failed': failed_count
                    },
                    'features': {
                        'detailed_responses': details_count,
                        'human_like_tone': human_count,
                        'category_mentions': category_count,
                        'priority_mentions': priority_count,
                        'typo_corrections': typo_count
                    }
                },
                'detailed_results': self.test_results
            }, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_file}")

def main():
    """Main test runner function"""
    runner = TodowaTestRunner()
    
    if not runner.initialize_system():
        print("❌ Failed to initialize system. Exiting.")
        return
    
    print(f"\n{'🎯'*25} STARTING COMPREHENSIVE TESTS {'🎯'*25}")
    
    # Run test suites
    runner.run_basic_task_creation_tests()
    runner.run_typo_correction_tests()
    
    # Generate final report
    runner.generate_test_report()
    
    print(f"\n{'✅'*25} TESTING COMPLETE {'✅'*25}")

if __name__ == "__main__":
    main()
