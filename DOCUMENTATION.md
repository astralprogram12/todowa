# Comprehensive Documentation

This document provides a detailed overview of the modules and components of the Multi-agent AI WhatsApp Assistant. It is intended for developers who want to understand the architecture, functionality, and implementation details of the system.

---

## Core Modules

### `config.py`

**Purpose**: This module centralizes all application settings, secrets, and credentials, loading them from environment variables. This approach enhances security and portability, making it easy to configure the application for different environments without changing the code.

**Attributes**:

-   `FONNTE_TOKEN` (Optional[str]): API token for the Fonnte WhatsApp messaging service.
-   `SUPABASE_URL` (Optional[str]): URL for the Supabase project database.
-   `SUPABASE_SERVICE_KEY` (Optional[str]): Service key for authenticating with the Supabase backend.
-   `UNVERIFIED_LIMIT` (int): The lifetime message limit for users who have not registered.
-   `VERIFIED_LIMIT` (int): The daily message limit for registered and verified users.
-   `MAX_AGENT_LOOPS` (int): A safety measure to prevent infinite loops in agent interactions.
-   `CHAT_TEST_USER_ID` (str): A constant UUID for a test user in the database.
-   `CHAT_TEST_PHONE` (str): A special identifier for the user during chat-based testing.
-   `SUPABASE_JWT_SECRET` (Optional[str]): The secret key for generating user-specific JWTs for Row Level Security.
-   `SUPABASE_ANON_KEY` (Optional[str]): The anonymous key for the Supabase project.

**Functions**:

-   `get_gemini_api_keys()`: Loads all Gemini API keys from environment variables into a named dictionary. It scans for variables named `GEMINI_API_KEY1`, `GEMINI_API_KEY2`, etc., and formats them as `{'gemini_1': 'key_value', ...}`.

### `database.py`

**Purpose**: This module handles all database interactions for the multi-agent AI assistant. It provides a comprehensive set of functions and a dedicated class for managing data in the Supabase database, including user verification, CRUD operations, and specialized queries.

**Standalone Functions**:

-   `check_and_update_usage(supabase, sender_phone, user_id)`: Checks if a user is within their usage limits and updates their message count.
-   `get_user_id_by_phone(supabase, phone)`: Retrieves a user's UUID using their phone number.
-   `get_user_context(supabase, user_id)`: Fetches user-specific settings, such as their timezone.

**Classes**:

-   **`DatabaseManager`**: Manages all database operations for a specific, authenticated user.
    -   `__init__(self, supabase_client, user_id)`: Initializes the manager for a specific user.
    -   `create_task(...)`: Creates a new task.
    -   `get_tasks_by_ids(...)`: Retrieves tasks by their unique IDs.
    -   `get_tasks(...)`: Retrieves a list of tasks with optional filters.
    -   `update_task(...)`: Updates a specific task.
    -   `delete_task(...)`: Deletes a specific task.
    -   `get_task_stats()`: Retrieves statistics about the user's tasks.
    -   `create_schedule(...)`: Creates a new scheduled action.
    -   `get_schedules(...)`: Fetches a list of schedules.
    -   `update_schedule(...)`: Updates a specific schedule.
    -   `delete_schedule(...)`: Deletes a specific schedule.
    -   `create_journal_entry_in_db(...)`: Creates a new journal entry.
    -   `search_journal_entries_by_titles(...)`: Searches for journal entries by title.
    -   `update_journal_entry_in_db(...)`: Updates a journal entry.
    -   `delete_journal_entry_in_db(...)`: Deletes a journal entry.
    -   `create_or_update_memory(...)`: Creates or updates an AI memory.
    -   `get_memories(...)`: Retrieves AI memories.
    -   `delete_memory(...)`: Deletes a specific AI memory.
    -   `create_tech_support_ticket(...)`: Creates a new tech support ticket.
    -   `get_recent_tasks_and_journals()`: Fetches tasks and journal entries from the last 3 days.
    -   `create_financial_transaction_in_db(...)`: Inserts a new financial transaction.
    -   `create_or_update_budget_in_db(...)`: Creates or updates a budget.

