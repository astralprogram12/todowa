# Complete Multi-Agent System with Supabase Integration

This is a complete version of the multi-agent system that integrates with Supabase functionality from the original application. It includes all agent files, prompt files, and tools necessary for deployment.

## Structure

- `app.py`: Main application entry point with webhook handling
- `run.py`: Script to run the enhanced multi-agent system
- `supabase_integration.py`: Module for integrating Supabase with the multi-agent system
- `prompts/v1/`: Essential prompt files for agent functionality
  - `00_core_identity.md`: Core identity and persona
  - `01_action_schema.md`: Action schema definitions
  - `02_task_processing.md`: Task processing instructions
  - And other prompt files for memory, silent mode, etc.
- `src/multi_agent_system/`: Core multi-agent system implementation
  - `agents/`: All agent implementations (task, reminder, silent mode, etc.)
  - `tool_collections/`: Tool collections for database, memory, NLP, time, etc.
  - `orchestrator.py`: The main orchestrator for the multi-agent system
  - `tools.py`: Core tools functionality
  - `agent_tools_mixin.py`: Mixin for agent tools

## Setup

1. Ensure all environment variables are set:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY`
   - `GEMINI_API_KEY`
   - `FONNTE_TOKEN`

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python run.py
   ```

## Deployment

This package contains everything needed for deployment to a platform like GitHub. Simply push this entire directory to your repository, and then deploy according to your platform's instructions.

## Key Features

1. Full integration with Supabase functionality from the original application
2. Complete multi-agent system with all agent types
3. Enhanced database tools that bridge to original database functions
4. Support for all database operations: tasks, reminders, silent mode, etc.
5. Comprehensive prompt files for agent functionality
