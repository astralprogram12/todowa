#!/usr/bin/env python3
"""
V4.0 Database Integration Test Suite
Tests all v4.0 database functions and enhanced AI tools integration
"""

import os
import sys
import json
from datetime import datetime, timedelta
from uuid import uuid4

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_test_results():
    """Initialize test results structure"""
    return {
        "test_suite": "V4.0 Database Integration",
        "timestamp": datetime.now().isoformat(),
        "results": {
            "database_functions": {},
            "ai_tools": {},
            "migration": {},
            "integration": {}
        },
        "summary": {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": []
        }
    }

def run_database_function_tests(results):
    """Test v4.0 database functions"""
    print("🧪 Testing V4.0 Database Functions...")
    
    try:
        # Import database functions
        from database_personal import (
            add_journal_entry, query_journal_entries, update_journal_entry, 
            analyze_mood_patterns, add_memory_entry, search_memories, 
            get_memory_timeline, classify_and_store_content, 
            get_classification_history, analyze_memory_relationships
        )
        
        # Mock Supabase client for testing
        class MockSupabase:
            def table(self, table_name):
                return MockTable(table_name)
        
        class MockTable:
            def __init__(self, table_name):
                self.table_name = table_name
                self.mock_data = []
            
            def insert(self, data):
                return MockResult([{**data, 'id': str(uuid4()), 'created_at': datetime.now().isoformat()}])
            
            def select(self, columns="*"):
                return MockQuery(self.mock_data)
                
            def update(self, data):
                return MockQuery([data])
                
            def delete(self):
                return MockQuery([])
        
        class MockQuery:
            def __init__(self, data):
                self.data = data
            
            def eq(self, column, value):
                return self
            
            def ilike(self, column, pattern):
                return self
                
            def or_(self, condition):
                return self
                
            def gte(self, column, value):
                return self
                
            def lte(self, column, value):
                return self
                
            def order(self, column, desc=False):
                return self
                
            def limit(self, n):
                return self
                
            def not_(self):
                return self
                
            def is_(self, column, value):
                return self
                
            def execute(self):
                return MockResult(self.data)
        
        class MockResult:
            def __init__(self, data):
                self.data = data
                self.error = None
        
        mock_supabase = MockSupabase()
        test_user_id = str(uuid4())
        
        # Test journal functions
        tests = [
            ("add_journal_entry", lambda: add_journal_entry(
                mock_supabase, test_user_id, "Test Journal", "This is a test journal entry", 
                mood_score=7.5, emotional_tone="positive"
            )),
            ("query_journal_entries", lambda: query_journal_entries(
                mock_supabase, test_user_id, limit=10
            )),
            ("analyze_mood_patterns", lambda: analyze_mood_patterns(
                mock_supabase, test_user_id, days=30
            )),
            ("add_memory_entry", lambda: add_memory_entry(
                mock_supabase, test_user_id, "Test Memory", "This is a test memory",
                memory_type="experience", importance_score=0.8
            )),
            ("search_memories", lambda: search_memories(
                mock_supabase, test_user_id, "test", limit=5
            )),
            ("get_memory_timeline", lambda: get_memory_timeline(
                mock_supabase, test_user_id, limit=20
            )),
            ("classify_and_store_content", lambda: classify_and_store_content(
                mock_supabase, test_user_id, "Today I feel great and happy"
            )),
            ("get_classification_history", lambda: get_classification_history(
                mock_supabase, test_user_id, limit=10
            )),
            ("analyze_memory_relationships", lambda: analyze_memory_relationships(
                mock_supabase, test_user_id
            ))
        ]
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                results["results"]["database_functions"][test_name] = {
                    "status": "PASSED", 
                    "result": "Function executed successfully",
                    "details": str(result)[:200] + "..." if len(str(result)) > 200 else str(result)
                }
                results["summary"]["passed"] += 1
            except Exception as e:
                results["results"]["database_functions"][test_name] = {
                    "status": "FAILED", 
                    "error": str(e)
                }
                results["summary"]["failed"] += 1
                results["summary"]["errors"].append(f"Database function {test_name}: {str(e)}")
            
            results["summary"]["total_tests"] += 1
        
        print(f"✅ Database function tests completed: {len([r for r in results['results']['database_functions'].values() if r['status'] == 'PASSED'])}/{len(tests)} passed")
        
    except ImportError as e:
        error_msg = f"Failed to import database functions: {str(e)}"
        results["results"]["database_functions"]["import_error"] = {"status": "FAILED", "error": error_msg}
        results["summary"]["failed"] += 1
        results["summary"]["errors"].append(error_msg)
        results["summary"]["total_tests"] += 1
        print(f"❌ Database function import failed: {str(e)}")

