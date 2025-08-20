from .base_agent import BaseAgent
import database_personal  # Fix #4: Proper database import
import os

class CoderAgent(BaseAgent):
    """Agent for handling code-related operations."""
    
    def __init__(self, supabase, ai_model):  # Fix #1: Correct constructor
        super().__init__(supabase, ai_model, "CoderAgent")
        self.comprehensive_prompts = {}
    
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
        
        # Load comprehensive prompts
        if not self.comprehensive_prompts:
            self.load_comprehensive_prompts()
        
        # NEW: Apply AI assumptions to enhance processing
        enhanced_context = self._apply_ai_assumptions(context, routing_info)
        
        # NEW: Use AI assumptions if available
        language = None
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
    
    
    def load_comprehensive_prompts(self):
        """Load ALL prompts from the prompts/v1/ directory and requirements."""
        try:
            prompts_dict = {}
            
            # Load all prompts from v1 directory
            v1_dir = "/workspace/user_input_files/todowa/prompts/v1"
            if os.path.exists(v1_dir):
                for file_name in os.listdir(v1_dir):
                    if file_name.endswith('.md'):
                        prompt_name = file_name.replace('.md', '')
                        file_path = os.path.join(v1_dir, file_name)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            prompts_dict[prompt_name] = f.read()
            
            # Load requirements
            requirements_path = "/workspace/user_input_files/99_requirements.md"
            if os.path.exists(requirements_path):
                with open(requirements_path, 'r', encoding='utf-8') as f:
                    prompts_dict['requirements'] = f.read()
            
            # Create comprehensive system prompt for coder agent
            self.comprehensive_prompts = {
                'core_system': self._build_coder_system_prompt(prompts_dict),
                'core_identity': prompts_dict.get('00_core_identity', ''),
                'ai_interactions': prompts_dict.get('04_ai_interactions', ''),
                'templates': prompts_dict.get('08_templates', ''),
                'requirements': prompts_dict.get('requirements', ''),
                'all_prompts': prompts_dict
            }
            
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}
    
    def _build_coder_system_prompt(self, prompts_dict):
        """Build comprehensive system prompt for coder agent."""
        core_identity = prompts_dict.get('00_core_identity', '')
        ai_interactions = prompts_dict.get('04_ai_interactions', '')
        templates = prompts_dict.get('08_templates', '')
        requirements = prompts_dict.get('requirements', '')
        
        return f"""{core_identity}

## CODER AGENT SPECIALIZATION
You are specifically focused on code-related operations:
- Generating clean, well-documented code in various languages
- Explaining code functionality and logic
- Debugging and troubleshooting code issues
- Providing code examples and best practices
- Following language-specific conventions and standards

{ai_interactions}

{templates}

## REQUIREMENTS COMPLIANCE
{requirements}

## CODER AGENT BEHAVIOR
- ALWAYS provide clean, readable code with comments
- Use proper language-specific conventions and best practices
- Include usage examples when generating code
- Apply comprehensive prompt guidance for enhanced code assistance
- Follow security and performance best practices"""
    
    def _apply_ai_assumptions(self, context, routing_info):
        """Apply AI assumptions to enhance the context"""
        enhanced_context = context.copy()
        if routing_info:
            enhanced_context.update(routing_info.get('assumptions', {}))
        return enhanced_context
    
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
        
        # Get system prompt from comprehensive prompts
        system_prompt = self.comprehensive_prompts.get('core_system', "You are a helpful coding agent.")
        
        user_prompt = f"""
Generate {language or 'generic'} code for: {description}

Requirements:
- Clean, readable code
- Include comments explaining the logic
- Follow best practices for {language or 'the language'}
- Provide usage examples if applicable
"""
        
        # Fix #2: Correct AI model call with array parameter
        response = await self.ai_model.generate_content([
            system_prompt, user_prompt
        ])
        response_text = response.text
        
        # Log the action
        database_personal.log_action(
            supabase=self.supabase,
            user_id=user_id,
            action_type="generate_code",
            entity_type="code",
            action_details={
                "language": language or "unknown",
                "description": description[:200]  # Truncate for storage
            },
            success_status=True
        )
        
        return {
            "status": "success",
            "message": f"Here's the {language or 'generic'} code for {description}:",
            "code": response_text,
            "language": language
        }
    
    async def _explain_code(self, user_id, user_input, context):
        """Explain code provided by the user."""
        # Extract code from user input
        code = self._extract_code_from_input(user_input)
        
        if not code:
            return {
                "status": "error",
                "message": "I couldn't find any code to explain in your message. Please provide the code you'd like me to explain."
            }
        
        # Get system prompt from comprehensive prompts
        system_prompt = self.comprehensive_prompts.get('core_system', "You are a helpful coding agent.")
        
        user_prompt = f"""
Explain this code in detail:

```
{code}
```

Please provide:
- What the code does
- How it works step by step
- Key concepts used
- Any potential improvements or issues
"""
        
        # Fix #2: Correct AI model call with array parameter
        response = await self.ai_model.generate_content([
            system_prompt, user_prompt
        ])
        response_text = response.text
        
        # Log the action
        database_personal.log_action(
            supabase=self.supabase,
            user_id=user_id,
            action_type="explain_code",
            entity_type="code",
            action_details={
                "code_length": len(code)
            },
            success_status=True
        )
        
        return {
            "status": "success",
            "message": "Here's my explanation of the code:",
            "explanation": response_text
        }
    
    async def _debug_code(self, user_id, user_input, context):
        """Help debug code provided by the user."""
        # Extract code and error information
        code = self._extract_code_from_input(user_input)
        error_info = self._extract_error_info(user_input)
        
        if not code:
            return {
                "status": "error",
                "message": "I couldn't find any code to debug. Please provide the code and describe the issue."
            }
        
        # Get system prompt from comprehensive prompts
        system_prompt = self.comprehensive_prompts.get('core_system', "You are a helpful coding agent.")
        
        user_prompt = f"""
Debug this code:

```
{code}
```

Error/Issue: {error_info or "General debugging assistance requested"}

Please provide:
- Identification of the problem
- Explanation of why it occurs
- Corrected code
- Prevention tips
"""
        
        # Fix #2: Correct AI model call with array parameter
        response = await self.ai_model.generate_content([
            system_prompt, user_prompt
        ])
        response_text = response.text
        
        # Log the action
        database_personal.log_action(
            supabase=self.supabase,
            user_id=user_id,
            action_type="debug_code",
            entity_type="code",
            action_details={
                "code_length": len(code),
                "error_provided": bool(error_info)
            },
            success_status=True
        )
        
        return {
            "status": "success",
            "message": "Here's my debugging analysis:",
            "debug_info": response_text
        }
    
    def _extract_code_description(self, user_input):
        """Extract the description of what code to generate."""
        # Simple extraction - remove common phrases
        description = user_input.lower()
        remove_phrases = ['write code', 'generate code', 'code for', 'create a script', 'to', 'that']
        
        for phrase in remove_phrases:
            description = description.replace(phrase, '')
        
        return description.strip()
    
    def _extract_code_from_input(self, user_input):
        """Extract code blocks from user input."""
        import re
        
        # Look for code in backticks
        code_match = re.search(r'```.*?\n(.*?)```', user_input, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
        
        # Look for inline code
        inline_match = re.search(r'`([^`]+)`', user_input)
        if inline_match:
            return inline_match.group(1).strip()
        
        # If no explicit code blocks, try to identify code-like content
        lines = user_input.split('\n')
        code_lines = []
        for line in lines:
            # Simple heuristic: lines with common programming symbols
            if any(symbol in line for symbol in ['()', '{}', '[]', ';', '=', '->', '=>']):
                code_lines.append(line)
        
        if code_lines:
            return '\n'.join(code_lines)
        
        return None
    
    def _extract_error_info(self, user_input):
        """Extract error information from user input."""
        error_keywords = ['error', 'exception', 'fails', 'broken', 'bug', 'issue', 'problem']
        
        for keyword in error_keywords:
            if keyword in user_input.lower():
                # Return the part of the input that likely contains error info
                lines = user_input.split('\n')
                error_lines = []
                for line in lines:
                    if any(kw in line.lower() for kw in error_keywords):
                        error_lines.append(line)
                
                if error_lines:
                    return ' '.join(error_lines)
        
        return None
