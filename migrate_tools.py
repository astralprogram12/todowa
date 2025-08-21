#!/usr/bin/env python3
"""
Todowa Tools Migration Script

This script helps migrate from the basic Todowa tool system to the enhanced version.
It performs the following operations:

1. Backs up existing files
2. Validates system requirements
3. Updates tool registry and functions
4. Migrates action schemas
5. Tests the new system
6. Provides rollback capability

Usage:
    python migrate_tools.py [--dry-run] [--backup-dir BACKUP_DIR]
"""

import os
import sys
import shutil
import json
import subprocess
from datetime import datetime
from pathlib import Path
import argparse
import logging

# Set up Windows-compatible logging
class WindowsFormatter(logging.Formatter):
    def format(self, record):
        # Remove Unicode emojis for Windows compatibility
        msg = super().format(record)
        # Replace common emojis with text equivalents
        replacements = {
            '🔍': '[SEARCH]',
            '✅': '[SUCCESS]',
            '💾': '[BACKUP]',
            '📦': '[PACKAGE]',
            '🔧': '[TOOL]',
            '📋': '[SCHEMA]',
            '🧪': '[TEST]',
            '❌': '[ERROR]',
            '💥': '[FAILED]',
            '🔄': '[ROLLBACK]'
        }
        for emoji, text in replacements.items():
            msg = msg.replace(emoji, text)
        return msg

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Configure handlers with Windows-compatible formatter
file_handler = logging.FileHandler('migration.log', encoding='utf-8')
console_handler = logging.StreamHandler(sys.stdout)

formatter = WindowsFormatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

