# Multi-Agent AI WhatsApp Assistant

This project is a sophisticated, AI-driven assistant that interacts with users through WhatsApp. It uses a multi-agent architecture to understand and process user requests, manage tasks, store notes, and much more.

## System Architecture

The system is built on a multi-agent architecture, where each agent has a specific role. This design allows for a clear separation of concerns and makes the system extensible and maintainable. The overall workflow is orchestrated by a central component that routes requests to the appropriate agents.

For a detailed visual representation of the workflow, please see the `detailed_flow_diagram.md` file.

## Detailed Documentation

For a comprehensive overview of each module, class, and function, please see the [**Detailed Documentation**](DOCUMENTATION.md).

### Orchestrator

The main entry point and orchestrator for the application is `wa_version.py`. It is a Flask application that receives user messages from WhatsApp via a webhook. Its key responsibilities include:

1.  **Receiving Requests:** Listens for incoming messages on the `/webhook` endpoint.
2.  **Context Resolution:** Uses the `ContextResolutionAgent` to clarify the user's command and understand its true intent, taking into account the conversation history.
3.  **Planning:** Employs the `AuditAgent` to break down the clarified command into a series of sub-tasks.
4.  **Delegation:** Routes each sub-task to the most appropriate specialized agent (e.g., `JournalAgent`, `TaskAgent`).
5.  **Execution:** Gathers the results from the specialist agents, which include actions to be performed on the database, and passes them to the `ActionExecutor`.
6.  **Response Generation:** Uses the `AnsweringAgent` to synthesize a single, coherent, and user-friendly response from the results of the entire process.

### Specialized Agents

The system includes several specialized agents, each an expert in a particular domain. These agents are Python classes designed to process a specific type of command and return a structured dictionary of actions and responses.

**Example: The `JournalAgent`**

The `src/multi_agent_system/agents/journal_agent.py` is a prime example of a specialized agent. Its purpose is to manage a user's long-term notes and memories. When the orchestrator delegates a command to the `JournalAgent` (e.g., "remind me that my friend's address is..."), the agent:

1.  Uses a powerful, prompt-engineered call to a Gemini AI model to determine the user's specific intent (e.g., `upsert`, `search`, `update`, `delete`).
2.  Can handle complex commands with multiple actions (e.g., "save a note about X and search for Y").
3.  Interacts with the Supabase database to create, retrieve, update, or delete journal entries.
4.  Returns a structured response to the orchestrator, including any data to be stored or actions to be executed.

## Getting Started

Follow these instructions to get the project running on your local machine for development and testing purposes.

### Prerequisites

*   Python 3.9 or higher
*   A Supabase account for the database
*   A Fonnte account for WhatsApp messaging
*   Access to Google's Gemini API

### Installation

1.  **Clone the repository:**

    ```sh
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Create a virtual environment and activate it:**

    ```sh
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install the required dependencies:**

    ```sh
    pip install -r requirements.txt
    ```

### Configuration

The application is configured using environment variables. Create a `.env` file in the root of the project or set these variables in your deployment environment.

The following variables are required:

*   `FONNTE_TOKEN`: Your API token from Fonnte for sending WhatsApp messages.
*   `SUPABASE_URL`: The URL of your Supabase project.
*   `SUPABASE_SERVICE_KEY`: The service role key for your Supabase project.
*   `GEMINI_API_KEY...`: Your API keys for the Gemini model. The system is designed to use multiple keys, which should be named `GEMINI_API_KEY1`, `GEMINI_API_KEY2`, and so on.

You can refer to `config.py` for more details on how these variables are loaded and used.

## Usage

To run the application locally for development, you can use the Flask development server included in `wa_version.py`.

```sh
python wa_version.py
```

This will start the server on `http://localhost:5001`.

### Webhook

The primary endpoint for the application is `/webhook`, which accepts `POST` requests. This endpoint is designed to be used with a service like Fonnte, which sends a JSON payload with the sender's phone number and the message content.

A `GET` request to `/webhook` will return a simple status message for verification purposes.

## Key Components

*   **`wa_version.py`**: The main application file. It contains the Flask web server, the orchestration logic, and the webhook endpoint.
*   **`config.py`**: Defines how the application is configured, primarily through environment variables.
*   **`database.py`**: Contains helper functions for interacting with the Supabase database, such as user verification and usage tracking.
*   **`action_executor.py`**: A class responsible for executing the list of actions returned by the specialist agents.
*   **`api_key_manager.py`**: Manages the pool of Gemini API keys.
*   **`src/multi_agent_system/agents/`**: This directory contains all the specialized AI agents. Each agent is a Python class that inherits from a base agent and is responsible for a specific set of tasks.
    *   **`context_resolution_agent.py`**: The "master router" that clarifies the user's command.
    *   **`audit_agent.py`**: Creates an execution plan of sub-tasks.
    *   **`journal_agent.py`**: Manages user notes and memories.
    *   **`task_agent.py`**: Manages tasks and to-do lists.
    *   **`schedule_agent.py`**: Handles scheduling and reminders.
    *   **`brain_agent.py`**: Manages the AI's own personality and settings.
    *   **`answering_agent.py`**: Formats the final response to the user.
    *   ...and others.
