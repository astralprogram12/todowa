#!/usr/bin/env python3
# cli.py
# Command Line Interface for Todowa Multi-Agent System
# Replaces WhatsApp webhook with direct command prompt interaction

import os
import sys
import asyncio
import traceback
from datetime import datetime

# --- 1. Add Project Directories to Python Path ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
src_dir = os.path.join(current_dir, 'src')
if src_dir not in sys.path:
    sys.path.append(src_dir)

# --- 2. Import All Necessary Modules ---
import google.generativeai as genai
from supabase import create_client, Client

import config
import database_personal
from src.multi_agent_system.orchestrator import Orchestrator

# --- 3. CLI Configuration ---
CLI_TEST_USER_ID = "e4824ec3-c9c4-4563-91f8-56077aa64d63"  # Test user created in Supabase
CLI_TEST_PHONE = "CLI_TEST_USER"  # Identifier for CLI testing

def print_banner():
    """Print the CLI banner"""
    print("="*60)
    print("🤖 TODOWA MULTI-AGENT SYSTEM - CLI MODE")
    print("📱 WhatsApp → 💻 Command Line Interface")
    print("="*60)
    print(f"⏰ Session started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"👤 Test User ID: {CLI_TEST_USER_ID}")
    print("\n💡 Available Commands:")
    print("   - Type any message to interact with agents")
    print("   - Type 'exit' or 'quit' to end session")
    print("   - Type 'help' for agent capabilities")
    print("   - Type 'status' to check system status")
    print("="*60)

def print_system_status(multi_agent_system, supabase):
    """Print system status information"""
    print("\n🔍 SYSTEM STATUS:")
    print(f"  ✅ Multi-Agent System: {'Ready' if multi_agent_system else 'Not Initialized'}")
    print(f"  ✅ Supabase Connection: {'Connected' if supabase else 'Not Connected'}")
    print(f"  ✅ Test User: {CLI_TEST_USER_ID}")
    print(f"  ✅ Google AI Model: Gemini-2.5-Flash")
    
    # Test database connection
    try:
        user_info = database_personal.get_user_id_by_phone(supabase, CLI_TEST_PHONE)
        print(f"  ✅ Database Test: {'Pass' if user_info else 'User not found'}")
    except Exception as e:
        print(f"  ❌ Database Test: {str(e)}")

def print_help():
    """Print help information about available agents"""
    print("\n🤖 AVAILABLE AGENTS:")
    agents_info = {
        "TaskAgent": "Manage tasks, todos, and project items",
        "ReminderAgent": "Set and manage time-based reminders", 
        "ContextAgent": "Access conversation history and memory",
        "ExpertAgent": "Get domain-specific expert advice",
        "ActionAgent": "Execute system operations and automation",
        "GeneralAgent": "General conversation and chat",
        "GuideAgent": "Get step-by-step instructions",
        "HelpAgent": "System help and troubleshooting",
        "InformationAgent": "Retrieve factual information",
        "PreferenceAgent": "Manage user settings and preferences",
        "CoderAgent": "Code generation and programming help",
        "SilentAgent": "Minimal response processing",
        "AuditAgent": "Activity monitoring and reporting",
        "SilentModeAgent": "Notification management",
        "IntentClassifierAgent": "Intent classification and routing"
    }
    
    for agent, description in agents_info.items():
        print(f"  📋 {agent}: {description}")
    
    print("\n💭 EXAMPLE QUERIES:")
    print("  - \"Add a task to buy groceries\"")
    print("  - \"Remind me about the meeting tomorrow at 2pm\"")
    print("  - \"What's my schedule for today?\"")
    print("  - \"Help me write a Python function\"")
    print("  - \"What are my current tasks?\"")

async def process_user_input(multi_agent_system, user_input):
    """Process user input through the multi-agent system"""
    try:
        print(f"\n🔄 Processing: '{user_input}'")
        print("⏳ Thinking...")
        
        # Call the orchestrator with CLI test user
        response = await multi_agent_system.process_user_input(
            user_id=CLI_TEST_USER_ID,
            user_input=user_input,
            phone_number=CLI_TEST_PHONE  # CLI identifier instead of real phone
        )
        
        print("\n🤖 AGENT RESPONSE:")
        print("─" * 50)
        if isinstance(response, dict):
            if 'message' in response:
                print(response['message'])
            else:
                print(f"Response: {response}")
        else:
            print(str(response))
        print("─" * 50)
        
        return response
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("🔧 Debug info:")
        traceback.print_exc()
        return None

def main():
    """Main CLI function"""
    # Initialize system
    print("🚀 Initializing Todowa CLI...")
    
    try:
        # Initialize Google AI
        print("  🔧 Setting up Google Generative AI...")
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Initialize Supabase
        print("  🔧 Connecting to Supabase...")
        supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        # Initialize Orchestrator
        print("  🔧 Loading Multi-Agent System...")
        multi_agent_system = Orchestrator(supabase, model)
        
        # Load prompts
        print("  🔧 Loading agent prompts...")
        prompts_dir = os.path.join(current_dir, 'prompts')
        multi_agent_system.load_all_agent_prompts(prompts_dir)
        
        print("✅ Initialization complete!")
        
    except Exception as e:
        print(f"❌ FATAL: Failed to initialize system: {str(e)}")
        traceback.print_exc()
        return
    
    # Print banner and start interactive session
    print_banner()
    
    # Main interaction loop
    try:
        while True:
            try:
                # Get user input
                user_input = input("\n💬 You: ").strip()
                
                # Handle special commands
                if user_input.lower() in ['exit', 'quit', 'q']:
                    print("\n👋 Goodbye! Ending Todowa CLI session.")
                    break
                elif user_input.lower() == 'help':
                    print_help()
                    continue
                elif user_input.lower() == 'status':
                    print_system_status(multi_agent_system, supabase)
                    continue
                elif user_input.lower() == 'clear':
                    os.system('cls' if os.name == 'nt' else 'clear')
                    print_banner()
                    continue
                elif not user_input:
                    print("💭 Please enter a message or command.")
                    continue
                
                # Process through multi-agent system
                response = asyncio.run(process_user_input(multi_agent_system, user_input))
                
            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupted by user. Type 'exit' to quit properly.")
                continue
            except Exception as e:
                print(f"\n❌ Unexpected error: {str(e)}")
                traceback.print_exc()
                continue
                
    except Exception as e:
        print(f"\n❌ FATAL: CLI session error: {str(e)}")
        traceback.print_exc()
    
    finally:
        print("\n📊 Session ended. Thank you for using Todowa CLI!")

if __name__ == "__main__":
    main()