class TodowaMigration:
    """Handles the migration from basic to enhanced Todowa tool system."""
    
    def __init__(self, dry_run=False, backup_dir=None):
        self.dry_run = dry_run
        self.backup_dir = backup_dir or f"todowa_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.project_root = Path.cwd()
        self.errors = []
        self.warnings = []
        
    def run_migration(self):
        """Execute the complete migration process."""
        logger.info("Starting Todowa Tools Migration")
        logger.info(f"Dry run: {self.dry_run}")
        logger.info(f"Backup directory: {self.backup_dir}")
        
        try:
            # Phase 1: Pre-migration checks
            self.validate_environment()
            
            # Phase 2: Backup
            self.create_backup()
            
            # Phase 3: System updates
            self.update_requirements()
            self.update_tool_system()
            self.update_action_schemas()
            
            # Phase 4: Testing
            self.test_system()
            
            # Phase 5: Final validation
            self.validate_migration()
            
            logger.info("✅ Migration completed successfully!")
            self.print_summary()
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            self.handle_failure()
            raise
    
    def validate_environment(self):
        """Validate that the environment is ready for migration."""
        logger.info("🔍 Validating environment...")
        
        # Check Python version
        if sys.version_info < (3, 8):
            raise RuntimeError("Python 3.8 or higher is required")
        
        # Check for required directories
        required_dirs = [
            "src/multi_agent_system",
            "prompts/v1",
            "."
        ]
        
        for dir_path in required_dirs:
            if not (self.project_root / dir_path).exists():
                self.errors.append(f"Required directory missing: {dir_path}")
        
        # Check for existing files
        critical_files = [
            "src/multi_agent_system/tools.py",
            "src/multi_agent_system/agent_tools_mixin.py",
            "prompts/v1/01_action_schema.md"
        ]
        
        for file_path in critical_files:
            if not (self.project_root / file_path).exists():
                self.warnings.append(f"Expected file not found: {file_path}")
        
        # Check database connectivity (if possible)
        self.check_database_modules()
        
        if self.errors:
            raise RuntimeError(f"Environment validation failed: {', '.join(self.errors)}")
        
        if self.warnings:
            logger.warning(f"⚠️  Warnings: {', '.join(self.warnings)}")
        
        logger.info("✅ Environment validation passed")
    
    def check_database_modules(self):
        """Check if database modules are available."""
        try:
            sys.path.insert(0, str(self.project_root))
            import database_personal
            import database_silent
            logger.info("✅ Database modules found")
        except ImportError as e:
            self.warnings.append(f"Database modules not available: {e}")
        finally:
            if str(self.project_root) in sys.path:
                sys.path.remove(str(self.project_root))
    
    def create_backup(self):
        """Create backup of existing system."""
        logger.info(f"💾 Creating backup in {self.backup_dir}...")
        
        if self.dry_run:
            logger.info("[DRY RUN] Would create backup")
            return
        
        backup_path = Path(self.backup_dir)
        backup_path.mkdir(exist_ok=True)
        
        # Backup critical directories
        backup_items = [
            ("src/multi_agent_system", "multi_agent_system"),
            ("prompts/v1", "prompts_v1"),
            ("database_personal.py", "database_personal.py"),
            ("database_silent.py", "database_silent.py"),
            ("services.py", "services.py")
        ]
        
        for source, dest in backup_items:
            source_path = self.project_root / source
            dest_path = backup_path / dest
            
            if source_path.exists():
                if source_path.is_dir():
                    shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                else:
                    shutil.copy2(source_path, dest_path)
                logger.info(f"  Backed up: {source}")
        
        # Create backup manifest
        manifest = {
            "backup_date": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "backed_up_items": [item[0] for item in backup_items if (self.project_root / item[0]).exists()]
        }
        
        with open(backup_path / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)
        
        logger.info("✅ Backup completed")
    
    def update_requirements(self):
        """Update Python requirements."""
        logger.info("📦 Updating requirements...")
        
        new_packages = ["croniter", "pytz"]
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would install: {', '.join(new_packages)}")
            return
        
        for package in new_packages:
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", package], 
                             check=True, capture_output=True, text=True)
                logger.info(f"  Installed: {package}")
            except subprocess.CalledProcessError as e:
                logger.warning(f"  Failed to install {package}: {e}")
        
        logger.info("✅ Requirements updated")
    
    def update_tool_system(self):
        """Update the tool system files."""
        logger.info("🔧 Updating tool system...")
        
        if self.dry_run:
            logger.info("[DRY RUN] Would update tool system files")
            return
        
        # File mappings: (source, destination)
        file_updates = [
            ("code/enhanced_tools.py", "src/multi_agent_system/tools.py"),
            ("code/enhanced_ai_tools.py", "ai_tools.py"),
            ("code/enhanced_agent_tools_mixin.py", "src/multi_agent_system/agent_tools_mixin.py")
        ]
        
        for source, dest in file_updates:
            source_path = Path(source)
            dest_path = self.project_root / dest
            
            if source_path.exists():
                # Ensure destination directory exists
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file
                shutil.copy2(source_path, dest_path)
                logger.info(f"  Updated: {dest}")
            else:
                logger.warning(f"  Source file not found: {source}")
        
        logger.info("✅ Tool system updated")
    
    def update_action_schemas(self):
        """Update action schema files."""
        logger.info("📋 Updating action schemas...")
        
        if self.dry_run:
            logger.info("[DRY RUN] Would update action schemas")
            return
        
        schema_updates = [
            ("code/enhanced_action_schema.md", "prompts/v1/01_action_schema.md"),
            ("code/enhanced_action_schema.json", "prompts/v1/01_action_schema.json")
        ]
        
        for source, dest in schema_updates:
            source_path = Path(source)
            dest_path = self.project_root / dest
            
            if source_path.exists():
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, dest_path)
                logger.info(f"  Updated: {dest}")
            else:
                logger.warning(f"  Source file not found: {source}")
        
        logger.info("✅ Action schemas updated")
    
    def test_system(self):
        """Test the updated system."""
        logger.info("🧪 Testing updated system...")
        
        if self.dry_run:
            logger.info("[DRY RUN] Would run system tests")
            return
        
        # Test 1: Import updated modules
        try:
            sys.path.insert(0, str(self.project_root))
            
            # Test tool registry
            from src.multi_agent_system.tools import tool_registry
            logger.info("  ✅ Tool registry imports successfully")
            
            # Test enhanced mixin
            from src.multi_agent_system.agent_tools_mixin import EnhancedAgentToolsMixin
            logger.info("  ✅ Enhanced mixin imports successfully")
            
            # Test AI tools
            try:
                import ai_tools
                logger.info("  ✅ AI tools import successfully")
            except ImportError as e:
                logger.warning(f"  ⚠️  AI tools import warning: {e}")
            
            # Test tool registration
            available_tools = tool_registry.list_tools()
            logger.info(f"  ✅ Found {len(available_tools)} registered tools")
            
        except Exception as e:
            logger.error(f"  ❌ System test failed: {e}")
            raise
        finally:
            if str(self.project_root) in sys.path:
                sys.path.remove(str(self.project_root))
        
        # Test 2: Validate action schema
        try:
            schema_path = self.project_root / "prompts/v1/01_action_schema.json"
            if schema_path.exists():
                with open(schema_path) as f:
                    schema = json.load(f)
                logger.info(f"  ✅ Action schema valid ({len(schema.get('actions', []))} actions)")
        except Exception as e:
            logger.warning(f"  ⚠️  Action schema validation warning: {e}")
        
        logger.info("✅ System tests completed")
    
    def validate_migration(self):
        """Final validation of the migration."""
        logger.info("✅ Validating migration...")
        
        # Check that all expected files exist
        expected_files = [
            "src/multi_agent_system/tools.py",
            "src/multi_agent_system/agent_tools_mixin.py",
            "ai_tools.py",
            "prompts/v1/01_action_schema.md",
            "prompts/v1/01_action_schema.json"
        ]
        
        missing_files = []
        for file_path in expected_files:
            if not (self.project_root / file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            raise RuntimeError(f"Migration validation failed. Missing files: {', '.join(missing_files)}")
        
        logger.info("✅ Migration validation passed")
    
    def handle_failure(self):
        """Handle migration failure and offer rollback."""
        logger.error("💥 Migration failed. Rolling back...")
        
        if not self.dry_run:
            self.rollback()
    
    def rollback(self):
        """Rollback to the backed up version."""
        logger.info(f"🔄 Rolling back from backup: {self.backup_dir}")
        
        backup_path = Path(self.backup_dir)
        if not backup_path.exists():
            logger.error("Backup directory not found. Manual rollback required.")
            return
        
        # Restore files from backup
        restore_items = [
            ("multi_agent_system", "src/multi_agent_system"),
            ("prompts_v1", "prompts/v1"),
            ("database_personal.py", "database_personal.py"),
            ("database_silent.py", "database_silent.py"),
            ("services.py", "services.py")
        ]
        
        for backup_name, restore_path in restore_items:
            backup_item = backup_path / backup_name
            restore_target = self.project_root / restore_path
            
            if backup_item.exists():
                if restore_target.exists():
                    if restore_target.is_dir():
                        shutil.rmtree(restore_target)
                    else:
                        restore_target.unlink()
                
                if backup_item.is_dir():
                    shutil.copytree(backup_item, restore_target)
                else:
                    restore_target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup_item, restore_target)
                
                logger.info(f"  Restored: {restore_path}")
        
        logger.info("✅ Rollback completed")
    
    def print_summary(self):
        """Print migration summary."""
        print("\n" + "=" * 60)
        print("🎉 TODOWA TOOLS MIGRATION SUMMARY")
        print("=" * 60)
        
        print(f"✅ Migration completed successfully!")
        print(f"📁 Backup created: {self.backup_dir}")
        print(f"🔧 Tool system: Enhanced with performance monitoring")
        print(f"📋 Action schemas: Updated with comprehensive CRUD operations")
        print(f"🚀 New features: Smart categorization, auto-reminders, analytics")
        
        if self.warnings:
            print(f"\n⚠️  Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"   • {warning}")
        
        print("\n📖 Next Steps:")
        print("   1. Review the updated action schema in prompts/v1/")
        print("   2. Test tool functionality with your application")
        print("   3. Monitor performance logs for any issues")
        print("   4. Update your AI prompts to use new features")
        
        print("\n🆘 Need help?")
        print("   • Check migration.log for detailed logs")
        print("   • Review docs/todowa_tools_update_guide.md")
        print(f"   • Use rollback if needed: python migrate_tools.py --rollback {self.backup_dir}")
        
        print("=" * 60)

def main():
    parser = argparse.ArgumentParser(description="Migrate Todowa tools to enhanced version")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be done without making changes")
    parser.add_argument("--backup-dir", type=str,
                       help="Custom backup directory name")
    parser.add_argument("--rollback", type=str,
                       help="Rollback from specified backup directory")
    
    args = parser.parse_args()
    
    if args.rollback:
        # Handle rollback
        migration = TodowaMigration(backup_dir=args.rollback)
        migration.rollback()
        return
    
    # Run migration
    migration = TodowaMigration(dry_run=args.dry_run, backup_dir=args.backup_dir)
    
    try:
        migration.run_migration()
    except KeyboardInterrupt:
        logger.info("\n⚠️  Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()