# Installation Commands for Windows

# Step 1: Navigate to your Todowa directory
cd C:\Users\Huawei-PC\Desktop\todowa

# Step 2: Copy core files (after extracting the package)
copy core\enhanced_tools.py .
copy core\enhanced_ai_tools.py .
copy core\enhanced_agent_tools_mixin.py .
copy schemas\enhanced_action_schema.md .
copy schemas\enhanced_action_schema.json .

# Step 3: Install dependencies
pip install croniter pytz

# Step 4: Preview migration
python migrate_tools.py --dry-run

# Step 5: Run migration
python migrate_tools.py

# Step 6: Test system
python test_enhanced_tools.py --verbose

# Optional: Run benchmarks
python test_enhanced_tools.py --benchmark

# If you need to rollback:
# python migrate_tools.py --rollback <backup_directory_name>
