# Todowa AGENT - Task Management System

**Version:** 3.0 - Enhanced Agents
**Last Updated:** 2025-08-21

## Purpose
This is the CLI-testable version of the Todowa multi-agent task management system. Use this version for testing and development via command line interface.

## Key Features
- ✅ Enhanced Audit Agent for response verification
- ✅ Intelligent time parsing for accurate reminders
- ✅ Natural conversational capabilities
- ✅ CLI testing interface via `cli.py` and automated testing
- ✅ Multi-agent architecture (TaskAgent, ReminderAgent, etc.)
- ✅ Supabase database integration
- ✅ AI-powered intent classification
- ✅ AI-powered typo correction
- ✅ Detailed task information including priorities and categories

## Quick Start
```bash
# Install dependencies
uv pip install -r requirements.txt

# Configure your credentials in config.py
# - GEMINI_API_KEY
# - SUPABASE_URL  
# - SUPABASE_SERVICE_KEY

# Run CLI interface for testing
python cli.py

# Run automated tests
python test_runner.py
```

## Enhanced Agents in v3.0

### Audit Agent
- Now verifies the truth in responses
- Specifically checks time-related claims
- Corrects inaccurate information automatically

### Reminder Agent
- Accurate time parsing for expressions like "in 5 minutes"
- Supports natural language time formats
- Properly displays time in response messages

### General Agent
- Enhanced conversational capabilities
- Natural dialogue patterns
- Empathetic responses

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
- **cli.py** - Command line interface for testing
- **test_runner.py** - Automated testing framework
- **src/multi_agent_system/** - Core agent framework
- **src/ai_text_processors/** - AI-powered text processing (including typo correction)
- **database_personal.py** - Database operations
- **enhanced_ai_tools.py** - AI-powered tools
- **prompts/** - Agent prompt templates

## Test Status
✅ **TESTS PASSED** - Enhanced version with improved functionality