### `api_key_manager.py`

**Purpose**: This module manages and rotates Gemini API keys to provide resilient access to the AI model. It contains two key classes: `ApiKeyManager` and `ResilientGeminiModel`.

**Classes**:

-   **`ResilientGeminiModel`**: A proxy wrapper for the Gemini model that enhances resilience by automatically handling API key rotation on failures.
    -   `__init__(self, key_manager, agent_name, is_json_model)`: Initializes the resilient model.
    -   `generate_content(self, *args, **kwargs)`: Wraps the model's `generate_content` call with retry logic.

-   **`ApiKeyManager`**: Manages and rotates Gemini API keys entirely in memory, making it ideal for serverless environments.
    -   `__init__(self, gemini_keys)`: Initializes the manager with a dictionary of keys.
    -   `mark_key_as_broken(self, key_value)`: Marks a specific key as broken in memory for the current session.
    -   `get_next_key(self)`: Gets the next valid (not broken) key from the list.
    -   `create_ai_model(self, agent_name)`: Creates a resilient Gemini client instance configured for JSON output.
    -   `create_chat_model(self, agent_name)`: Creates a resilient Gemini client instance for natural language chat.
    -   `get_key_count(self)`: Returns the total number of API keys loaded.
    -   `get_valid_key_count(self)`: Returns the number of keys not marked as broken.

### `action_executor.py`

**Purpose**: This module is a critical component of the AI assistant, responsible for translating the structured output from specialized agents into concrete actions. It receives a list of actions and dispatches them to the appropriate functions registered in the `tool_registry`.

**Classes**:

-   **`ActionExecutor`**: Executes a list of actions by dispatching them to registered tools.
    -   `__init__(self, db_manager, user_id)`: Initializes the executor for a specific user.
    -   `execute_actions(self, actions)`: Executes a list of actions using the tool registry, collecting and returning the results.

### `tools.py`

**Purpose**: This module provides a comprehensive tool registry and execution framework. It features an `EnhancedToolRegistry` that not only stores tool functions but also tracks detailed performance metrics for each.

**Key Components**:

-   `ToolMetrics`: A data class to hold performance data for a single tool.
-   `EnhancedToolRegistry`: A singleton class that manages all tools, their metadata, and performance metrics.
-   `@tool`: A decorator that simplifies the process of registering a function with the global `tool_registry`.

**Classes**:

-   **`ToolMetrics`**: Holds performance and usage metrics for a registered tool.
    -   `update(self, execution_time, success)`: Updates the metrics after a tool execution.
    -   `get_success_rate(self)`: Calculates the success rate of the tool.

-   **`EnhancedToolRegistry`**: An advanced tool registry with performance monitoring and analytics.
    -   `register(...)`: Registers a tool with enhanced metadata.
    -   `execute(...)`: Executes a tool with performance monitoring.
    -   `set_injection_context(...)`: Sets a context dictionary for auto-parameter injection.
    -   `get_metrics(...)`: Gets performance metrics for a specific tool.
    -   `get_all_metrics()`: Gets a summary of performance metrics for all tools.
    -   `get_tools_by_category(...)`: Gets all tool names in a specific category.
    -   `get_tool_info(...)`: Gets detailed information about a specific tool.
    -   `list_tools()`: Lists all registered tools with their summary information.
    -   `export_metrics(...)`: Exports metrics to a JSON file.
    -   `clear_metrics()`: Resets all performance metrics.

**Decorators**:

-   `@tool(name, description, category, auto_inject)`: A decorator to register a function as a tool in the global `tool_registry`.

### `ai_tools.py`

**Purpose**: This module defines the concrete implementations of the tools that AI agents can execute. These tools form the practical capabilities of the AI assistant, allowing it to perform actions like searching the internet, managing a database, and more.

**Decorators**:

-   `@db_tool_handler`: A decorator for database tools to standardize response and error handling.

**Tools**:

