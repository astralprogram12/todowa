# Todowa AGENT - Task Management System

**Version:** 3.5 - Enhanced Intelligence
**Last Updated:** 2025-08-21

## Purpose
This is the WhatsApp-enabled version of the Todowa multi-agent task management system with advanced v3.5 features including conversation memory, enhanced task extraction, and adaptive responses.

## New in v3.5 ✨

### 🧠 Conversation Memory
- Remembers the last 10 conversation exchanges
- Maintains context across multiple interactions
- Uses conversation history for more relevant responses

### 🎯 Enhanced Task Extraction
- Extracts clean, core task descriptions from verbose inputs
- Example: "remind me to eat in 5 minutes" → extracts just "eat"
- AI-powered parsing removes unnecessary text automatically

### ⏰ Improved Time Parsing
- Supports abbreviated time formats:
  - "10m" = 10 minutes
  - "1h" = 1 hour
  - "2d" = 2 days
- Enhanced accuracy in time interpretation
- Better handling of complex time expressions

### 🎨 Adaptive Response System
- Detects task importance automatically
- **Simple tasks** (eating, drinking water): Brief confirmations
- **Important tasks** (meetings, deadlines): Detailed assistance with follow-up offers
- Contextual response style adjustment

### 🔍 Enhanced Ambiguity Handling
- Proactively identifies unclear user inputs
- Requests specific clarification when needed
- Prevents misunderstandings before they occur

## Key Features
- ✅ Multi-agent architecture with 15 specialized agents
- ✅ WhatsApp webhook integration
- ✅ Supabase database integration with UUID user management
- ✅ Google Gemini 2.5 Flash AI model
- ✅ AI-powered intent classification and routing
- ✅ Comprehensive error handling and logging
- ✅ Leak-proof response system (no technical details exposed to users)

## Quick Start
```bash
# Install dependencies
uv pip install -r requirements.txt

# Configure your credentials in config.py
# - GEMINI_API_KEY
# - SUPABASE_URL  
# - SUPABASE_SERVICE_KEY

# Run WhatsApp webhook server
python app.py
```

## Specialized Agents

1. **ActionAgent** - Handles action-oriented user requests
2. **AuditAgent** - Verifies responses, handles ambiguity, extracts clean tasks
3. **CoderAgent** - Provides code-related assistance
4. **ContextAgent** - Manages conversation context and memory
5. **ExpertAgent** - Offers domain expertise
6. **GeneralAgent** - Handles general chat with adaptive responses
7. **GuideAgent** - Provides guidance and tutorials
8. **HelpAgent** - Responds to help requests
9. **InformationAgent** - Retrieves and presents information
10. **IntentClassifierAgent** - Classifies user intent with v3.5 enhancements
11. **PreferenceAgent** - Manages user preferences
12. **ReminderAgent** - Enhanced time parsing and reminder management
13. **SilentAgent** - Provides silent processing
14. **SilentModeAgent** - Manages silent mode settings
15. **TaskAgent** - Core task management functionality

## Architecture
- **app.py** - Flask webhook server for WhatsApp integration
- **src/multi_agent_system/** - v3.5 enhanced agent framework
  - **orchestrator.py** - v3.5 orchestrator with conversation memory
  - **agents/** - All 15 agents with v3.5 enhancements
- **database_personal.py** - Database operations with UUID user management
- **enhanced_tools.py** - Unified tool registry system
- **prompts/v1/** - Comprehensive agent prompt templates

## v3.5 Technical Improvements
- Enhanced BaseAgent class with conversation memory
- Improved Orchestrator with 10-message history tracking
- Advanced task importance analysis in GeneralAgent
- Time accuracy verification in AuditAgent
- Abbreviation support in ReminderAgent
- Clean response filtering to prevent system information leaks

## Webhook Integration
- Accepts POST requests at `/webhook` endpoint
- Processes WhatsApp message data
- Validates user registration via phone number
- Returns structured responses to WhatsApp

## Database Schema
- UUID-based user identification
- Conversation tracking and logging
- Task and reminder storage
- Action logging for audit trails

## Test Status
✅ **v3.5 ENHANCED** - All new features implemented and ready for production