def run_ai_tools_tests(results):
    """Test v4.0 AI tools integration"""
    print("🤖 Testing V4.0 AI Tools Integration...")
    
    try:
        # Import enhanced_ai_tools
        from enhanced_ai_tools import (
            create_journal_entry, get_journal_entries, analyze_mood_patterns,
            create_memory, search_memories, get_memory_timeline, analyze_memory_relationships,
            classify_content, get_classification_history
        )
        
        # Check if tools are properly registered
        from enhanced_tools import tool_registry
        
        v4_tools = [
            "create_journal_entry", "get_journal_entries", "analyze_mood_patterns",
            "create_memory", "search_memories", "get_memory_timeline", 
            "analyze_memory_relationships", "classify_content", "get_classification_history"
        ]
        
        for tool_name in v4_tools:
            if tool_name in tool_registry:
                results["results"]["ai_tools"][tool_name] = {
                    "status": "PASSED",
                    "result": "Tool registered successfully",
                    "category": tool_registry[tool_name].get("category", "unknown")
                }
                results["summary"]["passed"] += 1
            else:
                results["results"]["ai_tools"][tool_name] = {
                    "status": "FAILED",
                    "error": "Tool not found in registry"
                }
                results["summary"]["failed"] += 1
                results["summary"]["errors"].append(f"AI tool {tool_name} not registered")
            
            results["summary"]["total_tests"] += 1
        
        # Test tool function definitions
        tool_functions = [
            create_journal_entry, get_journal_entries, analyze_mood_patterns,
            create_memory, search_memories, get_memory_timeline, analyze_memory_relationships,
            classify_content, get_classification_history
        ]
        
        functions_test = "ai_tool_functions"
        if all(callable(func) for func in tool_functions):
            results["results"]["ai_tools"][functions_test] = {
                "status": "PASSED",
                "result": f"All {len(tool_functions)} tool functions are callable"
            }
            results["summary"]["passed"] += 1
        else:
            results["results"]["ai_tools"][functions_test] = {
                "status": "FAILED",
                "error": "Some tool functions are not callable"
            }
            results["summary"]["failed"] += 1
            results["summary"]["errors"].append("AI tool functions not callable")
        
        results["summary"]["total_tests"] += 1
        
        print(f"✅ AI tools tests completed: {len([r for r in results['results']['ai_tools'].values() if r['status'] == 'PASSED'])}/{len(v4_tools) + 1} passed")
        
    except ImportError as e:
        error_msg = f"Failed to import AI tools: {str(e)}"
        results["results"]["ai_tools"]["import_error"] = {"status": "FAILED", "error": error_msg}
        results["summary"]["failed"] += 1
        results["summary"]["errors"].append(error_msg)
        results["summary"]["total_tests"] += 1
        print(f"❌ AI tools import failed: {str(e)}")

def run_migration_tests(results):
    """Test v4.0 migration script"""
    print("🔄 Testing V4.0 Migration Script...")
    
    try:
        # Check if migration file exists
        migration_path = "/workspace/updated_cli_version/database/v4_migration.sql"
        if os.path.exists(migration_path):
            with open(migration_path, 'r') as f:
                migration_content = f.read()
            
            # Check for required tables
            required_tables = ['content_classifications', 'journal_entries', 'memories', 'daily_mood_tracking']
            
            for table in required_tables:
                if f"CREATE TABLE IF NOT EXISTS {table}" in migration_content:
                    results["results"]["migration"][f"{table}_creation"] = {
                        "status": "PASSED",
                        "result": f"Table {table} creation script found"
                    }
                    results["summary"]["passed"] += 1
                else:
                    results["results"]["migration"][f"{table}_creation"] = {
                        "status": "FAILED",
                        "error": f"Table {table} creation script missing"
                    }
                    results["summary"]["failed"] += 1
                    results["summary"]["errors"].append(f"Migration missing table {table}")
                
                results["summary"]["total_tests"] += 1
            
            # Check for indexes
            if "CREATE INDEX" in migration_content:
                results["results"]["migration"]["indexes"] = {
                    "status": "PASSED",
                    "result": "Index creation scripts found"
                }
                results["summary"]["passed"] += 1
            else:
                results["results"]["migration"]["indexes"] = {
                    "status": "FAILED",
                    "error": "No index creation scripts found"
                }
                results["summary"]["failed"] += 1
                results["summary"]["errors"].append("Migration missing indexes")
            
            results["summary"]["total_tests"] += 1
            
            print(f"✅ Migration tests completed: {len([r for r in results['results']['migration'].values() if r['status'] == 'PASSED'])}/{len(required_tables) + 1} passed")
        else:
            results["results"]["migration"]["file_exists"] = {
                "status": "FAILED",
                "error": "Migration file not found"
            }
            results["summary"]["failed"] += 1
            results["summary"]["errors"].append("Migration file missing")
            results["summary"]["total_tests"] += 1
            print("❌ Migration file not found")
            
    except Exception as e:
        error_msg = f"Migration test error: {str(e)}"
        results["results"]["migration"]["error"] = {"status": "FAILED", "error": error_msg}
        results["summary"]["failed"] += 1
        results["summary"]["errors"].append(error_msg)
        results["summary"]["total_tests"] += 1
        print(f"❌ Migration test failed: {str(e)}")

