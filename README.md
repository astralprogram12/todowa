# Todowa WhatsApp - Task Management System

**Version:** Updated with Natural Language Processing  
**Interface:** WhatsApp Integration via Webhook  
**Last Updated:** 2025-08-21

## Purpose
This is the WhatsApp-integrated version of the Todowa multi-agent task management system. Deploy this version for production WhatsApp bot functionality.

## Key Features
- ✅ Natural language task understanding (no keyword extraction)
- ✅ WhatsApp webhook integration via `app.py`
- ✅ Multi-agent architecture (TaskAgent, ReminderAgent, etc.)
- ✅ Supabase database integration
- ✅ AI-powered intent classification
- ✅ Fonnte API for WhatsApp messaging

## Quick Start
```bash
# Install dependencies
uv pip install -r requirements.txt

# Configure your credentials in config.py
# - GEMINI_API_KEY
# - SUPABASE_URL  
# - SUPABASE_SERVICE_KEY
# - FONNTE_TOKEN

# Deploy to your preferred platform (Vercel, Railway, etc.)
# Webhook URL: https://your-domain.com/webhook
```

## WhatsApp Commands
- "Add a task to call the client"
- "Mark the 'call the client' task as done"
- "What are my current tasks?"
- "Remind me to buy groceries tomorrow at 3pm"

## Architecture
- **app.py** - WhatsApp webhook handler
- **src/multi_agent_system/** - Core agent framework  
- **database_personal.py** - Database operations
- **enhanced_ai_tools.py** - AI-powered tools
- **services.py** - WhatsApp messaging via Fonnte
- **prompts/** - Agent prompt templates

## Deployment
This version is ready for deployment to any platform that supports Python web apps:
- Vercel (recommended for serverless)
- Railway 
- Heroku
- Any VPS with Python support

## Recent Improvements
- Removed brittle keyword extraction
- Implemented AI-powered natural language understanding
- Fixed database constraint issues (using 'done' status)
- Enhanced UUID handling for task updates
- Improved error handling and response parsing
- Synced with CLI version for consistency

## Integration
- **Fonnte API** for WhatsApp messaging
- **Supabase** for database and real-time features
- **Google Gemini** for AI understanding
