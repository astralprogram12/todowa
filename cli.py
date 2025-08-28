#!/usr/bin/env python3
# cli.py - V4.0 Enhanced CLI with Multilingual Support and Advanced Features
# Complete integration of V4.0: AI Time Parser, Translation, Memory, Journal, Enhanced Validation

import os
import sys
import asyncio
import traceback
import json
from datetime import datetime

# --- V4.0 Enhanced Path Setup ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
src_dir = os.path.join(current_dir, 'src')
if src_dir not in sys.path:
    sys.path.append(src_dir)

# --- V4.0 Imports ---
import google.generativeai as genai
from supabase import create_client, Client

import config
import database_personal
from src.multi_agent_system.orchestrator import OrchestratorV4, test_v4_integration, Orchestrator

# --- V4.0 CLI Configuration ---
CLI_TEST_USER_ID = "e4824ec3-c9c4-4563-91f8-56077aa64d63"  # Test user created in Supabase
CLI_TEST_PHONE = "CLI_TEST_USER"  # Identifier for CLI testing

def print_banner():
    """Print the V4.0 CLI banner"""
    print("="*70)
    print("🚀 TODOWA V4.0 MULTI-AGENT SYSTEM - ENHANCED CLI MODE")
    print("🌐 Multilingual • ⏰ AI Time Parser • 🧠 Memory & Journal • ✅ Enhanced Validation")
    print("="*70)
    print(f"⏰ Session started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"👤 Test User ID: {CLI_TEST_USER_ID}")
    print("\n💡 V4.0 Enhanced Commands:")
    print("   🔤 Multilingual support (Indonesian, Spanish, French, etc.)")
    print("   ⏰ Advanced time parsing: 'ingetin 5 menit lagi buang sampah'")
    print("   🧠 Memory management: 'remember this important moment'")
    print("   📔 Journal entries: 'journal: had a great day today'")
    print("   🔧 System commands: 'status', 'features', 'stats', 'help', 'exit'")
    print("="*70)

def print_system_status(multi_agent_system, supabase):
    """Print V4.0 system status information"""
    print("\n🔍 V4.0 SYSTEM STATUS:")
    print(f"  ✅ V4.0 Orchestrator: {'Ready' if multi_agent_system else 'Not Initialized'}")
    print(f"  ✅ Supabase Connection: {'Connected' if supabase else 'Not Connected'}")
    print(f"  ✅ Test User: {CLI_TEST_USER_ID}")
    print(f"  ✅ Google AI Model: Gemini-2.5-Flash")
    
    # V4.0 Features Status
    if multi_agent_system and hasattr(multi_agent_system, 'get_v4_features_status'):
        features_status = multi_agent_system.get_v4_features_status()
        print("\n  🆕 V4.0 Features:")
        for feature, enabled in features_status.get('features', {}).items():
            status = "✅" if enabled else "❌"
            feature_name = feature.replace('_', ' ').title()
            print(f"    {status} {feature_name}")
        
        print("\n  🤖 Available Agents:")
        agents = features_status.get('agents_available', [])
        for i, agent in enumerate(agents, 1):
            agent_name = agent.replace('_', ' ').title()
            print(f"    {i:2d}. {agent_name}")
    
    # Test database connection
    try:
        user_info = database_personal.get_user_id_by_phone(supabase, CLI_TEST_PHONE)
        print(f"\n  ✅ Database Test: {'Pass' if user_info else 'User not found'}")
    except Exception as e:
        print(f"  ❌ Database Test: {str(e)}")

def print_v4_features():
    """Print detailed V4.0 features information"""
    print("\n🆕 V4.0 ENHANCED FEATURES:")
    print("🌐 Multilingual Support:")
    print("   • Automatic language detection (Indonesian, Spanish, French, etc.)")
    print("   • Context-aware translation")
    print("   • Original language preservation")
    
    print("\n⏰ AI-Powered Time Parser:")
    print("   • Natural language time understanding")
    print("   • Fixes Indonesian parsing: 'ingetin 5 menit lagi' = 'in 5 minutes'")
    print("   • Multi-language time expressions")
    
    print("\n✅ Enhanced Double-Check Validation:")
    print("   • AI-powered response validation")
    print("   • Time consistency checking")
    print("   • Language coherence verification")
    
    print("\n🧠 Memory & Journal Management:")
    print("   • Intelligent memory storage and retrieval")
    print("   • Personal journal with sentiment analysis")
    print("   • Timeline organization and relationship mapping")
    
    print("\n📋 Content Classification:")
    print("   • Automatic routing to Memory/Journal agents")
    print("   • Context-aware response generation")
    print("   • Enhanced intent understanding")

def print_validation_stats(multi_agent_system):
    """Print V4.0 validation statistics"""
    if not multi_agent_system or not hasattr(multi_agent_system, 'get_orchestrator_statistics'):
        print("\n❌ Validation statistics not available")
        return
    
    stats = multi_agent_system.get_orchestrator_statistics()
    print("\n📊 V4.0 VALIDATION STATISTICS:")
    print(f"  Total Validations: {stats.get('total_validations', 0)}")
    print(f"  Issues Caught: {stats.get('issues_caught', 0)}")
    print(f"  Corrections Applied: {stats.get('corrections_applied', 0)}")
    print(f"  Multilingual Fixes: {stats.get('multilingual_corrections', 0)}")
    print(f"  Time Parsing Fixes: {stats.get('time_parsing_fixes', 0)}")
    
    if stats.get('total_validations', 0) > 0:
        print(f"  Issue Detection Rate: {stats.get('issue_detection_rate', 0):.2%}")
        print(f"  Correction Rate: {stats.get('correction_rate', 0):.2%}")

def print_help():
    """Print help information about available agents"""
    print("\n🤖 AVAILABLE AGENTS:")
    agents_info = {
        "TaskAgent": "Manage tasks, todos, and project items",
        "Enhanced ReminderAgent (V4.0)": "Advanced time-based reminders with AI time parsing", 
        "MemoryAgent (V4.0)": "Store and retrieve personal memories intelligently",
        "JournalAgent (V4.0)": "Manage personal journal entries with sentiment analysis", 
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
        
        # Initialize V4.0 Orchestrator
        print("  🔧 Loading V4.0 Multi-Agent System...")
        multi_agent_system = OrchestratorV4(supabase, model)
        
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
                elif user_input.lower() == 'features':
                    print_v4_features()
                    continue
                elif user_input.lower() == 'stats':
                    print_validation_stats(multi_agent_system)
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
