from .base_agent import BaseAgent
import database_personal as database
import os
import json

class IntentClassifierAgent(BaseAgent):
    """Enhanced agent for intent classification with query vs action distinction."""
    
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model, agent_name="IntentClassifierAgent")
        self.comprehensive_prompts = {}

    async def _detect_operation_type(self, user_input):
        """AI-powered operation type detection without regex patterns"""
        try:
            system_prompt = """You are an expert in understanding user intent and operation types. 

Analyze the user input and determine if it represents:
- "query": User wants to read/retrieve/view information (questions, requests for data)
- "create": User wants to add/create new items (tasks, reminders, etc.)
- "update": User wants to modify/change existing items (mark complete, edit, etc.)
- "delete": User wants to remove/delete items
- "general": General conversation or unclear intent

Consider context clues, verbs, and overall meaning regardless of language.

Return only one word: "query", "create", "update", "delete", or "general"."""

            user_prompt = f"Classify this user input: {user_input}"
            
            response = self.ai_model.generate_content([system_prompt, user_prompt])
            operation_type = response.text.strip().lower()
            
            # Validate the response
            valid_operations = ["query", "create", "update", "delete", "general"]
            if operation_type in valid_operations:
                return operation_type
            else:
                # Default fallback based on AI understanding
                return "create"
                
        except Exception as e:
            print(f"Error in AI operation detection: {e}")
            return "create"

    def load_comprehensive_prompts(self):
        try:
            self.comprehensive_prompts = {
                'core_system': self._build_enhanced_classifier_system_prompt({})
            }
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}
    
    def _build_enhanced_classifier_system_prompt(self, prompts_dict):
        enhanced_prompt = """You are an advanced AI-powered intent classification system that understands user intent across multiple languages and contexts.

CORE CAPABILITIES:
- Multi-language understanding (English, Spanish, French, German, Chinese, Japanese, etc.)
- Context-aware intent detection without rigid patterns
- Natural language understanding for implicit and explicit requests
- Cultural and linguistic nuance recognition

CLASSIFICATION FRAMEWORK:

1. QUERY OPERATIONS (Information Retrieval):
   - Any request to view, see, check, list, show, or get information
   - Questions about existing data
   - Status inquiries
   - Reporting requests
   Examples: "¿Cuáles son mis tareas?", "Show my tasks", "タスクを見せて", "Mes tâches?"

2. ACTION OPERATIONS (Data Manipulation):
   a) CREATE: Adding new items, reminders, tasks
      Examples: "Créer une tâche", "Add task", "新しいタスク", "Recordarme que..."
   
   b) UPDATE: Modifying existing items, marking complete, editing
      Examples: "Mark as done", "Terminer la tâche", "完了にする", "Actualizar tarea"
   
   c) DELETE: Removing, canceling, deleting items
      Examples: "Delete task", "Supprimer", "削除", "Eliminar tarea"

3. GENERAL: Casual conversation, greetings, unclear intent

DOMAIN DETECTION:
- task: Task management related
- reminder: Reminder/notification related  
- chat: General conversation
- preference: User settings/preferences
- help: Assistance requests

RESPONSE FORMAT:
Always return valid JSON with:
{
    "primary_intent": "query_[domain]" or "action_[domain]" or "general",
    "operation": "read" | "create" | "update" | "delete" | "none",
    "confidence": 0.0-1.0,
    "detected_language": "language_code",
    "domain_entities": ["extracted", "keywords"],
    "assumptions": {}
}

CRITICAL: Understand intent based on meaning, not keywords. Be language-agnostic and context-aware."""
        
        return enhanced_prompt

    async def classify_intent(self, user_input, context):
        """Fully AI-powered intent classification with multi-language support."""
        try:
            if not self.comprehensive_prompts:
                self.load_comprehensive_prompts()
            
            system_prompt = self.comprehensive_prompts.get('core_system', 'You are an intent classification assistant.')
            
            # Get AI-powered operation type detection
            operation_type = await self._detect_operation_type(user_input)
            
            # Build enhanced user prompt with context
            context_info = ""
            if context:
                user_id = context.get('user_id', 'unknown')
                session_context = context.get('session_context', {})
                if session_context:
                    context_info = f"\nContext: Recent conversation - {session_context.get('recent_topics', 'None')}"
            
            user_prompt = f"""Classify this user input with full AI understanding: "{user_input}"

AI Operation Hint: Detected as {operation_type} operation{context_info}

Analyze the complete semantic meaning and return JSON:
{{
    "primary_intent": "query_domain" or "action_domain" or "general",
    "operation": "read" | "create" | "update" | "delete" | "none",
    "confidence": 0.0-1.0,
    "detected_language": "language_code",
    "domain_entities": ["key", "terms", "extracted"],
    "assumptions": {{
        "inferred_domain": "explanation",
        "operation_reasoning": "why this operation"
    }}
}}

Examples across languages:
- "What are my tasks?" → {{"primary_intent": "query_task", "operation": "read", "detected_language": "en"}}
- "Créer une nouvelle tâche" → {{"primary_intent": "action_task", "operation": "create", "detected_language": "fr"}}
- "タスクを完了にマーク" → {{"primary_intent": "action_task", "operation": "update", "detected_language": "ja"}}
- "Mostrar mis recordatorios" → {{"primary_intent": "query_reminder", "operation": "read", "detected_language": "es"}}
- "Eliminar esta tarea" → {{"primary_intent": "action_task", "operation": "delete", "detected_language": "es"}}"""
      
            # Make AI call for comprehensive classification
            response = self.ai_model.generate_content([system_prompt, user_prompt])
            response_text = response.text.strip()
            
            # Parse the AI classification
            try:
                # Extract JSON from response
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start >= 0 and end > start:
                    json_str = response_text[start:end]
                    classification = json.loads(json_str)
                    
                    # Validate and enhance classification
                    if 'operation' not in classification:
                        classification['operation'] = 'read' if operation_type == 'query' else operation_type
                    
                    if 'confidence' not in classification:
                        classification['confidence'] = 0.8
                    
                    if 'detected_language' not in classification:
                        classification['detected_language'] = 'en'
                    
                    if 'domain_entities' not in classification:
                        classification['domain_entities'] = []
                    
                    if 'assumptions' not in classification:
                        classification['assumptions'] = {}
                        
                else:
                    # Pure AI fallback without patterns
                    classification = await self._ai_fallback_classification(user_input, operation_type)
                            
            except Exception as e:
                print(f"Classification parsing error: {e}")
                # Pure AI fallback without pattern matching
                classification = await self._ai_fallback_classification(user_input, operation_type)
            
            # Log classification (internal only)
            user_id = context.get('user_id') if context else None
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
            return await self._ai_fallback_classification(user_input, "general")

    async def _ai_fallback_classification(self, user_input, operation_type):
        """Pure AI fallback classification without pattern matching"""
        try:
            fallback_prompt = f"""Quick classification for: "{user_input}"
            
Detected operation: {operation_type}

Return simple JSON:
{{
    "primary_intent": "general" or "query_task" or "action_task" or "query_reminder" or "action_reminder",
    "operation": "{operation_type}",
    "confidence": 0.6,
    "detected_language": "en",
    "domain_entities": [],
    "assumptions": {{"fallback_used": true}}
}}"""

            response = self.ai_model.generate_content([fallback_prompt])
            response_text = response.text.strip()
            
            # Try to parse fallback response
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response_text[start:end]
                return json.loads(json_str)
            
        except Exception as e:
            print(f"Fallback classification error: {e}")
        
        # Ultimate fallback - pure structure without patterns
        return {
            "primary_intent": "general",
            "operation": operation_type if operation_type in ["read", "create", "update", "delete"] else "none",
            "confidence": 0.3,
            "detected_language": "en",
            "domain_entities": [],
            "assumptions": {"emergency_fallback": True}
        }

    async def process(self, user_input, context, routing_info=None):
        """This agent doesn't provide user-facing responses."""
        return {
            "message": "Classification complete."
        }