-   **Web**:
    -   `internet_search(query, num_results)`: Performs an internet search using DuckDuckGo.
-   **Tasks**:
    -   `create_task(...)`: Creates a new task.
    -   `update_task(...)`: Updates an existing task.
    -   `delete_task(...)`: Deletes a task.
    -   `get_tasks(...)`: Retrieves tasks based on specified criteria.
    -   `get_task_stats()`: Retrieves statistics about the user's tasks.
-   **Journal**:
    -   `create_journal_entry(...)`: Creates a new journal entry.
    -   `search_journal_entries(...)`: Searches for journal entries by title.
    -   `update_journal_entry(...)`: Updates a journal entry.
    -   `delete_journal_entry(...)`: Deletes a journal entry.
-   **AI Brain (Memory)**:
    -   `create_or_update_memory(...)`: Creates or updates an AI's internal memory.
    -   `get_memories(...)`: Retrieves AI memories.
    -   `delete_memory(...)`: Deletes an AI memory.
-   **Scheduling**:
    -   `create_schedule(...)`: Creates a new scheduled action.
    -   `get_schedules(...)`: Retrieves a list of scheduled actions.
    -   `update_schedule(...)`: Updates a scheduled action.
    -   `delete_schedule(...)`: Deletes a scheduled action.
-   **Financial**:
    -   `create_financial_transaction(...)`: Creates a new financial transaction.
    -   `create_or_update_budget(...)`: Creates or updates a budget.
-   **Tech Support**:
    -   `create_tech_support_ticket(...)`: Creates a new tech support ticket.

### `services.py`

**Purpose**: This module encapsulates functions that interact with external, third-party APIs. By centralizing these interactions, the application can easily manage and, if necessary, replace service providers without altering the core business logic.

**Functions**:

-   `send_fonnte_message(target, message)`: Sends a reply message to a user via the Fonnte WhatsApp API.

### `time_parser.py`

**Purpose**: This module is deprecated and kept for backward compatibility only. The functionality for parsing time expressions has been integrated directly into the relevant agents.

**Classes**:

-   **`TimeParser`**: A dummy class for backward compatibility. Its methods are deprecated and should not be used.

---

## Agent Modules

### `answering_agent.py`

**Purpose**: This agent is the last step in the chain, responsible for synthesizing all processed information into a single, user-friendly response. It fetches communication style preferences from the database and injects them into a prompt for the AI model, ensuring the final output is consistent with the user's desired persona.

**Classes**:

-   **`AnsweringAgent`**: Handles all final user responses by applying a database-defined persona.
    -   `__init__(self, ai_model, supabase)`: Initializes the agent.
    -   `process_multi_response(self, context)`: Processes output from multiple agents to synthesize a single response.
    -   `process_error(self, error_message)`: Formats a generic, safe error message for the user.
    -   `process_response(self, information)`: Processes information and generates the final user response.
    -   `process_context_clarification(self, clarification_request)`: Formats a clarification question to send back to the user.

### `audit_agent.py`

**Purpose**: This agent acts as a master router, analyzing a clarified user command and creating a multi-step execution plan. It intelligently splits or groups parts of the command and routes them to the correct specialist agents based on the user's underlying goal.

**Classes**:

-   **`AuditPlannerPromptBuilder`**: Constructs the detailed, rule-based prompt for the `AuditAgent`.
    -   `build(self, resolved_command, conversation_history)`: Assembles the complete prompt with headers, rules, agent rosters, examples, and the user's command.

-   **`AuditAgent`**: Uses the prompt from the builder and an AI model to generate the execution plan.
    -   `__init__(self, ai_model)`: Initializes the agent with an AI model.
    -   `create_execution_plan(self, resolved_command, conversation_history)`: Takes a clarified command and conversation history and returns a structured execution plan.

### `brain_agent.py`

**Purpose**: This agent intelligently manages user preferences and the AI's communication style. It uses a stateful approach, merging new requests with existing settings to maintain a consistent persona.

**Classes**:

