#!/usr/bin/env python3
# run_quick_test.py
# Quick single test runner for individual test cases

import os
import sys
import asyncio
import argparse
from datetime import datetime

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
from src.multi_agent_system.orchestrator import Orchestrator

# Test configuration
CLI_TEST_USER_ID = "e4824ec3-c9c4-4563-91f8-56077aa64d63"
CLI_TEST_PHONE = "CLI_TEST_USER"

async def run_single_test(test_input):
    """Run a single test with the given input"""
    try:
        print("🚀 Initializing Todowa System...")
        
        # Initialize Google AI
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Initialize Supabase
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        # Initialize Orchestrator
        multi_agent_system = Orchestrator(supabase, model)
        
        # Load prompts
        prompts_dir = os.path.join(current_dir, 'prompts')
        multi_agent_system.load_all_agent_prompts(prompts_dir)
        
        print("✅ System initialized!")
        print(f"\n🔄 Testing: '{test_input}'")
        print("⏳ Processing...")
        
        # Process the input
        response = await multi_agent_system.process_user_input(
            user_id=CLI_TEST_USER_ID,
            user_input=test_input,
            phone_number=CLI_TEST_PHONE
        )
        
        print(f"\n🤖 RESPONSE:")
        print(f"─" * 60)
        if isinstance(response, dict):
            if 'message' in response:
                print(response['message'])
            else:
                print(f"Response: {response}")
        else:
            print(str(response))
        print(f"─" * 60)
        
        return response
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def main():
    parser = argparse.ArgumentParser(description='Run a quick test with Todowa CLI')
    parser.add_argument('test_input', help='The test input to send to the system')
    
    args = parser.parse_args()
    
    print(f"{'='*80}")
    print(f"🧪 QUICK TEST RUNNER - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")
    
    result = asyncio.run(run_single_test(args.test_input))
    
    print(f"\n{'='*80}")
    print(f"🏁 Test completed at {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
