# Inferred Database Schema

This document lists the database tables and columns as inferred from their usage in `database.py` and `ai_tools.py`. The function of each table and column is described based on its context in the code.

## Table: `user_whatsapp`

**Function:** Stores information about WhatsApp users, including their usage and basic settings.

| Column | Inferred Function |
|---|---|
| `user_id` | A unique identifier for the user. |
| `phone` | The user's WhatsApp phone number. |
| `daily_message_count` | Tracks the number of messages a user has sent on the current day for usage limiting. |
| `last_message_date` | The date of the user's last message, used to reset the daily message count. |
| `timezone` | The user's timezone, used for date and time calculations. |

## Table: `tasks`

**Function:** Stores user-created tasks or to-do items.

| Column | Inferred Function |
|---|---|
| `id` | A unique identifier for the task. |
| `user_id` | The ID of the user who owns the task. |
| `title` | The title or name of the task. |
| `description` | A brief description of the task. |
| `notes` | Detailed notes or additional information about the task. |
| `priority` | The priority level of the task (e.g., 'low', 'medium', 'high'). |
| `status` | The current status of the task (e.g., 'todo', 'done'). |
| `category` | A user-defined category for the task. |
| `due_date` | The date when the task is due. |
| `created_at` | A timestamp indicating when the task was created. |
| `updated_at` | A timestamp indicating when the task was last updated. |

## Table: `scheduled_actions`

**Function:** Stores information about actions that are scheduled to be executed in the future.

| Column | Inferred Function |
|---|---|
| `id` | A unique identifier for the scheduled action. |
| `user_id` | The ID of the user who owns the scheduled action. |
| `action_type` | The type of action to be performed. |
| `action_payload` | The data required to execute the scheduled action. |
| `schedule_type` | The type of schedule (e.g., 'recurring', 'one-time'). |
| `schedule_value` | The value that defines the schedule (e.g., a cron string). |
| `timezone` | The timezone for the schedule. |
| `next_run_at` | The timestamp for the next scheduled execution. |
| `status` | The current status of the scheduled action (e.g., 'active'). |
| `updated_at` | A timestamp indicating when the schedule was last updated. |

## Table: `journals`

**Function:** Stores user-created journal entries, notes, and memories.

| Column | Inferred Function |
|---|---|
| `id` | A unique identifier for the journal entry. |
| `user_id` | The ID of the user who owns the journal entry. |
| `title` | The title of the journal entry. |
| `content` | The main content of the journal entry. |
| `category` | A user-defined category for the journal entry. |
| `entry_type` | The type of journal entry (e.g., 'note', 'memory'). |
| `created_at` | A timestamp indicating when the journal entry was created. |
| `updated_at` | A timestamp indicating when the journal entry was last updated. |

## Table: `ai_brain_memories`

**Function:** Stores the AI's internal memories and preferences about a user.

| Column | Inferred Function |
|---|---|
| `id` | A unique identifier for the memory. |
| `user_id` | The ID of the user to whom the memory pertains. |
| `brain_data_type` | The type of memory being stored (e.g., 'user_preferences'). |
| `content_json` | A JSON object containing the structured memory data. |
| `content` | A text representation of the memory. |
| `importance` | An integer rating of the memory's importance. |

## Table: `tech_support_tickets`

**Function:** Stores tech support tickets submitted by users.

| Column | Inferred Function |
|---|---|
| `user_id` | The ID of the user who submitted the ticket. |
| `message` | The user's message describing the technical issue. |
| `status` | The current status of the support ticket (e.g., 'open'). |

## Table: `financial_transactions`

**Function:** Stores individual financial transactions (income or expense) for a user.

| Column | Inferred Function |
|---|---|
| `user_id` | The ID of the user who owns the transaction. |
| `transaction_type` | The type of transaction (e.g., 'income', 'expense'). |
| `amount` | The monetary value of the transaction. |
| `currency` | The currency of the transaction (e.g., 'USD'). |
| `category` | A user-defined category for the transaction (e.g., 'groceries', 'salary'). |
| `description` | A brief description of the transaction. |
| `transaction_date` | The date the transaction occurred. |

## Table: `budgets`

**Function:** Stores user-defined budgets for specific categories and time periods.

| Column | Inferred Function |
|---|---|
| `user_id` | The ID of the user who owns the budget. |
| `category` | The category the budget applies to. |
| `amount` | The budgeted amount for the period. |
| `period` | The time period for the budget (e.g., 'monthly', 'weekly', 'yearly'). |
| `start_date` | The start date of the budget period. |
| `end_date` | The end date of the budget period. |
