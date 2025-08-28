from .base_agent import BaseAgent
import database_personal as database
import os
import json

class IntentClassifierAgent(BaseAgent):
    """Agent for intent classification without technical leaks."""
    
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model, agent_name="IntentClassifierAgent")
        self.comprehensive_prompts = {}

    def load_comprehensive_prompts(self):
        try:
            prompts_dict = {}
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
            v1_dir = os.path.join(project_root, "prompts", "v1")
            
            if os.path.exists(v1_dir):
                for file_name in os.listdir(v1_dir):
                    if file_name.endswith('.md'):
                        prompt_name = file_name.replace('.md', '')
                        file_path = os.path.join(v1_dir, file_name)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            prompts_dict[prompt_name] = f.read()

            self.comprehensive_prompts = {
                'core_system': self._build_classifier_system_prompt(prompts_dict)
            }
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}
    
    def _build_classifier_system_prompt(self, prompts_dict):
        core_identity = prompts_dict.get('00_core_identity', 'You are an intent classification assistant.')
        decision_tree = prompts_dict.get('09_intelligent_decision_tree', '')
        
        enhanced_prompt = f"""{core_identity}

{decision_tree}

You are the central classification system. Use the 9-branch decision tree to analyze user input.

CLASSIFICATION INSTRUCTIONS:
1. Apply the priority system (Memory > Silent Mode > Journal > AI Actions > Reminders > Tasks > Guide > Expert > Chat)
2. Use pattern matching for each branch
3. Calculate confidence scores
4. Generate smart assumptions based on detected patterns
5. Return structured JSON with primary_intent, confidence, and assumptions

CLASSIFICATION TO AGENT MAPPING:
- memory → context (memory operations handled by context_agent)
- silent → silent_mode (silent mode operations)
- journal → information (knowledge entries handled by information_agent)
- ai_action → task (recurring actions handled by task_agent)
- reminder → reminder (reminder operations)
- task → task (task management)
- guide → guide (help and assistance)
- expert → expert (advice and strategy)
- chat → general (general conversation)

Available agents in orchestrator: general, task, reminder, information, guide, expert, coder, audit, silent_mode, context, preference, action, help, silent

Return only classification data, no user-facing messages.

CRITICAL: Never include system details, debugging info, or technical formatting in any output.
"""
        
        return enhanced_prompt

    async def classify_intent(self, user_input, context):
        """Classify user intent - internal function, not user-facing."""
        try:
            if not self.comprehensive_prompts:
                self.load_comprehensive_prompts()
            
            system_prompt = self.comprehensive_prompts.get('core_system', 'You are an intent classification assistant.')
            
            user_prompt = f"""
Classify this user input using the 9-branch decision tree: {user_input}

Return JSON with:
{{
    "primary_intent": "agent_name",
    "confidence": 0.8,
    "assumptions": {{}}
}}

CLASSIFICATION TO AGENT MAPPING:
- memory → context
- silent → silent_mode
- journal → information
- ai_action → task
- reminder → reminder
- task → task
- guide → guide
- expert → expert
- chat → general

Available agents in orchestrator: general, task, reminder, information, guide, expert, coder, audit, silent_mode, context, preference, action, help, silent
"""
      
            # Make AI call (synchronous)
            response = self.ai_model.generate_content([system_prompt, user_prompt])
            response_text = response.text
            
            # Parse the classification (internal processing)
            try:
                # Extract JSON from response
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start >= 0 and end > start:
                    json_str = response_text[start:end]
                    classification = json.loads(json_str)
                else:
                    # Fallback classification
                    classification = {
                        "primary_intent": "general",
                        "confidence": 0.5,
                        "assumptions": {}
                    }
            except Exception as e:
                print(f"Classification parsing error: {e}")
                classification = {
                    "primary_intent": "general", 
                    "confidence": 0.5,
                    "assumptions": {}
                }
            
            # Log classification (internal only)
            user_id = context.get('user_id')
            if user_id:
                self._log_action(
                    user_id=user_id,
                    action_type="intent_classified",
                    entity_type="classification",
                    action_details=classification,
                    success_status=True
                )
            
            return classification
            
        except Exception as e:
            print(f"ERROR in IntentClassifierAgent: {e}")
            return {
                "primary_intent": "general",
                "confidence": 0.3,
                "assumptions": {}
            }

    async def process(self, user_input, context, routing_info=None):
        """This agent doesn't provide user-facing responses."""
        return {
            "message": "Classification complete."
        }
