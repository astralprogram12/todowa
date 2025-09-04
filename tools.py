"""
A comprehensive tool registry and execution framework.

This module provides an advanced system for registering, managing, and executing
tools within the application. It features an `EnhancedToolRegistry` that not
only stores tool functions but also tracks detailed performance metrics for each,
including execution time, success rates, and usage counts.

Key Components:
- `ToolMetrics`: A data class to hold performance data for a single tool.
- `EnhancedToolRegistry`: A singleton class that manages all tools, their
  metadata, and their performance metrics.
- `@tool`: A decorator that simplifies the process of registering a function
  with the global `tool_registry`.

The registry supports tool categorization, auto-injection of context-dependent
parameters (like a database manager), and methods for analytics and reporting.
"""
import time
import logging
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
import json

@dataclass
class ToolMetrics:
    """
    Holds performance and usage metrics for a registered tool.

    Attributes:
        execution_count (int): The total number of times the tool has been called.
        total_execution_time (float): The cumulative time spent executing the tool.
        success_count (int): The number of times the tool executed successfully.
        error_count (int): The number of times the tool raised an exception.
        last_execution (Optional[datetime]): The timestamp of the last execution.
        average_execution_time (float): The average time per execution.
    """
    execution_count: int = 0
    total_execution_time: float = 0.0
    success_count: int = 0
    error_count: int = 0
    last_execution: Optional[datetime] = None
    average_execution_time: float = 0.0
    
    def update(self, execution_time: float, success: bool):
        """
        Updates the metrics after a tool execution.

        Args:
            execution_time: The time it took for the tool to execute.
            success: A boolean indicating if the execution was successful.
        """
        self.execution_count += 1
        self.total_execution_time += execution_time
        self.last_execution = datetime.now()
        
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
            
        self.average_execution_time = self.total_execution_time / self.execution_count
    
    def get_success_rate(self) -> float:
        """
        Calculates the success rate of the tool as a percentage.

        Returns:
            The success rate, or 0.0 if the tool has not been executed.
        """
        if self.execution_count == 0:
            return 0.0
        return (self.success_count / self.execution_count) * 100

