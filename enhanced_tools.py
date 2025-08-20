import time
import logging
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json

@dataclass
class ToolMetrics:
    """Performance metrics for tool execution"""
    execution_count: int = 0
    total_execution_time: float = 0.0
    success_count: int = 0
    error_count: int = 0
    last_execution: Optional[datetime] = None
    average_execution_time: float = 0.0
    
    def update(self, execution_time: float, success: bool):
        """Update metrics after tool execution"""
        self.execution_count += 1
        self.total_execution_time += execution_time
        self.last_execution = datetime.now()
        
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
            
        self.average_execution_time = self.total_execution_time / self.execution_count
    
    def get_success_rate(self) -> float:
        """Calculate success rate as percentage"""
        if self.execution_count == 0:
            return 0.0
        return (self.success_count / self.execution_count) * 100

class EnhancedToolRegistry:
    """Enhanced tool registry with performance monitoring and analytics"""
    
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.tool_metadata: Dict[str, Dict[str, Any]] = {}
        self.tool_metrics: Dict[str, ToolMetrics] = {}
        self.logger = logging.getLogger(__name__)
        
    def register(self, name: str, func: Callable, 
                description: str = "", 
                category: str = "general",
                parameters: List[str] = None,
                auto_inject: List[str] = None):
        """Register a tool with enhanced metadata"""
        self.tools[name] = func
        self.tool_metadata[name] = {
            'description': description,
            'category': category,
            'parameters': parameters or [],
            'auto_inject': auto_inject or [],
            'registered_at': datetime.now().isoformat()
        }
        self.tool_metrics[name] = ToolMetrics()
        self.logger.info(f"Registered tool: {name} in category: {category}")
    
    def execute(self, name: str, *args, **kwargs) -> Any:
        """Execute a tool with performance monitoring"""
        if name not in self.tools:
            raise ValueError(f"Tool '{name}' not found")
        
        start_time = time.time()
        success = False
        result = None
        
        try:
            # Auto-inject common parameters if specified
            auto_inject = self.tool_metadata[name].get('auto_inject', [])
            if auto_inject and hasattr(self, '_injection_context'):
                for param in auto_inject:
                    if param in self._injection_context and param not in kwargs:
                        kwargs[param] = self._injection_context[param]
            
            result = self.tools[name](*args, **kwargs)
            success = True
            
        except Exception as e:
            self.logger.error(f"Error executing tool '{name}': {str(e)}")
            raise
        finally:
            execution_time = time.time() - start_time
            self.tool_metrics[name].update(execution_time, success)
            
        return result
    
    def set_injection_context(self, context: Dict[str, Any]):
        """Set context for auto-parameter injection"""
        self._injection_context = context
    
    def get_metrics(self, name: str) -> ToolMetrics:
        """Get performance metrics for a tool"""
        return self.tool_metrics.get(name, ToolMetrics())
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get performance metrics for all tools"""
        metrics = {}
        for name, metric in self.tool_metrics.items():
            metrics[name] = {
                'execution_count': metric.execution_count,
                'total_execution_time': metric.total_execution_time,
                'success_rate': metric.get_success_rate(),
                'average_execution_time': metric.average_execution_time,
                'last_execution': metric.last_execution.isoformat() if metric.last_execution else None
            }
        return metrics
    
    def get_tools_by_category(self, category: str) -> List[str]:
        """Get all tools in a specific category"""
        return [name for name, metadata in self.tool_metadata.items() 
                if metadata['category'] == category]
    
    def get_tool_info(self, name: str) -> Dict[str, Any]:
        """Get detailed information about a tool"""
        if name not in self.tools:
            return None
        
        return {
            'name': name,
            'metadata': self.tool_metadata[name],
            'metrics': {
                'execution_count': self.tool_metrics[name].execution_count,
                'success_rate': self.tool_metrics[name].get_success_rate(),
                'average_execution_time': self.tool_metrics[name].average_execution_time
            }
        }
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools with their info"""
        return [self.get_tool_info(name) for name in self.tools.keys()]
    
    def export_metrics(self, filepath: str):
        """Export metrics to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(self.get_all_metrics(), f, indent=2, default=str)
    
    def clear_metrics(self):
        """Clear all performance metrics"""
        for name in self.tool_metrics:
            self.tool_metrics[name] = ToolMetrics()
        self.logger.info("All tool metrics cleared")

# Global tool registry instance
tool_registry = EnhancedToolRegistry()

# Decorator for easy tool registration
def tool(name: str = None, description: str = "", 
         category: str = "general", 
         auto_inject: List[str] = None):
    """Decorator to register a function as a tool"""
    def decorator(func: Callable):
        tool_name = name or func.__name__
        import inspect
        params = list(inspect.signature(func).parameters.keys())
        
        tool_registry.register(
            name=tool_name,
            func=func,
            description=description,
            category=category,
            parameters=params,
            auto_inject=auto_inject or []
        )
        return func
    return decorator
