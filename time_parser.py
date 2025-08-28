"""
Dummy time_parser module for backward compatibility.

This module has been removed and its functionality has been
moved directly into the task management agent.
"""

class TimeParser:
    """Dummy TimeParser class for backward compatibility."""
    
    def __init__(self, supabase=None, ai_model=None):
        """Initialize dummy time parser."""
        pass
    
    def get_parser_statistics(self):
        """Return empty statistics."""
        return {
            'total_calls': 0,
            'overall_success_rate': 0.0,
            'pattern_success_count': 0,
            'ai_success_count': 0,
            'success_count': 0
        }
    
    async def parse_time_expression(self, text, current_time=None, 
                                   user_timezone="UTC", language_hint=None):
        """Dummy method - functionality moved to task management agent."""
        return {
            'has_time_expression': False,
            'confidence': 0.0,
            'time_info': {
                'parsed_time': None,
                'type': 'deprecated',
                'description': 'Time parsing moved to task management agent'
            },
            'extracted_task': text,
            'parsing_method': 'deprecated'
        }
