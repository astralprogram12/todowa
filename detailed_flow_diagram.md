System Flow Diagram Description
This diagram illustrates a sophisticated, AI-driven system for processing user requests. The entire process is managed by a central orchestrator, chat.py, which guides the user's command through a sequence of specialized AI agents.
code
Code
**User Input** (e.g., "remind me to call Nisa tomorrow")
           ↓
 ┌───────────────────┐
 │      **chat.py**      │
 │ (The Main Orchestrator) │
 │ - Receives user input.  │
 │ - Creates a user-specific │
 │   `DatabaseManager`.    │
 └─────────┬─────────┘
           ↓
┌────────────────────────────────────────────────────────┐
│ 🧠 ContextResolutionAgent (.resolve_context) │
│ (The Master Router) │
│ - Receives the raw command from chat.py. │
│ - Uses an internal, in-memory conversation history to │
│ understand context, correct typos, and resolve │
│ ambiguities (like "it" or "that"). │
│ - Its AI prompt determines the user's final intent │
│ and selects the single best destination agent. │
│ - Returns a JSON object like {"clarified_command": ..., "route_to": ...}.│
└─┬──────────────────┬──────────────────┬────────────────┘
| (Route: Journal) | (Route: Brain) | (Route: Task/Reminder)
| | |
↓ ↓ ↓
┌────────────┐ ┌────────────┐ ┌────────────────────┐
│ 📝 │ │ 🧠 │ │ 📋 │
│ Journal │ │ Brain │ │ TaskReminder │
│ Agent │ │ Agent │ │ Agent │
│ - Receives the clarified_command & user context from chat.py. │
│ - Performs deep analysis based on its specialty. │
│ - Generates a final JSON list of actions to be executed.│
└────────────┘ └────────────┘ └────────────────────┘
│ │ │
└─────────┬────────┼────────┬─────────┘
| | |
(Data: A list of final, executable JSON actions sent back to chat.py)
| | |
└────────┼────────┘
↓
┌────────────────────────────────────────────────────────┐
│ 🔧 ActionExecutor (.execute_actions) │
│ (The Hands) │
│ - Is instantiated by chat.py for each request. │
│ - Is given the user-specific DatabaseManager to │
│ ensure all actions are performed for the correct user.│
│ - Executes the tools specified in the JSON actions. │
└────────────────────┬───────────────────────────────────┘
|
(Interacts with Tools, Database, and Supabase)
|
(Data: A dictionary of execution results (success/failure) is sent back to chat.py)
|
┌──────────────────── V ───────────────────────────────────┐
│ 🤖 AnsweringAgent (.process_response) │
│ (The Voice) │
│ - Receives a complete package from chat.py: the │
│ original command, clarified command, action results,│
│ and specialist agent's notes. │
│ - Formats a single, user-friendly final message. │
└────────────────────┬───────────────────────────────────┘
↓
✅ Final User Response
Description of chat.py
This script is the central orchestrator and the main entry point for the "Todowa Chat" application. It doesn't have deep specialized knowledge itself; instead, it manages the entire lifecycle of a user's request, ensuring each step is executed in the correct order and that context is passed properly between the different agents and components.
Key Responsibilities:
Initialization: It sets up the entire system on startup, creating instances of the database client, the API key manager, and all the specialized AI agents (ContextResolutionAgent, JournalAgent, etc.).
Request Lifecycle Management: For each incoming user message, it performs a strict sequence of operations, acting as the "conductor" for the other agents.
User-Specific Context: It creates a new, request-specific DatabaseManager instance for every message, ensuring all database operations are securely scoped to the correct user.
Dispatching: It uses the ContextResolutionAgent's routing decision to call the appropriate specialist agent (e.g., JournalAgent).
Execution: It takes the JSON action list from the specialist agent and passes it to the ActionExecutor for execution.
History Management: After a request is fully processed, it calls ContextResolutionAgent.add_interaction() to "close the loop," adding the outcome of the turn to the router's short-term memory.
Description of context_resolution_agent.py
This script defines the Master Router, the intelligent dispatcher for the entire system. Its sole responsibility is to analyze a user's raw input and decide which specialized agent is best equipped to handle it.
Key Features and Logic:
Single, In-Memory History: The agent uses a ConversationHistory class to store only the last 5 turns of the conversation in memory. It is designed for a single session and focuses entirely on the immediate context.
Prompt-Driven Intelligence: The agent's "brain" is a comprehensive system prompt that defines its capabilities, including being a polyglot expert, handling typos, and recognizing contextual patterns.
Strict Routing Logic: The prompt gives the AI a rigid menu of possible destinations (t, JournalAgent, etc.) and forces it to choose exactly one.
Mandatory JSON Output: The agent's prompt strictly enforces that the AI's output must be a single JSON object with clarified_command and route_to keys, ensuring its decision is predictable and machine-readable.
Description of journal_agent.py
This script defines the Journal Agent, a specialist responsible for managing a user's long-term, non-task-related information, like notes, facts, and memories. It is designed to turn unstructured user commands into structured, searchable data.
Key Features and Logic:
Batch Processing: Its standout feature is the ability to process multiple commands from a single user message. It uses an initial AI call (_split_command_into_chunks) to break the user's input into a list of independent tasks.
Multi-Step AI Pipeline: For each chunk, it performs a sequence of AI-powered analyses:
Intent Determination: It classifies the user's goal for the chunk (e.g., create, search, update).
Content Analysis & Structuring: It uses a highly restrictive AI prompt to extract a broad, general title (3 words or less, no specific details) and a category from the user's content. This is crucial for maintaining high-quality, easily searchable data in the database.
Intelligent Conflict Resolution: When asked to save information that is similar to an existing note (upsert intent), it does not automatically overwrite the data. Instead, it stops and asks the user for clarification, preventing accidental data loss.
Clean Design: It uses a JournalPromptFactory class to separate all prompt-building logic from the agent's workflow logic, making the code easier to read and maintain.
Description of brain_agent.py
This script defines the Brain Agent, a highly specialized agent whose sole purpose is to manage the AI's own behavior and communication style based on the user's preferences. It acts as the AI's "personality control panel."
Key Features and Logic:
Stateful Design: The agent's core philosophy is to be stateful. It is always aware of the user's current preferences before making any decisions.
Efficient Single-Call Logic: Unlike other agents, it uses a single, powerful AI call to handle each request. Its workflow is:
FETCH: It retrieves the user's current communication style settings from the user_context.
ANALYZE & MERGE: It sends both the current settings and the new user command to the AI in one prompt. The AI's job is to intelligently merge the two to determine the final, desired state.
EXECUTE: The agent trusts the AI's JSON output completely, which contains both the user-facing response and the final actions list needed to update the database.
Intelligent Merging: Its prompt contains a "Golden Rule" that forces the AI to preserve and merge settings, preventing it from accidentally deleting preferences. It also has specific rules for handling direct conflicts ("latest wins"), deletions, and listing current settings.