def run_integration_tests(results):
    """Test v4.0 integration between components"""
    print("🔗 Testing V4.0 Component Integration...")
    
    try:
        # Test database-tools integration
        integration_tests = [
            ("database_import", "Can import database_personal module"),
            ("ai_tools_import", "Can import enhanced_ai_tools module"),
            ("schema_file", "V4.0 schema file exists"),
            ("migration_file", "V4.0 migration file exists")
        ]
        
        for test_name, description in integration_tests:
            try:
                if test_name == "database_import":
                    import database_personal
                    results["results"]["integration"][test_name] = {
                        "status": "PASSED",
                        "result": description
                    }
                elif test_name == "ai_tools_import":
                    import enhanced_ai_tools
                    results["results"]["integration"][test_name] = {
                        "status": "PASSED",
                        "result": description
                    }
                elif test_name == "schema_file":
                    schema_path = "/workspace/updated_cli_version/database/v4_0_schema.sql"
                    if os.path.exists(schema_path):
                        results["results"]["integration"][test_name] = {
                            "status": "PASSED",
                            "result": description
                        }
                    else:
                        raise FileNotFoundError("Schema file not found")
                elif test_name == "migration_file":
                    migration_path = "/workspace/updated_cli_version/database/v4_migration.sql"
                    if os.path.exists(migration_path):
                        results["results"]["integration"][test_name] = {
                            "status": "PASSED",
                            "result": description
                        }
                    else:
                        raise FileNotFoundError("Migration file not found")
                
                results["summary"]["passed"] += 1
                
            except Exception as e:
                results["results"]["integration"][test_name] = {
                    "status": "FAILED",
                    "error": str(e)
                }
                results["summary"]["failed"] += 1
                results["summary"]["errors"].append(f"Integration {test_name}: {str(e)}")
            
            results["summary"]["total_tests"] += 1
        
        print(f"✅ Integration tests completed: {len([r for r in results['results']['integration'].values() if r['status'] == 'PASSED'])}/{len(integration_tests)} passed")
        
    except Exception as e:
        error_msg = f"Integration test error: {str(e)}"
        results["results"]["integration"]["error"] = {"status": "FAILED", "error": error_msg}
        results["summary"]["failed"] += 1
        results["summary"]["errors"].append(error_msg)
        results["summary"]["total_tests"] += 1
        print(f"❌ Integration test failed: {str(e)}")

def generate_report(results):
    """Generate comprehensive test report"""
    print("\n" + "="*60)
    print("📊 V4.0 DATABASE INTEGRATION TEST REPORT")
    print("="*60)
    
    print(f"🕐 Timestamp: {results['timestamp']}")
    print(f"📊 Total Tests: {results['summary']['total_tests']}")
    print(f"✅ Passed: {results['summary']['passed']}")
    print(f"❌ Failed: {results['summary']['failed']}")
    print(f"📈 Success Rate: {(results['summary']['passed'] / results['summary']['total_tests'] * 100):.1f}%" if results['summary']['total_tests'] > 0 else "No tests run")
    
    if results['summary']['errors']:
        print(f"\n🚨 Errors ({len(results['summary']['errors'])}):")
        for i, error in enumerate(results['summary']['errors'][:10], 1):  # Show first 10 errors
            print(f"   {i}. {error}")
        if len(results['summary']['errors']) > 10:
            print(f"   ... and {len(results['summary']['errors']) - 10} more errors")
    
    print("\n📋 Test Categories:")
    for category, tests in results['results'].items():
        passed_count = len([t for t in tests.values() if t.get('status') == 'PASSED'])
        total_count = len(tests)
        print(f"   {category.replace('_', ' ').title()}: {passed_count}/{total_count}")
    
    # Save detailed results
    report_file = f"V4_0_DATABASE_INTEGRATION_TEST_RESULTS_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {report_file}")
    
    return results

def main():
    """Main test runner"""
    print("🚀 Starting V4.0 Database Integration Test Suite")
    print("="*60)
    
    results = create_test_results()
    
    # Run all test suites
    run_database_function_tests(results)
    run_ai_tools_tests(results)
    run_migration_tests(results)
    run_integration_tests(results)
    
    # Generate final report
    final_results = generate_report(results)
    
    # Return appropriate exit code
    return 0 if final_results['summary']['failed'] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