class EnhancedToolRegistry:
    """
    An advanced tool registry with performance monitoring and analytics.

    This class serves as a central repository for all tools available in the
    system. It allows for tool registration, execution, and provides a rich
    set of features for monitoring and analyzing tool performance.

    Attributes:
        tools (Dict[str, Callable]): A mapping of tool names to their functions.
        tool_metadata (Dict[str, Dict]): Stores metadata for each tool.
        tool_metrics (Dict[str, ToolMetrics]): Stores performance metrics for each tool.
        logger: The logger instance for this class.
    """
    
    def __init__(self):
        """Initializes the EnhancedToolRegistry."""
        self.tools: Dict[str, Callable] = {}
        self.tool_metadata: Dict[str, Dict[str, Any]] = {}
        self.tool_metrics: Dict[str, ToolMetrics] = {}
        self.logger = logging.getLogger(__name__)
        
    def __len__(self) -> int:
        """Returns the number of registered tools."""
        return len(self.tools)
    
    def __iter__(self):
        """Allows iteration over the names of registered tools."""
        return iter(self.tools)
    
    def __contains__(self, name: str) -> bool:
        """Checks if a tool with the given name is registered."""
        return name in self.tools
    
    def items(self):
        """
        Returns a view of the tool items for dictionary-like iteration.

        Returns:
            A list of tuples, each containing the tool name and a dictionary
            with its function and category.
        """
        return [(name, {'function': func, 'category': self.tool_metadata[name]['category']}) 
                for name, func in self.tools.items()]
    
    def register(self, name: str, func: Callable, 
                description: str = "", 
                category: str = "general",
                parameters: List[str] = None,
                auto_inject: List[str] = None):
        """
        Registers a tool with enhanced metadata.

        Args:
            name: The name to register the tool under.
            func: The callable function for the tool.
            description: A description of what the tool does.
            category: A category to group the tool under.
            parameters: A list of the tool's parameter names.
            auto_inject: A list of parameter names that should be auto-injected
                         from the context.
        """
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
        """
        Executes a tool with performance monitoring.

        Args:
            name: The name of the tool to execute.
            *args: Positional arguments for the tool function.
            **kwargs: Keyword arguments for the tool function.

        Returns:
            The result of the tool's execution.

        Raises:
            ValueError: If the tool is not found.
            Exception: Propagates exceptions from the tool's execution.
        """
        if name not in self.tools:
            raise ValueError(f"Tool '{name}' not found")
        
        start_time = time.time()
        success = False
        try:
            if hasattr(self, '_injection_context'):
                for param in self.tool_metadata[name].get('auto_inject', []):
                    if param in self._injection_context and param not in kwargs:
                        kwargs[param] = self._injection_context[param]
            
            result = self.tools[name](*args, **kwargs)
            success = True
            return result
        except Exception as e:
            self.logger.error(f"Error executing tool '{name}': {str(e)}")
            raise
        finally:
            execution_time = time.time() - start_time
            self.tool_metrics[name].update(execution_time, success)
    
    def set_injection_context(self, context: Dict[str, Any]):
        """
        Sets a context dictionary for auto-parameter injection.

        Args:
            context: A dictionary where keys are parameter names that can be
                     injected into tool calls.
        """
        self._injection_context = context
    
    def get_metrics(self, name: str) -> ToolMetrics:
        """
        Gets the performance metrics for a specific tool.

        Args:
            name: The name of the tool.

        Returns:
            A `ToolMetrics` object for the specified tool.
        """
        return self.tool_metrics.get(name, ToolMetrics())
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Gets a summary of performance metrics for all registered tools.

        Returns:
            A dictionary where keys are tool names and values are dictionaries
            of their performance metrics.
        """
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
        """
        Gets a list of all tool names in a specific category.

        Args:
            category: The category to search for.

        Returns:
            A list of tool names belonging to that category.
        """
        return [name for name, metadata in self.tool_metadata.items() 
                if metadata['category'] == category]
    
    def get_tool_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Gets detailed information about a specific tool.

        Args:
            name: The name of the tool.

        Returns:
            A dictionary containing the tool's name, metadata, and key metrics,
            or None if the tool is not found.
        """
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
        """
        Lists all registered tools with their summary information.

        Returns:
            A list of dictionaries, each representing a tool's info.
        """
        return [self.get_tool_info(name) for name in self.tools.keys()]
    
    def export_metrics(self, filepath: str):
        """
        Exports the current performance metrics for all tools to a JSON file.

        Args:
            filepath: The path to the file where metrics will be saved.
        """
        with open(filepath, 'w') as f:
            json.dump(self.get_all_metrics(), f, indent=2, default=str)
    
    def clear_metrics(self):
        """Resets all performance metrics for all tools."""
        for name in self.tool_metrics:
            self.tool_metrics[name] = ToolMetrics()
        self.logger.info("All tool metrics cleared")

# Global tool registry instance
tool_registry = EnhancedToolRegistry()

def tool(name: str = None, description: str = "", 
         category: str = "general", 
         auto_inject: List[str] = None):
    """
    A decorator to register a function as a tool in the global `tool_registry`.

    This decorator simplifies the registration process by allowing you to mark
    any function as a tool directly in the code. It automatically inspects
    the function's signature to determine its parameters.

    Args:
        name (str, optional): The name to register the tool with. If not provided,
                              the function's name is used.
        description (str, optional): A description of the tool's purpose.
        category (str, optional): The category to assign the tool to. Defaults to 'general'.
        auto_inject (List[str], optional): A list of parameter names that should be
                                           automatically injected from the context.

    Returns:
        The decorated function, which is now registered as a tool.
    """
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
