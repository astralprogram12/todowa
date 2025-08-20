# Coder Agent - handles code-related operations

from .base_agent import BaseAgent

class CoderAgent(BaseAgent):
    """Agent for handling code-related operations."""
    
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model, "CoderAgent")
    
    async def process(self, user_input, context, routing_info=None):
        """Process code-related user input and return a response.
       
        Args:
            user_input: The input text from the user
            context: The context of the conversation
            routing_info: NEW - AI classification with smart assumptions
            
        Returns:
            A response to the user input
        """
        user_id = context.get('user_id')
        
        # NEW: Apply AI assumptions to enhance processing
        enhanced_context = self._apply_ai_assumptions(context, routing_info)
        
        # NEW: Use AI assumptions if available
        if routing_info and routing_info.get('assumptions'):
            print(f"CoderAgent using AI assumptions: {routing_info['assumptions']}")
            # Use AI-suggested language if available
            language = routing_info['assumptions'].get('language')
        
        # Parse the user input to determine the code operation
        operation, detected_language = self._determine_operation(user_input)
        language = language or detected_language  # AI assumption takes priority
        
        if operation == 'generate':
            return await self._generate_code(user_id, user_input, language, context)
        elif operation == 'explain':
            return await self._explain_code(user_id, user_input, context)
        elif operation == 'debug':
            return await self._debug_code(user_id, user_input, context)
        else:
            return {
                "status": "error",
                "message": "I'm not sure what code operation you want to perform. Please try again with a clearer request."
            }
    
    def _determine_operation(self, user_input):
        """Determine the code operation and language from the user input."""
        user_input_lower = user_input.lower()
        
        # Determine operation
        operation = None
        if any(phrase in user_input_lower for phrase in ['write code', 'generate code', 'code for', 'create a script']):
            operation = 'generate'
        elif any(phrase in user_input_lower for phrase in ['explain code', 'explain this', 'what does this code do']):
            operation = 'explain'
        elif any(phrase in user_input_lower for phrase in ['debug code', 'fix code', 'help with code', 'error in code']):
            operation = 'debug'
        
        # Determine language
        language = None
        language_keywords = {
            'python': ['python', '.py'],
            'javascript': ['javascript', 'js', '.js', 'node'],
            'typescript': ['typescript', 'ts', '.ts'],
            'html': ['html', '.html'],
            'css': ['css', '.css'],
            'sql': ['sql', 'database query', 'db query'],
            'bash': ['bash', 'shell', 'terminal', 'command line']
        }
        
        for lang, keywords in language_keywords.items():
            if any(keyword in user_input_lower for keyword in keywords):
                language = lang
                break
        
        return operation, language
    
    async def _generate_code(self, user_id, user_input, language, context):
        """Generate code based on user input."""
        # Extract the code description from the user input
        description = self._extract_code_description(user_input)
        
        if not description:
            return {
                "status": "error",
                "message": "I couldn't determine what code to generate. Please provide a clear description."
            }
        
        # Log the action
        self._log_action(
            user_id=user_id,
            action_type="generate_code",
            entity_type="code",
            action_details={
                "language": language or 'python',
                "description": description
            },
            success_status=True
        )
        
        # Sample code for demonstration
        sample_code = "print('Hello, World!')" if language == 'python' else "console.log('Hello, World!');"
        
        return {
            "status": "ok",
            "message": f"Here's the {language or 'Python'} code I generated for '{description}':",
            "code": sample_code,
            "language": language or 'python'
        }
    
    def _extract_code_description(self, user_input):
        """Extract the code description from the user input."""
        user_input_lower = user_input.lower()
        
        # Look for description indicators
        description_indicators = ['code for', 'generate code for', 'write code for', 'create a script for']
        for indicator in description_indicators:
            if indicator in user_input_lower:
                parts = user_input_lower.split(indicator, 1)
                if len(parts) > 1:
                    return parts[1].strip()
        
        # If no specific indicators are found, use the entire input
        # minus common prefixes like "write code" or "generate code"
        common_prefixes = ['write code', 'generate code', 'code', 'create a script']
        for prefix in common_prefixes:
            if user_input_lower.startswith(prefix):
                return user_input[len(prefix):].strip()
        
        return user_input
    
    # Placeholder methods for other code operations
    async def _explain_code(self, user_id, user_input, context):
        """Explain code based on user input."""
        # TODO: Implement code explanation logic
        return {"status": "ok", "message": "Code explanation functionality not yet implemented."}
    
    async def _debug_code(self, user_id, user_input, context):
        """Debug code based on user input."""
        # TODO: Implement code debugging logic
        return {"status": "ok", "message": "Code debugging functionality not yet implemented."}
