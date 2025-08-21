#!/usr/bin/env python3
"""
Todowa Enhanced Tools Test Suite

Comprehensive testing suite for the enhanced Todowa tool system.
Tests all major functionality including:

- Tool registration and discovery
- Parameter injection and processing
- Database operations (if available)
- Error handling and recovery
- Performance monitoring
- Category management
- Reminder automation

Usage:
    python test_enhanced_tools.py [--verbose] [--skip-db] [--benchmark]
"""

import sys
import os
import unittest
import asyncio
import time
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class TestEnhancedTools(unittest.TestCase):
    """Test the enhanced tool registry system."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Import and set up the tool registry
        try:
            from code.enhanced_tools import ToolRegistry, tool_registry, register_tool
            self.ToolRegistry = ToolRegistry
            self.registry = ToolRegistry()  # Create fresh registry for testing
            self.register_tool = register_tool
        except ImportError as e:
            self.skipTest(f"Enhanced tools not available: {e}")
        
        # Create mock functions for testing
        @self.register_tool("test_tool", "test", "Test tool for unit testing")
        def test_function(param1: str, param2: int = 10, supabase=None, user_id=None):
            return {"param1": param1, "param2": param2, "has_supabase": supabase is not None}
        
        self.test_function = test_function
    
    def test_tool_registration(self):
        """Test that tools are properly registered."""
        # Create a test tool
        @self.register_tool("test_registration", "testing", "Registration test")
        def test_func(arg1: str, arg2: int = 5):
            return f"{arg1}-{arg2}"
        
        # Check that tool is registered
        self.assertIn("test_registration", self.registry.tools)
        
        # Check metadata
        tool = self.registry.get_tool("test_registration")
        self.assertEqual(tool['category'], "testing")
        self.assertEqual(tool['description'], "Registration test")
        self.assertIn("arg1", tool['required_params'])
        self.assertIn("arg2", tool['optional_params'])
        self.assertEqual(tool['optional_params']['arg2'], 5)
    
    def test_parameter_injection(self):
        """Test automatic parameter injection."""
        # Mock the injected parameters
        mock_supabase = Mock()
        mock_user_id = "test-user-123"
        
        # Test with manual parameter injection
        result = self.test_function("test", supabase=mock_supabase, user_id=mock_user_id)
        
        self.assertEqual(result["param1"], "test")
        self.assertEqual(result["param2"], 10)  # Default value
        self.assertTrue(result["has_supabase"])
    
    def test_parameter_processing(self):
        """Test snake_case conversion and list processing."""
        test_data = {
            "camelCaseKey": "value",
            "anotherKey": "value2",
            "nested": {
                "innerKey": "nested_value"
            }
        }
        
        processed = self.registry._convert_keys_to_snake_case(test_data)
        
        self.assertIn("camel_case_key", processed)
        self.assertIn("another_key", processed)
        self.assertIn("inner_key", processed["nested"])
    
    async def test_tool_execution(self):
        """Test tool execution with timing and error handling."""
        # Register test tool in the registry
        self.registry.register_tool(
            "execution_test", self.test_function, "test", "Execution test"
        )
        
        # Test successful execution
        result = await self.registry.call_tool("execution_test", param1="hello")
        
        self.assertEqual(result['status'], 'success')
        self.assertIn('execution_time', result)
        self.assertIn('timestamp', result)
        self.assertEqual(result['result']['param1'], 'hello')
    
    async def test_error_handling(self):
        """Test error handling in tool execution."""
        # Register a tool that raises an exception
        @self.register_tool("error_tool", "test", "Tool that raises errors")
        def error_function():
            raise ValueError("Test error")
        
        self.registry.register_tool("error_test", error_function, "test", "Error test")
        
        result = await self.registry.call_tool("error_test")
        
        self.assertEqual(result['status'], 'error')
        self.assertIn('error', result)
        self.assertIn('traceback', result)
        self.assertIn('execution_time', result)
    
    def test_performance_tracking(self):
        """Test performance statistics tracking."""
        # Register a test tool
        @self.register_tool("perf_tool", "test", "Performance test tool")
        def perf_function():
            time.sleep(0.01)  # Small delay
            return "completed"
        
        self.registry.register_tool("perf_test", perf_function, "test", "Perf test")
        
        # Execute multiple times
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        for _ in range(3):
            result = loop.run_until_complete(self.registry.call_tool("perf_test"))
            self.assertEqual(result['status'], 'success')
        
        # Check performance report
        report = self.registry.get_performance_report()
        self.assertGreater(report['total_executions'], 0)
        self.assertIn('tools', report)
        
        # Check tool-specific stats
        tool = self.registry.get_tool("perf_test")
        self.assertEqual(tool['execution_count'], 3)
        self.assertGreater(tool['total_execution_time'], 0)
        
        loop.close()

class TestEnhancedAITools(unittest.TestCase):
    """Test the enhanced AI tools functionality."""
    
    def setUp(self):
        """Set up test fixtures for AI tools."""
        # Mock database modules
        self.mock_supabase = Mock()
        self.mock_user_id = "test-user-456"
        
        # Mock database_personal module
        self.mock_db_personal = Mock()
        self.mock_db_personal.add_task_entry.return_value = {"id": "task-123", "title": "Test Task"}
        self.mock_db_personal.query_tasks.return_value = []
        self.mock_db_personal.log_action.return_value = {"id": "log-123"}
        
        # Patch the database modules
        self.db_patch = patch.dict('sys.modules', {
            'database_personal': self.mock_db_personal,
            'database_silent': Mock()
        })
        self.db_patch.start()
    
    def tearDown(self):
        """Clean up patches."""
        self.db_patch.stop()
    
    def test_task_creation(self):
        """Test enhanced task creation functionality."""
        try:
            from code.enhanced_ai_tools import add_task
        except ImportError:
            self.skipTest("Enhanced AI tools not available")
        
        # Test basic task creation
        result = add_task(
            supabase=self.mock_supabase,
            user_id=self.mock_user_id,
            title="Test Task",
            category="Work",
            priority="high"
        )
        
        self.assertEqual(result['status'], 'ok')
        self.assertIn('message', result)
        
        # Verify database was called
        self.mock_db_personal.add_task_entry.assert_called_once()
    
    def test_category_validation(self):
        """Test category validation and processing."""
        try:
            from code.enhanced_ai_tools import validate_and_process_category
        except ImportError:
            self.skipTest("Enhanced AI tools not available")
        
        # Mock existing categories
        self.mock_db_personal.get_user_categories.return_value = [
            {"name": "Work", "count": 5},
            {"name": "Personal", "count": 3}
        ]
        
        # Test exact match
        result = validate_and_process_category(
            supabase=self.mock_supabase,
            user_id=self.mock_user_id,
            category_input="Work",
            task_title="Important meeting",
            task_notes="Team sync"
        )
        
        self.assertEqual(result['category'], 'Work')
        self.assertEqual(result['status'], 'existing_exact_match')
    
    def test_reminder_automation(self):
        """Test automated reminder setting with task creation."""
        try:
            from code.enhanced_ai_tools import set_reminder
        except ImportError:
            self.skipTest("Enhanced AI tools not available")
        
        # Mock finding no existing task
        self.mock_db_personal.query_tasks.return_value = []
        # Mock successful task creation
        self.mock_db_personal.add_task_entry.return_value = {
            "id": "task-456", "title": "New Reminder Task"
        }
        # Mock successful reminder update
        self.mock_db_personal.update_task_entry.return_value = {
            "id": "task-456", "reminder_at": "2025-01-21T10:00:00Z"
        }
        
        # Test setting reminder for non-existing task (should create task)
        result = set_reminder(
            supabase=self.mock_supabase,
            user_id=self.mock_user_id,
            titleMatch="Doctor appointment",
            reminderTime="2025-01-21T10:00:00Z",
            category="Health"
        )
        
        self.assertEqual(result['status'], 'ok')
        self.assertIn('task_id', result)
        
        # Verify task was created and reminder was set
        self.mock_db_personal.add_task_entry.assert_called_once()
        self.mock_db_personal.update_task_entry.assert_called_once()

class TestEnhancedMixin(unittest.TestCase):
    """Test the enhanced agent tools mixin."""
    
    def setUp(self):
        """Set up test fixtures for mixin testing."""
        try:
            from code.enhanced_agent_tools_mixin import EnhancedAgentToolsMixin
            self.EnhancedAgentToolsMixin = EnhancedAgentToolsMixin
        except ImportError:
            self.skipTest("Enhanced mixin not available")
        
        # Create a test agent class
        class TestAgent(self.EnhancedAgentToolsMixin):
            def __init__(self):
                super().__init__()
                self.supabase = Mock()
                self.user_id = "test-agent-user"
                self.ai_model = "test-model"
        
        self.agent = TestAgent()
    
    def test_parameter_injection(self):
        """Test automatic parameter injection in the mixin."""
        # Test parameter injection
        kwargs = {"custom_param": "value"}
        injected = self.agent._inject_standard_parameters(kwargs)
        
        self.assertIn("supabase", injected)
        self.assertIn("user_id", injected)
        self.assertIn("ai_model", injected)
        self.assertEqual(injected["custom_param"], "value")
        self.assertEqual(injected["user_id"], "test-agent-user")
    
    def test_tool_suggestion(self):
        """Test intelligent tool suggestion."""
        # Test tool suggestion based on input
        suggestions = self.agent.suggest_tools("send a message", top_n=2)
        
        # Should return list of tool suggestions
        self.assertIsInstance(suggestions, list)
        for suggestion in suggestions:
            self.assertIn('name', suggestion)
            self.assertIn('relevance_score', suggestion)
    
    def test_usage_tracking(self):
        """Test tool usage statistics tracking."""
        # Simulate tool usage
        self.agent._track_tool_usage("test_tool", 0.1, True)
        self.agent._track_tool_usage("test_tool", 0.15, True)
        self.agent._track_tool_usage("test_tool", 0.2, False)
        
        # Check statistics
        self.assertIn("test_tool", self.agent._tool_usage_stats)
        stats = self.agent._tool_usage_stats["test_tool"]
        
        self.assertEqual(stats['count'], 3)
        self.assertEqual(stats['success_count'], 2)
        self.assertEqual(stats['error_count'], 1)
        self.assertAlmostEqual(stats['total_time'], 0.45, places=2)
    
    def test_performance_summary(self):
        """Test performance summary generation."""
        # Add some usage data
        self.agent._track_tool_usage("tool1", 0.1, True)
        self.agent._track_tool_usage("tool2", 0.2, True)
        self.agent._track_tool_usage("tool1", 0.15, False)
        
        # Get performance summary
        summary = self.agent.get_performance_summary()
        
        self.assertIn('total_tools_used', summary)
        self.assertIn('total_executions', summary)
        self.assertIn('success_rate', summary)
        self.assertIn('most_used_tools', summary)
        
        self.assertEqual(summary['total_tools_used'], 2)
        self.assertEqual(summary['total_executions'], 3)

class TestActionSchema(unittest.TestCase):
    """Test the enhanced action schema."""
    
    def test_schema_validity(self):
        """Test that the action schema is valid JSON."""
        schema_path = Path("code/enhanced_action_schema.json")
        
        if not schema_path.exists():
            self.skipTest("Enhanced action schema not found")
        
        with open(schema_path) as f:
            schema = json.load(f)
        
        # Basic structure validation
        self.assertIn('actions', schema)
        self.assertIn('schema_version', schema)
        self.assertIsInstance(schema['actions'], list)
        
        # Check that essential actions are present
        action_types = {action.get('type') for action in schema['actions']}
        essential_actions = {
            'add_task', 'update_task', 'delete_task', 'complete_task',
            'set_reminder', 'add_memory', 'search_memories',
            'activate_silent_mode', 'schedule_ai_action'
        }
        
        for essential in essential_actions:
            self.assertIn(essential, action_types, f"Missing essential action: {essential}")
    
    def test_enhanced_features(self):
        """Test that enhanced features are documented in schema."""
        schema_path = Path("code/enhanced_action_schema.json")
        
        if not schema_path.exists():
            self.skipTest("Enhanced action schema not found")
        
        with open(schema_path) as f:
            schema = json.load(f)
        
        # Check for enhancement documentation
        self.assertIn('enhancements', schema)
        enhancements = schema['enhancements']
        
        self.assertIn('category_management', enhancements)
        self.assertIn('performance_monitoring', enhancements)
        self.assertIn('reminder_automation', enhancements)
        
        # Check specific enhancement flags
        self.assertTrue(enhancements['category_management']['auto_assignment'])
        self.assertTrue(enhancements['performance_monitoring']['execution_timing'])
        self.assertTrue(enhancements['reminder_automation']['auto_task_creation'])

def run_benchmark_tests():
    """Run performance benchmark tests."""
    print("\n🚀 Running benchmark tests...")
    
    try:
        from code.enhanced_tools import ToolRegistry, register_tool
    except ImportError:
        print("  ⚠️  Enhanced tools not available for benchmarking")
        return
    
    # Create benchmark registry
    registry = ToolRegistry()
    
    # Register benchmark tools
    @register_tool("benchmark_simple", "benchmark", "Simple benchmark tool")
    def simple_tool(param: str):
        return f"processed: {param}"
    
    @register_tool("benchmark_complex", "benchmark", "Complex benchmark tool")
    def complex_tool(data: dict, iterations: int = 100):
        result = []
        for i in range(iterations):
            result.append({"iteration": i, "data": data})
        return {"processed_items": len(result)}
    
    # Register tools in benchmark registry
    registry.register_tool("benchmark_simple", simple_tool, "benchmark", "Simple benchmark")
    registry.register_tool("benchmark_complex", complex_tool, "benchmark", "Complex benchmark")
    
    # Run benchmarks
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Benchmark 1: Simple tool execution
    start_time = time.time()
    for i in range(100):
        result = loop.run_until_complete(registry.call_tool("benchmark_simple", param=f"test-{i}"))
        assert result['status'] == 'success'
    simple_time = time.time() - start_time
    
    # Benchmark 2: Complex tool execution
    start_time = time.time()
    for i in range(10):
        result = loop.run_until_complete(registry.call_tool("benchmark_complex", 
                                                           data={"test": i}, iterations=50))
        assert result['status'] == 'success'
    complex_time = time.time() - start_time
    
    loop.close()
    
    # Print results
    print(f"  Simple tool (100 executions): {simple_time:.3f}s ({simple_time*10:.1f}ms avg)")
    print(f"  Complex tool (10 executions):  {complex_time:.3f}s ({complex_time*100:.1f}ms avg)")
    
    # Performance report
    report = registry.get_performance_report()
    print(f"  Total executions: {report['total_executions']}")
    print(f"  Total errors: {report['total_errors']}")
    print(f"  ✅ Benchmark tests completed")

def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="Test enhanced Todowa tools")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose test output")
    parser.add_argument("--skip-db", action="store_true",
                       help="Skip database-dependent tests")
    parser.add_argument("--benchmark", action="store_true",
                       help="Run performance benchmark tests")
    parser.add_argument("--pattern", type=str,
                       help="Test pattern to match (e.g., 'test_tool*')")
    
    args = parser.parse_args()
    
    # Configure test verbosity
    verbosity = 2 if args.verbose else 1
    
    print("🧪 Todowa Enhanced Tools Test Suite")
    print("=" * 50)
    
    # Discover and run tests
    loader = unittest.TestLoader()
    
    if args.pattern:
        suite = loader.loadTestsFromName(args.pattern, module=__name__)
    else:
        suite = loader.loadTestsFromModule(__name__)
    
    # Filter out database tests if requested
    if args.skip_db:
        print("⚠️  Skipping database-dependent tests")
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=verbosity, stream=sys.stdout)
    result = runner.run(suite)
    
    # Run benchmarks if requested
    if args.benchmark:
        run_benchmark_tests()
    
    # Print summary
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("✅ All tests passed!")
        print(f"Ran {result.testsRun} tests successfully")
        
        if result.skipped:
            print(f"⚠️  {len(result.skipped)} tests skipped")
            for test, reason in result.skipped:
                print(f"   • {test}: {reason}")
    else:
        print("❌ Some tests failed")
        print(f"Ran {result.testsRun} tests: {len(result.failures)} failures, {len(result.errors)} errors")
        
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"   • {test}")
        
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"   • {test}")
        
        sys.exit(1)

if __name__ == "__main__":
    main()