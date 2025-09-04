"""
Deprecated Time Parser Module.

This module is kept for backward compatibility purposes only. The functionality
for parsing time expressions from user input has been integrated directly into
the `TaskManagementAgent` and other relevant agents that handle time-sensitive
information.

This ensures that time parsing is handled within the context of the specific
task, leading to more accurate and context-aware interpretations.
"""

class TimeParser:
    """
    A dummy TimeParser class for backward compatibility.

    This class and its methods are deprecated and should not be used in new
    implementations.
    """
    
    def __init__(self, supabase=None, ai_model=None):
        """
        Initializes the dummy time parser. This is a no-op.

        Args:
            supabase: Ignored.
            ai_model: Ignored.
        """
        pass
    
    def get_parser_statistics(self) -> dict:
        """
        Returns empty statistics, as this parser is no longer in use.

        Returns:
            A dictionary with zero-value statistics.
        """
        return {
            'total_calls': 0,
            'overall_success_rate': 0.0,
            'pattern_success_count': 0,
            'ai_success_count': 0,
            'success_count': 0
        }
    
    async def parse_time_expression(self, text: str, current_time=None,
                                   user_timezone: str = "UTC", language_hint=None) -> dict:
        """
        A dummy method indicating that the time parsing functionality is deprecated.

        Args:
            text: The text to parse.
            current_time: Ignored.
            user_timezone: Ignored.
            language_hint: Ignored.

        Returns:
            A dictionary indicating that the feature is deprecated.
        """
        return {
            'has_time_expression': False,
            'confidence': 0.0,
            'time_info': {
                'parsed_time': None,
                'type': 'deprecated',
                'description': 'Time parsing functionality has been moved into the relevant agents.'
            },
            'extracted_task': text,
            'parsing_method': 'deprecated'
        }
