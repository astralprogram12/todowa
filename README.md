# Todowa WhatsApp - Task Management System

**Version:** Modern WhatsApp Interface
**Last Updated:** 2025-08-21

## Purpose
This is the WhatsApp interface version of the Todowa multi-agent task management system. It provides the same core functionality as the CLI version but is designed specifically for WhatsApp integration.

## Key Features
- ✅ Natural language task understanding (no keyword extraction)
- ✅ Multi-agent architecture (TaskAgent, ReminderAgent, etc.)
- ✅ Supabase database integration
- ✅ AI-powered intent classification
- ✅ AI-powered typo correction
- ✅ WhatsApp webhook integration
- ✅ Detailed task information including priorities and categories

## Agents
The system includes the following agents:

1. ActionAgent - Handles action-oriented user requests
2. AuditAgent - Monitors and audits system operations
3. CoderAgent - Provides code-related assistance
4. ContextAgent - Manages conversation context
5. ExpertAgent - Offers domain expertise
6. GeneralAgent - Handles general requests
7. GuideAgent - Provides guidance and tutorials
8. HelpAgent - Responds to help requests
9. InformationAgent - Retrieves and presents information
10. IntentClassifierAgent - Classifies user intent
11. PreferenceAgent - Manages user preferences
12. ReminderAgent - Handles reminders and scheduling
13. SilentAgent - Provides silent processing
14. SilentModeAgent - Manages silent mode settings
15. TaskAgent - Core task management functionality

## Architecture
- **app.py** - WhatsApp webhook interface
- **src/multi_agent_system/** - Core agent framework
- **src/ai_text_processors/** - AI-powered text processing (including typo correction)
- **database_personal.py** - Database operations
- **enhanced_ai_tools.py** - AI-powered tools
- **prompts/** - Agent prompt templates

## Enhanced Features
- AI-powered typo correction for improved user experience
- Detailed task information including priorities and categories
- Robust webhook handling for WhatsApp integration
