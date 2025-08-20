import json
import logging
from typing import Dict, List, Any, Optional
from enhanced_ai_tools import tool_registry, set_context
from enhanced_tools import ToolMetrics

class EnhancedAgentToolsMixin:
    """
    Enhanced mixin for agent tool integration with smart features
    Provides agents with access to the enhanced tool system
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._tools_initialized = False
        
    def initialize_tools(self, supabase_client=None, user_id: str = None):
        """
        Initialize the enhanced tool system with dependency injection
        
        Args:
            supabase_client: Supabase client for database operations
            user_id: User identifier for personalized operations
        """
        try:
            if supabase_client and user_id:
                set_context(supabase_client, user_id)
                self.logger.info(f"Enhanced tools initialized for user: {user_id}")
            else:
                self.logger.warning("Tools initialized without full context")
                
            self._tools_initialized = True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize tools: {str(e)}")
            raise
    
    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a tool with enhanced error handling and logging
        
        Args:
            tool_name: Name of the tool to execute
            **kwargs: Tool parameters
        
        Returns:
            Dict containing execution result
        """
        if not self._tools_initialized:
            return {
                "success": False, 
                "error": "Tools not initialized. Call initialize_tools() first."
            }
        
        try:
            self.logger.info(f"Executing tool: {tool_name} with params: {list(kwargs.keys())}")
            result = tool_registry.execute(tool_name, **kwargs)
            
            # Log successful execution
            metrics = tool_registry.get_metrics(tool_name)
            self.logger.info(
                f"Tool '{tool_name}' executed successfully. "
                f"Total executions: {metrics.execution_count}, "
                f"Success rate: {metrics.get_success_rate():.1f}%"
            )
            
            return {"success": True, "data": result}
            
        except Exception as e:
            self.logger.error(f"Error executing tool '{tool_name}': {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_available_tools(self, category: str = None) -> List[Dict[str, Any]]:
        """
        Get list of available tools, optionally filtered by category
        
        Args:
            category: Optional category filter
        
        Returns:
            List of tool information dictionaries
        """
        if category:
            tool_names = tool_registry.get_tools_by_category(category)
            return [tool_registry.get_tool_info(name) for name in tool_names]
        else:
            return tool_registry.list_tools()
    
    def get_tool_categories(self) -> List[str]:
        """
        Get all available tool categories
        
        Returns:
            List of category names
        """
        categories = set()
        for metadata in tool_registry.tool_metadata.values():
            categories.add(metadata['category'])
        return sorted(list(categories))
    
    def get_tool_performance_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive performance report for all tools
        
        Returns:
            Dict containing performance metrics and analysis
        """
        all_metrics = tool_registry.get_all_metrics()
        
        # Calculate aggregated statistics
        total_executions = sum(m['execution_count'] for m in all_metrics.values())
        avg_success_rate = sum(m['success_rate'] for m in all_metrics.values()) / len(all_metrics) if all_metrics else 0
        
        # Find most/least used tools
        most_used = max(all_metrics.items(), key=lambda x: x[1]['execution_count']) if all_metrics else None
        least_used = min(all_metrics.items(), key=lambda x: x[1]['execution_count']) if all_metrics else None
        
        # Find fastest/slowest tools
        tools_with_time = {k: v for k, v in all_metrics.items() if v['average_execution_time'] > 0}
        fastest = min(tools_with_time.items(), key=lambda x: x[1]['average_execution_time']) if tools_with_time else None
        slowest = max(tools_with_time.items(), key=lambda x: x[1]['average_execution_time']) if tools_with_time else None
        
        report = {
            "summary": {
                "total_tools": len(all_metrics),
                "total_executions": total_executions,
                "average_success_rate": round(avg_success_rate, 2)
            },
            "usage_stats": {
                "most_used_tool": most_used[0] if most_used else None,
                "most_used_count": most_used[1]['execution_count'] if most_used else 0,
                "least_used_tool": least_used[0] if least_used else None,
                "least_used_count": least_used[1]['execution_count'] if least_used else 0
            },
            "performance_stats": {
                "fastest_tool": fastest[0] if fastest else None,
                "fastest_time": fastest[1]['average_execution_time'] if fastest else 0,
                "slowest_tool": slowest[0] if slowest else None,
                "slowest_time": slowest[1]['average_execution_time'] if slowest else 0
            },
            "detailed_metrics": all_metrics
        }
        
        return report
    
    def smart_tool_suggestion(self, intent: str, context: Dict[str, Any] = None) -> List[str]:
        """
        Suggest appropriate tools based on user intent and context
        
        Args:
            intent: User's intended action (e.g., "create task", "check reminders")
            context: Additional context information
        
        Returns:
            List of suggested tool names
        """
        intent_lower = intent.lower()
        suggestions = []
        
        # Intent-to-tool mapping
        intent_mappings = {
            "create": ["create_task", "create_reminder", "create_category"],
            "get": ["get_tasks", "get_reminders", "get_categories"],
            "update": ["update_task"],
            "delete": ["delete_task"],
            "analytics": ["get_task_analytics"],
            "validate": ["validate_cron_expression"]
        }
        
        # Find matching tools based on intent
        for key, tools in intent_mappings.items():
            if key in intent_lower:
                suggestions.extend(tools)
        
        # Context-based refinement
        if context:
            if "task" in intent_lower:
                suggestions = [t for t in suggestions if "task" in t or "analytics" in t]
            elif "reminder" in intent_lower:
                suggestions = [t for t in suggestions if "reminder" in t]
            elif "category" in intent_lower:
                suggestions = [t for t in suggestions if "category" in t]
        
        # Remove duplicates and return
        return list(set(suggestions))
    
    def bulk_execute_tools(self, operations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute multiple tool operations in sequence
        
        Args:
            operations: List of dicts with 'tool_name' and 'params' keys
        
        Returns:
            List of execution results
        """
        results = []
        
        for i, operation in enumerate(operations):
            try:
                tool_name = operation.get('tool_name')
                params = operation.get('params', {})
                
                if not tool_name:
                    results.append({
                        "operation_index": i,
                        "success": False,
                        "error": "Missing tool_name"
                    })
                    continue
                
                result = self.execute_tool(tool_name, **params)
                result["operation_index"] = i
                results.append(result)
                
            except Exception as e:
                results.append({
                    "operation_index": i,
                    "success": False,
                    "error": str(e)
                })
        
        self.logger.info(f"Bulk execution completed: {len(results)} operations")
        return results
    
    def export_tool_schema(self) -> Dict[str, Any]:
        """
        Export the complete tool schema for agent configuration
        
        Returns:
            Dict containing complete tool schema information
        """
        schema = {
            "version": "2.0",
            "generated_at": tool_registry.get_all_metrics().get('generated_at', 'unknown'),
            "categories": self.get_tool_categories(),
            "tools": {}
        }
        
        for tool_name, tool_func in tool_registry.tools.items():
            metadata = tool_registry.tool_metadata.get(tool_name, {})
            metrics = tool_registry.get_metrics(tool_name)
            
            schema["tools"][tool_name] = {
                "description": metadata.get('description', ''),
                "category": metadata.get('category', 'general'),
                "parameters": metadata.get('parameters', []),
                "auto_inject": metadata.get('auto_inject', []),
                "performance": {
                    "execution_count": metrics.execution_count,
                    "success_rate": metrics.get_success_rate(),
                    "average_execution_time": metrics.average_execution_time
                }
            }
        
        return schema
    
    def clear_tool_metrics(self):
        """
        Clear all tool performance metrics
        """
        tool_registry.clear_metrics()
        self.logger.info("All tool metrics cleared")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the tool system
        
        Returns:
            Dict containing health status information
        """
        health_status = {
            "status": "healthy",
            "initialized": self._tools_initialized,
            "total_tools": len(tool_registry.tools),
            "issues": []
        }
        
        # Check for tools with high error rates
        for tool_name, metrics in tool_registry.tool_metrics.items():
            if metrics.execution_count > 5:  # Only check tools that have been used
                success_rate = metrics.get_success_rate()
                if success_rate < 80:  # Less than 80% success rate
                    health_status["issues"].append(
                        f"Tool '{tool_name}' has low success rate: {success_rate:.1f}%"
                    )
        
        if health_status["issues"]:
            health_status["status"] = "warning"
        
        if not self._tools_initialized:
            health_status["status"] = "error"
            health_status["issues"].append("Tools not properly initialized")
        
        return health_status
