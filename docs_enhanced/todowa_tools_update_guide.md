# Todowa Tools Update Guide

## Overview
This guide will help you migrate from the basic Todowa tool system to the enhanced version with comprehensive task management, smart categorization, and performance monitoring.

## Prerequisites
- Python 3.7 or higher
- Existing Todowa installation
- Administrative privileges to install packages

## Step-by-Step Migration Process

### Step 1: Backup Your Current System
The migration script automatically creates backups, but it's recommended to manually backup important files:

```bash
cp -r src/ src_backup/
cp -r prompts/ prompts_backup/
cp *.py backup_files/
```

### Step 2: Copy Enhanced Files
Copy all the enhanced files to your Todowa root directory:
- `enhanced_tools.py`
- `enhanced_ai_tools.py`  
- `enhanced_agent_tools_mixin.py`
- `enhanced_action_schema.md`
- `enhanced_action_schema.json`
- `migrate_tools.py` (updated with Windows compatibility)
- `test_enhanced_tools.py`

### Step 3: Run Migration (Dry Run First)
First, preview what changes will be made:

```bash
python migrate_tools.py --dry-run
```

### Step 4: Install New Dependencies
The system requires two new packages:

```bash
pip install croniter pytz
```

### Step 5: Execute Migration
Run the actual migration:

```bash
python migrate_tools.py
```

### Step 6: Test the New System
Run comprehensive tests:

```bash
python test_enhanced_tools.py --verbose
```

### Step 7: Performance Benchmarks (Optional)
Run performance benchmarks:

```bash
python test_enhanced_tools.py --benchmark
```

## Rollback Instructions
If anything goes wrong, you can rollback to the previous version:

```bash
python migrate_tools.py --rollback <backup_directory>
```

The backup directory name will be displayed during migration (e.g., `todowa_backup_20250820_172338`).

## New Features Overview

### 1. Enhanced Task Management
- Comprehensive CRUD operations
- Smart categorization based on keywords
- Priority levels (low, medium, high, urgent)
- Due date management
- Status tracking (pending, in_progress, completed, cancelled)

### 2. Advanced Reminder System
- Auto-task creation when creating reminders
- Flexible scheduling with cron expression support
- Link reminders to existing tasks

### 3. Category Management
- Create custom categories with colors
- Automatic categorization based on content analysis
- Category-based filtering and organization

### 4. Performance Monitoring
- Execution time tracking
- Success/failure rate monitoring
- Usage statistics and analytics
- Performance reports and optimization suggestions

### 5. Smart Features
- Automatic parameter injection (supabase, user_id)
- Context-aware tool suggestions
- Bulk operations support
- Enhanced error handling and logging

## Database Schema Updates
The enhanced system requires the following database tables:

```sql
-- Tasks table (enhanced)
CREATE TABLE tasks (
  id SERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT DEFAULT '',
  priority TEXT DEFAULT 'medium',
  status TEXT DEFAULT 'pending',
  category TEXT DEFAULT 'general',
  due_date DATE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Reminders table (new)
CREATE TABLE reminders (
  id SERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  task_id INTEGER REFERENCES tasks(id),
  title TEXT NOT NULL,
  description TEXT DEFAULT '',
  remind_at TIMESTAMP NOT NULL,
  is_sent BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Categories table (new)
CREATE TABLE categories (
  id SERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT DEFAULT '',
  color TEXT DEFAULT '#3B82F6',
  created_at TIMESTAMP DEFAULT NOW()
);
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all enhanced files are in the correct location
2. **Database Connection**: Verify Supabase credentials and connectivity
3. **Package Dependencies**: Install `croniter` and `pytz` packages
4. **Permissions**: Ensure write permissions for backup operations

### Log Files
Check the following log files for detailed information:
- `migration.log`: Migration process logs
- `test_results.log`: Test execution logs

### Getting Help
If you encounter issues:
1. Check the log files for detailed error messages
2. Ensure all prerequisites are met
3. Verify database schema is up to date
4. Run tests to identify specific problems

## Post-Migration Validation

After successful migration, verify:
1. All existing tasks are preserved
2. New tool functions work correctly
3. Performance monitoring is active
4. Database operations complete successfully
5. Agent integration functions properly

## Performance Optimization

For optimal performance:
1. Regularly monitor tool execution metrics
2. Use bulk operations for multiple tasks
3. Implement appropriate database indexes
4. Monitor memory usage during heavy operations

## Next Steps

After successful migration:
1. Explore the new analytics features
2. Set up custom categories for better organization
3. Configure automated reminders
4. Review performance reports regularly
5. Update agent prompts to use new action schemas
