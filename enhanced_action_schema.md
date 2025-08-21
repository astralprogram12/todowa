# Enhanced Action Schema for Todowa AI Agent Tools

## Overview
This document describes the enhanced action schema for the Todowa AI agent tools system. The system now includes comprehensive task management, smart categorization, performance monitoring, and advanced features like automatic parameter injection.

## Available Actions

### Task Management Actions

#### create_task
**Description:** Create a new task with comprehensive details and smart categorization
**Category:** tasks  
**Auto-inject:** supabase, user_id

**Parameters:**
- `title` (required): Task title
- `description` (optional): Detailed description
- `priority` (optional): low, medium, high, urgent (default: medium)
- `due_date` (optional): ISO format date string (YYYY-MM-DD)
- `category` (optional): Task category (auto-categorized if 'general')

**Example:**
```json
{
  "action": "create_task",
  "parameters": {
    "title": "Complete project report",
    "description": "Finalize the Q4 analysis report for the client",
    "priority": "high",
    "due_date": "2025-08-25",
    "category": "work"
  }
}
```

#### get_tasks
**Description:** Retrieve tasks with comprehensive filtering options
**Category:** tasks  
**Auto-inject:** supabase, user_id

**Parameters:**
- `status` (optional): pending, in_progress, completed, cancelled
- `priority` (optional): low, medium, high, urgent
- `category` (optional): Filter by category
- `due_before` (optional): ISO format date string
- `limit` (optional): Maximum number of tasks (default: 50)

**Example:**
```json
{
  "action": "get_tasks",
  "parameters": {
    "status": "pending",
    "priority": "high",
    "limit": 10
  }
}
```

#### update_task
**Description:** Update an existing task with new information
**Category:** tasks  
**Auto-inject:** supabase, user_id

**Parameters:**
- `task_id` (required): ID of the task to update
- `title` (optional): New title
- `description` (optional): New description
- `status` (optional): New status
- `priority` (optional): New priority
- `due_date` (optional): New due date
- `category` (optional): New category

**Example:**
```json
{
  "action": "update_task",
  "parameters": {
    "task_id": 123,
    "status": "completed",
    "priority": "medium"
  }
}
```

#### delete_task
**Description:** Delete a task permanently
**Category:** tasks  
**Auto-inject:** supabase, user_id

**Parameters:**
- `task_id` (required): ID of the task to delete

**Example:**
```json
{
  "action": "delete_task",
  "parameters": {
    "task_id": 123
  }
}
```

### Reminder Management Actions

#### create_reminder
**Description:** Create a reminder with smart task creation
**Category:** reminders  
**Auto-inject:** supabase, user_id

**Parameters:**
- `title` (required): Reminder title
- `remind_at` (required): ISO format datetime string
- `description` (optional): Additional details
- `task_id` (optional): Link to existing task (auto-creates if not provided)

**Smart Feature:** If no `task_id` is provided, the system automatically creates a task.

**Example:**
```json
{
  "action": "create_reminder",
  "parameters": {
    "title": "Team meeting",
    "remind_at": "2025-08-22T09:00:00Z",
    "description": "Weekly team sync meeting"
  }
}
```

#### get_reminders
**Description:** Get reminders with filtering options
**Category:** reminders  
**Auto-inject:** supabase, user_id

**Parameters:**
- `is_sent` (optional): Filter by sent status
- `task_id` (optional): Filter by specific task
- `remind_before` (optional): ISO format datetime string
- `limit` (optional): Maximum number of reminders (default: 50)

**Example:**
```json
{
  "action": "get_reminders",
  "parameters": {
    "is_sent": false,
    "remind_before": "2025-08-25T00:00:00Z"
  }
}
```

### Category Management Actions

#### create_category
**Description:** Create a new category for organizing tasks
**Category:** categories  
**Auto-inject:** supabase, user_id

**Parameters:**
- `name` (required): Category name
- `description` (optional): Category description
- `color` (optional): Hex color code (default: #3B82F6)

**Example:**
```json
{
  "action": "create_category",
  "parameters": {
    "name": "Personal Projects",
    "description": "Personal development and hobby projects",
    "color": "#10B981"
  }
}
```

#### get_categories
**Description:** Retrieve all categories for the user
**Category:** categories  
**Auto-inject:** supabase, user_id

**Parameters:** None

**Example:**
```json
{
  "action": "get_categories",
  "parameters": {}
}
```

### Analytics & Reporting Actions

#### get_task_analytics
**Description:** Generate comprehensive task analytics
**Category:** analytics  
**Auto-inject:** supabase, user_id

**Parameters:**
- `days` (optional): Number of days to analyze (default: 30)

**Returns:**
- Total tasks, completion rates, priority distribution, category distribution

**Example:**
```json
{
  "action": "get_task_analytics",
  "parameters": {
    "days": 7
  }
}
```

### Utility Actions

#### validate_cron_expression
**Description:** Validate a cron expression and provide next execution times
**Category:** utilities

**Parameters:**
- `cron_expr` (required): Cron expression (e.g., "0 9 * * MON-FRI")

**Example:**
```json
{
  "action": "validate_cron_expression",
  "parameters": {
    "cron_expr": "0 9 * * MON-FRI"
  }
}
```

## Enhanced Features

### 1. Automatic Parameter Injection
The system automatically injects common parameters like `supabase` client and `user_id` into tool functions, reducing boilerplate and ensuring consistency.

### 2. Smart Category Management
When creating tasks, if the category is 'general', the system automatically categorizes based on keywords in the title and description:
- **work**: meeting, project, deadline, report, presentation, client, team, office
- **personal**: shopping, grocery, family, friend, birthday, anniversary, vacation
- **health**: doctor, appointment, exercise, gym, medication, checkup, health
- **finance**: bank, payment, bill, tax, budget, money, invoice, insurance
- **home**: clean, repair, maintenance, garden, organize, decorate
- **learning**: study, course, book, tutorial, lesson, practice, exam

### 3. Performance Monitoring
Every tool execution is monitored for:
- Execution count
- Average execution time
- Success/failure rates
- Last execution timestamp

### 4. Smart Task-Reminder Integration
When creating a reminder without a `task_id`, the system automatically creates a corresponding task, ensuring nothing falls through the cracks.

## Response Format

All actions return responses in a consistent format:

**Success Response:**
```json
{
  "success": true,
  "data": {
    // Actual response data
  }
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Error message describing what went wrong"
}
```

## Categories

Tools are organized into the following categories:
- **tasks**: Task management operations
- **reminders**: Reminder management operations  
- **categories**: Category management operations
- **analytics**: Reporting and analytics operations
- **utilities**: General utility functions

## Error Handling

The system includes comprehensive error handling:
- Database connection failures
- Invalid parameters
- Permission denied errors
- Resource not found errors
- Validation errors

All errors are logged and returned in a consistent format for easy debugging and user feedback.