-   **`BrainAgent`**: Manages the AI's behavior and user preferences.
    -   `__init__(self, ai_model, api_key_manager)`: Initializes the agent.
    -   `process_command(self, user_command, user_context)`: Processes a command by fetching the current state, analyzing the request in context, and returning executable JSON actions.

### `context_resolution_agent.py`

**Purpose**: This agent is the first step in the processing pipeline. It clarifies and synthesizes messy, conversational user input into a single, clean, and actionable command that other agents can understand.

**Classes**:

-   **`ContextResolverPromptBuilder`**: Constructs the detailed, rule-based prompt for the `ContextResolutionAgent`.
    -   `build(self, user_command, conversation_history)`: Assembles the complete prompt with headers, rules, examples, and the user's command.

-   **`ContextResolutionAgent`**: Uses the prompt from the builder and an AI model to generate the clarified command.
    -   `__init__(self, ai_model)`: Initializes the agent with an AI model.
    -   `resolve_context(self, user_command, conversation_history)`: Takes a raw user command and conversation history and returns a structured, unambiguous command.

### `financial_agent.py`

**Purpose**: This agent is responsible for managing a user's finances. It can track income and expenses, and set budgets.

**Classes**:

-   **`FinancialPromptBuilder`**: Constructs prompts for the `FinancialAgent`.
    -   `build_intent_parser_prompt(self, user_command)`: Builds a prompt to parse the user's financial intent.

-   **`FinancialAgent`**: An agent for managing a user's finances.
    -   `__init__(self, ai_model, supabase)`: Initializes the agent.
    -   `process_command(self, user_command, user_context)`: The main entry point for processing financial commands.

### `finding_agent.py`

**Purpose**: This agent is an expert, multi-stage information retrieval agent. It uses a safe, dual-search strategy: first, a targeted category-based search, and second, a recency-based search. It always falls back to a web search if its internal search is unsuccessful.

**Classes**:

-   **`FindingAgent`**: An expert information retrieval agent.
    -   `__init__(self, ai_model, supabase)`: Initializes the agent.
    -   `process_command(self, user_command, user_context)`: The main entry point for processing a search command.

### `general_fallback_agent.py`

**Purpose**: This agent is an expert reasoning agent that handles complex queries using a two-step "research and synthesize" process. It can access personal data and the live internet to provide insightful, evidence-based answers.

**Classes**:

-   **`GeneralFallbackAgent`**: An expert reasoning agent.
    -   `__init__(self, ai_model, supabase)`: Initializes the agent.
    -   `process_command(self, user_command, user_context)`: Orchestrates the internal "Triage -> Fetch -> Synthesize" workflow.

### `guide_agent.py`

**Purpose**: This agent provides basic guidance on how to use the application.

**Classes**:

-   **`GuideAgent`**: Provides basic guidance on how to use the application.
    -   `__init__(self)`: Initializes the agent.
    -   `process_command(self, user_command, user_context)`: Processes the user's command to see if it's a request for help.

### `journal_agent.py`

**Purpose**: This agent is an intelligent, self-contained agent for managing a user's journal. It uses a single, powerful intent model and efficiently batches similar actions to minimize API calls.

**Classes**:

-   **`JournalAgent`**: An intelligent agent for managing a user's journal.
    -   `__init__(self, ai_model, supabase, api_key_manager)`: Initializes the agent.
    -   `process_command(self, user_command, user_context)`: The main entry point for a single intent model and intelligent batching.

### `schedule_agent.py`

**Purpose**: This agent is an intelligent scheduler for future and recurring actions. It can create, list, find, update, and delete schedules.

**Classes**:

-   **`ScheduleAgent`**: An intelligent scheduler for future and recurring actions.
    -   `__init__(self, ai_model, supabase, api_key_manager)`: Initializes the agent.
    -   `process_command(self, user_command, user_context)`: The main entry point for processing a schedule command.

### `task_agent.py`

**Purpose**: This agent is responsible for managing a user's tasks. It can create, list, update, complete, and delete tasks, and it can also handle batch operations.

**Classes**:

-   **`TaskAgent`**: Manages a user's tasks.
    -   `__init__(self, ai_model, supabase, api_key_manager)`: Initializes the agent.
    -   `process_command(self, user_command, user_context)`: The main entry point for processing a task command.

### `task_management_agent.py`

**Purpose**: This agent is a goal-oriented agent with strict JSON validation for managing tasks. It features intelligent context inference, fuzzy matching, and time intelligence.

**Classes**:

-   **`TaskManagementAgent`**: A goal-oriented agent for managing tasks.
    -   `__init__(self, ai_model)`: Initializes the agent.
    -   `process_command(self, clear_command, user_context)`: The main entry point for processing a task command.

### `tech_support_agent.py`

**Purpose**: This agent handles user frustration and technical issues by creating a support ticket.

**Classes**:

-   **`TechSupportPromptBuilder`**: Constructs prompts for the `TechSupportAgent`.
    -   `build_intent_parser_prompt(self, user_command)`: Builds a prompt to parse the user's tech support request.

-   **`TechSupportAgent`**: An agent that handles user frustration and technical issues.
    -   `__init__(self, ai_model, supabase)`: Initializes the agent.
    -   `process_command(self, user_command, user_context)`: Processes the command and creates a tech support ticket action.

---

## Main Application

### `wa_version.py`

**Purpose**: This is the main application file. It initializes the Flask web server, sets up the webhook endpoint, and orchestrates the entire multi-agent workflow for processing incoming user messages.

**Functions**:

-   `create_user_jwt(user_id, jwt_secret)`: Generates a JWT for a given user ID to enable Row Level Security in Supabase.

**Classes**:

-   **`DatabaseConversationHistory`**: Manages storing and retrieving structured conversation history in the Supabase database.
    -   `__init__(self, supabase_client, user_id, max_history)`: Initializes the history manager.
    -   `add_interaction(self, user_input, clarified_input, response)`: Adds a new interaction to the database.
    -   `get_recent_context(self)`: Retrieves the most recent conversation turns for context.

-   **`TodowaApp`**: The main application class that holds the state and orchestrates the agent workflow.
    -   `__init__(self)`: Initializes the application.
    -   `initialize_system(self)`: Connects to Supabase, initializes the API key manager, and sets up the core agents.
    -   `create_user_supabase_client(self, user_id)`: Creates a new Supabase client authenticated as a specific user.
    -   `process_message_async(self, message, user_id, user_supabase_client)`: The core asynchronous method that processes a user's message through the entire agent pipeline.
    -   `_build_user_context(self, user_id, user_supabase_client)`: Fetches and assembles the user's context from the database.
    -   `_execute_json_actions(self, user_id, actions, db_manager)`: Executes the list of actions generated by the agents.

**Flask Routes**:

-   `@app.route('/webhook', methods=['POST', 'GET'])`: The main endpoint for receiving incoming messages from the WhatsApp provider.
-   `@app.route('/', methods=['GET'])`: A simple health check endpoint.

---

## Utility Modules

### `src/multi_agent_system/utils/api_key_manager.py`

**Purpose**: This module provides a utility class for managing API keys, including fetching them from a database and tracking their usage and performance.

**Classes**:

-   **`ApiKeyManager`**: A utility class for managing API keys.
    -   `__init__(self, supabase_client, named_keys)`: Initializes the manager.
    -   `get_key(self, provider)`: Gets the next available key for a given provider.
    -   `get_statistics(self, provider)`: Gets usage statistics for a provider's keys.
    -   `add_key_to_database(self, name, provider)`: Adds a new key to the database.

### `task_agent.py`

**Purpose**: This agent is responsible for managing a user's tasks. It can create, list, update, complete, and delete tasks, and it can also handle batch operations.

**Classes**:

-   **`TaskAgent`**: Manages a user's tasks.
    -   `__init__(self, ai_model, supabase, api_key_manager)`: Initializes the agent.
    -   `process_command(self, user_command, user_context)`: The main entry point for processing a task command.
