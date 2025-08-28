import json
import logging
import time
from typing import Dict, Any, Optional, List, Union

logger = logging.getLogger(__name__)


class JournalAgent:
    """
    An intelligent, self-contained agent for managing a user's journal.
    This version uses a single, powerful intent model and efficiently batches
    similar actions to minimize API calls. It is ID-aware and has robust fallbacks.
    """
    def __init__(self, ai_model=None, supabase=None, api_key_manager=None):
        self.ai_model = ai_model
        self.supabase = supabase
        self.api_key_manager = api_key_manager
        self.last_api_call = 0
        self.rate_limit_seconds = 2
        self.category_cache = {}
        self.default_categories = ['contact', 'location', 'note', 'idea', 'memory']
        self.user_context = None

    # --------------------------------------------------------------------------
    # Core Agent Logic
    # --------------------------------------------------------------------------

    def process_command(self, user_command: str, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main entry point. Processes commands using a single intent model and intelligent batching.
        """
        if not self.ai_model or not self.supabase:
            return self._error_response("Journal Agent is not properly initialized.")

        try:
            user_id = user_context.get('user_info', {}).get('user_id')
            if not user_id: return self._error_response("User ID is required.")

            self.user_context = user_context or {}

            # --- STEP 1: The "Planner" Call (Always 1 API Call) ---
            parsed_command = self._determine_all_intents(user_command)
            all_parsed_actions = parsed_command.get('actions', [])
            if not all_parsed_actions:
                all_parsed_actions = [{'intent': 'upsert', 'content': user_command}]

            all_actions = []
            all_responses = []
            final_context_update = {}

            # --- STEP 2: The "Worker" Phase with Intelligent Batching ---

            # Group all upserts to be processed in a single batch
            upsert_details = [action for action in all_parsed_actions if action.get('intent') == 'upsert']
            if upsert_details:
                result = self._handle_batch_upsert(upsert_details, user_id)
                all_actions.extend(result.get('actions', []))
                if result.get('response'): all_responses.append(result['response'])

            # Process all other intents one-by-one, as they are unique operations
            other_details = [action for action in all_parsed_actions if action.get('intent') != 'upsert']
            for action_details in other_details:
                intent = action_details.get('intent')
                result = {}
                if intent == 'search':
                    result = self._handle_search_intent(action_details, user_id)
                elif intent == 'update':
                    result = self._handle_update_intent(action_details, user_id)
                elif intent == 'delete':
                    result = self._handle_delete_intent(action_details, user_id)

                all_actions.extend(result.get('actions', []))
                if result.get('response'): all_responses.append(result['response'])
                if result.get('context_update'): final_context_update.update(result['context_update'])

            if not all_actions and not all_responses:
                return self._error_response("I couldn't understand what you wanted to do.")

            final_response = "\n".join(all_responses)
            if len(all_responses) > 1:
                 final_response = f"Okay, I've handled {len(all_responses)} items for you:\n- " + "\n- ".join(all_responses)

            return {'success': bool(all_actions), 'actions': all_actions, 'response': final_response, 'context_update': final_context_update}
            
        except Exception as e:
            logger.exception(f"Journal processing failed unexpectedly: {e}")
            return self._error_response("An error occurred while processing your journal request.")

    # ... (The rest of the code, including all handlers and prompt builders, remains exactly the same as the previous full version) ...
    
    # --------------------------------------------------------------------------
    # Intent Handlers (No changes needed in these handlers)
    # --------------------------------------------------------------------------

    def _handle_batch_upsert(self, intent_details_list: List[Dict], user_id: str) -> Dict:
        contents_to_analyze = [details.get('content') for details in intent_details_list if details.get('content')]
        if not contents_to_analyze:
            return {'actions': [], 'response': None}
        analyzed_details = self._analyze_batch_journal_details(contents_to_analyze, user_id)
        if len(analyzed_details) != len(contents_to_analyze):
            return {'actions': [], 'response': "There was an issue analyzing the new entries."}
        actions, titles = [], []
        for content, analysis in zip(contents_to_analyze, analyzed_details):
            action = {'type': 'create_journal_entry', 'title': analysis['title'], 'content': content, 'category': analysis['category'], 'entry_type': 'free_form'}
            actions.append(action)
            titles.append(analysis['title'])
        response = f"Saved {len(titles)} new entries, including '{titles[0]}'." if titles else ""
        return {'success': True, 'actions': actions, 'response': response}

    def _handle_search_intent(self, intent_details: Dict, user_id: str) -> Dict:
        query = intent_details.get('query')
        if not query: return self._error_response("Please specify what you want to search for.")
        all_entries_summary = self._get_all_titles_and_categories(user_id)
        if not all_entries_summary: return self._error_response("You don't have any journal entries to search yet.")
        matching_titles = self._find_matching_entries_for_search(query, all_entries_summary)
        if not matching_titles:
            return {'success': True, 'actions': [], 'response': f"I couldn't find any notes matching '{query}'."}
        full_entries = self._get_journal_details_by_titles(user_id, matching_titles)
        if not full_entries:
             return self._error_response(f"I found titles matching '{query}', but failed to retrieve their content.")
        context_update = {'last_retrieved_journal_entries': [{'id': entry['id'], 'title': entry['title']} for entry in full_entries]}
        action = {'type': 'retrieved_journal_data', 'data': full_entries}
        response = f"I found {len(full_entries)} note(s) related to '{query}'."
        if len(full_entries) == 1:
            response = f"Found it! Looking up '{full_entries[0]['title']}'."
        return {'success': True, 'actions': [action], 'response': response, 'context_update': context_update}
        
    def _handle_update_intent(self, intent_details: Dict, user_id: str) -> Dict:
        title_match_query = intent_details.get('title_match')
        new_content = intent_details.get('new_content')
        if not title_match_query or not new_content:
            return self._error_response("To update, please tell me which note to change and the new content.")
        last_retrieved = self.user_context.get('last_retrieved_journal_entries', [])
        if last_retrieved:
            entry_id = self._resolve_id_from_context(title_match_query, last_retrieved)
            if entry_id:
                analysis = self._analyze_batch_journal_details([new_content], user_id)[0]
                action = {'type': 'update_journal_entry', 'id': entry_id, 'patch': {'content': new_content, 'title': analysis['title'], 'category': analysis['category']}}
                original_title = next((e['title'] for e in last_retrieved if e['id'] == entry_id), "the note")
                return {'success': True, 'actions': [action], 'response': f"Okay, updating '{original_title}'."}
        resolved_titles = self._resolve_title_match(title_match_query, user_id, self.user_context)
        if not resolved_titles:
            return self._error_response(f"I couldn't find any note matching '{title_match_query}' to update.")
        if isinstance(resolved_titles, list):
            titles_str = "', '".join(resolved_titles)
            return {'success': False, 'actions': [], 'response': f"I found a few notes that could match: '{titles_str}'. Please be more specific."}
        resolved_title = resolved_titles
        analysis = self._analyze_batch_journal_details([new_content], user_id)[0]
        action = {'type': 'update_journal_entry', 'titleMatch': resolved_title, 'patch': {'content': new_content, 'title': analysis['title'], 'category': analysis['category']}}
        return {'success': True, 'actions': [action], 'response': f"Okay, attempting to update '{resolved_title}'."}

    def _handle_delete_intent(self, intent_details: Dict, user_id: str) -> Dict:
        title_match_query = intent_details.get('title_match')
        if not title_match_query: return self._error_response("Please specify the title of the note to delete.")
        last_retrieved = self.user_context.get('last_retrieved_journal_entries', [])
        if last_retrieved:
            entry_id = self._resolve_id_from_context(title_match_query, last_retrieved)
            if entry_id:
                original_title = next((e['title'] for e in last_retrieved if e['id'] == entry_id), "the note")
                action = {'type': 'delete_journal_entry', 'id': entry_id}
                return {'success': True, 'actions': [action], 'response': f"Okay, I'll delete the note titled '{original_title}'."}
        resolved_titles = self._resolve_title_match(title_match_query, user_id, self.user_context)
        if not resolved_titles:
            return self._error_response(f"I couldn't find any note matching '{title_match_query}' to delete.")
        if isinstance(resolved_titles, list):
            titles_str = "', '".join(resolved_titles)
            return {'success': False, 'actions': [], 'response': f"I found a few notes that could match: '{titles_str}'. Please be more specific."}
        resolved_title = resolved_titles
        action = {'type': 'delete_journal_entry', 'titleMatch': resolved_title}
        return {'success': True, 'actions': [action], 'response': f"Okay, I'll delete the note titled '{resolved_title}'."}

    # --------------------------------------------------------------------------
    # Smart Helper & AI Methods
    # --------------------------------------------------------------------------

    def _resolve_title_match(self, query: str, user_id: str, context: Optional[Dict] = None) -> Optional[Union[str, List[str]]]:
        all_entries = self._get_all_titles_and_categories(user_id)
        if not all_entries: return None
        matching_titles = self._find_matching_entries_for_search(query, all_entries)
        if len(matching_titles) == 1: return matching_titles[0]
        if len(matching_titles) > 1 and context:
            conversation_history = context.get('history', '')
            if conversation_history:
                single_title = self._find_single_match_with_context(query, matching_titles, conversation_history)
                if single_title: return single_title
        return matching_titles if matching_titles else None

    def _resolve_id_from_context(self, query: str, entries: List[Dict]) -> Optional[int]:
        if not entries: return None
        prompt = self._build_contextual_id_resolver_prompt(query, entries)
        response_text = self._make_ai_request_sync(prompt)
        try:
            result = json.loads(response_text.strip().replace('```json', '').replace('```', ''))
            entry_id = result.get('id')
            if entry_id and entry_id in [e['id'] for e in entries]: return entry_id
            return None
        except (json.JSONDecodeError, TypeError, ValueError): return None

    def _determine_all_intents(self, user_command: str) -> Dict[str, Any]:
        """New method to parse all actions from a command at once."""
        prompt = self._build_multi_intent_determination_prompt(user_command)
        response_text = self._make_ai_request_sync(prompt)
        try:
            return json.loads(response_text.strip().replace('```json', '').replace('```', ''))
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Could not parse multi-intent response. Defaulting to single upsert. Response: {response_text}")
            return {"actions": [{'intent': 'upsert', 'content': user_command}]}

    def _analyze_batch_journal_details(self, contents: List[str], user_id: str) -> List[Dict[str, str]]:
        custom_categories = self._get_user_custom_categories(user_id)
        all_categories = list(set(self.default_categories + custom_categories))
        prompt = self._build_batch_journal_analysis_prompt(contents, all_categories)
        response_text = self._make_ai_request_sync(prompt)
        try:
            analysis_list = json.loads(response_text.strip().replace('```json', '').replace('```', ''))
            return analysis_list if isinstance(analysis_list, list) else []
        except (json.JSONDecodeError, TypeError): return [{'category': 'note', 'title': 'Journal Entry'}] * len(contents)

    def _find_matching_entries_for_search(self, query: str, entries: List[Dict[str, str]]) -> List[str]:
        prompt = self._build_journal_search_filter_prompt(query, entries)
        response_text = self._make_ai_request_sync(prompt)
        try:
            result = json.loads(response_text.strip().replace('```json', '').replace('```', ''))
            return result.get('titles', [])
        except (json.JSONDecodeError, TypeError): return []

    def _find_single_match_with_context(self, query: str, possible_titles: List[str], context: str) -> Optional[str]:
        possible_entries = [{'title': title} for title in possible_titles]
        prompt = self._build_contextual_search_filter_prompt(query, possible_entries, context)
        response_text = self._make_ai_request_sync(prompt)
        try:
            result = json.loads(response_text.strip().replace('```json', '').replace('```', ''))
            return result.get('title')
        except (json.JSONDecodeError, TypeError): return None

    # --------------------------------------------------------------------------
    # Database and Utility Methods
    # --------------------------------------------------------------------------

    def _get_user_custom_categories(self, user_id: str) -> List[str]:
        cache_key = f"journal_categories_{user_id}"
        if cache_key in self.category_cache and time.time() - self.category_cache[cache_key][0] < 300: return self.category_cache[cache_key][1]
        try:
            if not self.supabase: return []
            result = self.supabase.table('journals').select('category').eq('user_id', user_id).execute()
            if result.data:
                custom_cats = list(set(d['category'] for d in result.data if d.get('category')))
                self.category_cache[cache_key] = (time.time(), custom_cats)
                return custom_cats
        except Exception as e: logger.error(f"Error fetching custom journal categories: {e}")
        return []

    def _get_all_titles_and_categories(self, user_id: str) -> List[Dict[str, str]]:
        try:
            if not self.supabase: return []
            result = self.supabase.table('journals').select('title, category').eq('user_id', user_id).execute()
            return result.data if result.data else []
        except Exception as e: logger.error(f"Error fetching all journal titles and categories: {e}")
        return []

    def _get_journal_details_by_titles(self, user_id: str, titles: List[str]) -> List[Dict[str, str]]:
        try:
            if not self.supabase: return []
            result = self.supabase.table('journals').select('id, title, content, category').eq('user_id', user_id).in_('title', titles).execute()
            return result.data if result.data else []
        except Exception as e: logger.error(f"Error fetching journal details by titles: {e}")
        return []

    def _make_ai_request_sync(self, prompt: str) -> Optional[str]:
        if not self.ai_model: return None
        try:
            self._enforce_rate_limit()
            response = self.ai_model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.exception(f"AI request failed in JournalAgent: {e}")
            return None

    def _enforce_rate_limit(self):
        time_since_call = time.time() - self.last_api_call
        if time_since_call < self.rate_limit_seconds: time.sleep(self.rate_limit_seconds - time_since_call)
        self.last_api_call = time.time()

    def _error_response(self, message: str) -> Dict[str, Any]:
        return {'success': False, 'actions': [], 'response': f"❌ {message}", 'error': message}

    # --------------------------------------------------------------------------
    # Internal Prompt Building Methods
    # --------------------------------------------------------------------------
    
    @staticmethod
    def _build_multi_intent_determination_prompt(user_command: str) -> str:
        """
        New, powerful prompt that parses a complex command into a list of distinct actions,
        making the separate chunking step obsolete.
        """
        return f"""You are an expert at analyzing complex user commands for a journal. Your task is to deconstruct the user's request into a list of specific, standalone actions.

User Command: "{user_command}"

**CRITICAL GOAL:** Your response MUST be a single JSON object with one key: "actions". The value of "actions" must be a list of action objects. Each action object must have an "intent" and other relevant fields.

**JSON Field Definitions for Each Action:**
- "intent": One of ['upsert', 'search', 'update', 'delete'].
- "content": The main information to be saved (for 'upsert').
- "query": The search term or question (for 'search').
- "title_match": A specific description of the note to change or delete.
- "new_content": The new information for an update.

---
**EXAMPLES**
---

# Command with multiple, different intents
- "update my note about the project with the new deadline and find Farah's phone number"
  Response: {{"actions": [
      {{"intent": "update", "title_match": "note about the project", "new_content": "the new deadline"}},
      {{"intent": "search", "query": "Farah's phone number"}}
  ]}}

# Command with multiple upserts (batch creation)
- "rumah farah di jl rosyid 23, rumah adit di jl pupsa no 2"
  Response: {{"actions": [
      {{"intent": "upsert", "content": "rumah farah di jl rosyid 23"}},
      {{"intent": "upsert", "content": "rumah adit di jl pupsa no 2"}}
  ]}}

# A simple, single-intent command
- "what is the address for the meeting?"
  Response: {{"actions": [
      {{"intent": "search", "query": "the address for the meeting"}}
  ]}}

# A complex, single-intent update
- "change the note about Farah's address in Bandung to say she now lives in Jakarta"
  Response: {{"actions": [
      {{"intent": "update", "title_match": "note about Farah's address in Bandung", "new_content": "Farah now lives in Jakarta"}}
  ]}}

# A command with three different intents
- "catat ide proyek baru, cari nomor telepon adit, lalu hapus catatan rapat kemarin"
  Response: {{"actions": [
      {{"intent": "upsert", "content": "ide proyek baru"}},
      {{"intent": "search", "query": "nomor telepon adit"}},
      {{"intent": "delete", "title_match": "catatan rapat kemarin"}}
  ]}}

---
Now, analyze the user's command carefully. If it only contains one action, the "actions" list should have only one item. Respond with ONLY a valid JSON object.
"""
    
    @staticmethod
    def _build_batch_journal_analysis_prompt(contents: List[str], all_categories: List[str]) -> str:
        formatted_contents = "\n".join([f'- "{item}"' for item in contents])
        return f"""You are an expert at summarizing content into a title and category. Analyze the following list of journal entries and generate a corresponding JSON array of analysis objects.
**Entries to Analyze:**\n{formatted_contents}
**Categorization Rules (CRITICAL):**
1. **PRIORITY 1: Use Existing Categories.** You MUST try to match each entry to one of the user's existing categories: {json.dumps(all_categories)}.
2. **PRIORITY 2: Create a New, Specific Category.** If an entry does not fit, create a NEW, descriptive, topic-focused category. (e.g., "Project Ideas", "Contact Information"). Avoid vague terms.
3. **Title Generation**: The title should be a concise, descriptive summary.
**Response Format:** Must be a single JSON array with the same number of objects as entries provided, each with "category" and "title" keys.
---
EXAMPLE:
- Entries: ["address of Farah at JL Oak No. 321", "Adit's phone number is 555-1234"]
- Existing Categories: ["contact", "location"]
- Response: [{{"category": "location", "title": "Farah's Address"}}, {{"category": "contact", "title": "Adit's Phone Number"}}]
---
Now, analyze the list of entries and provide your response.
"""

    @staticmethod
    def _build_journal_search_filter_prompt(query: str, entries: List[Dict[str, str]]) -> str:
        formatted_entries = "\n".join([f"- Title: \"{entry['title']}\", Category: \"{entry['category']}\"" for entry in entries])
        return f"""You are a smart journal search filter. Find all entries relevant to the user's query from the list below.
User Query: "{query}"
Available Journal Entries:\n{formatted_entries}
Instructions:
1. Analyze the query's intent (person, topic, project?).
2. Select ALL logical matches.
3. Your response MUST be a JSON object with a single key: "titles", which is a list of exact titles.
4. If no entries match, return an empty list: {{"titles": []}}.
---
EXAMPLE:
- Query: "everything about Farah"
- Entries: Title: "Farah's Address", Title: "Farah's Favorite Color", Title: "Adit's Phone"
- Response: {{"titles": ["Farah's Address", "Farah's Favorite Color"]}}
---
"""

    @staticmethod
    def _build_contextual_search_filter_prompt(query: str, entries: List[Dict[str, str]], context: str) -> str:
        formatted_entries = "\n".join([f"- Title: \"{entry['title']}\"" for entry in entries])
        return f"""You are an expert at resolving ambiguity. The user wants to select one entry. Use the conversation context to determine the single most likely entry they are referring to.
**Available Journal Entries:**\n{formatted_entries}
**Conversation Context:**\n{context}
**User's Vague Request:** "{query}"
**Instructions:**
1. Read the context and the user's request carefully.
2. Identify the single entry the user is most clearly referring to.
3. Your response MUST be a JSON object with a single key: "title", the exact title of the single best match.
4. If you cannot confidently determine a single match, return null: {{"title": null}}.
---
EXAMPLE:
- Context: "Agent: I found two notes: 'Farah's Address' (in Bandung) and 'Farah's Location' (moved to Jakarta)."
- User Request: "delete the one in bandung"
- Response: {{"title": "Farah's Address"}}
---
"""

    @staticmethod
    def _build_contextual_id_resolver_prompt(query: str, entries: List[Dict[str, any]]) -> str:
        formatted_entries = "\n".join([f"- ID: {entry['id']}, Title: \"{entry['title']}\"" for entry in entries])
        return f"""You are an expert at understanding user follow-up commands. The user was just shown a list of journal entries and now wants to act on one of them. Your job is to identify the SINGLE entry they are referring to and return its unique ID.
**Entries the user is looking at:**\n{formatted_entries}
**User's Command:** "{query}"
**Instructions:**
1. Analyze the command for position ("the first one"), keywords ("the budget note"), etc.
2. Determine the single, most likely entry.
3. Your response MUST be a JSON object with a single key: "id", the integer ID of the best match.
4. If you cannot confidently determine a single match, return null: {{"id": null}}.
---
EXAMPLE 1: Positional Reference
- Entries:\n  - ID: 101, Title: "Project Alpha Ideas"\n  - ID: 102, Title: "Project Alpha Budget"
- User Command: "delete the second one"
- Response: {{"id": 102}}
---
Now, analyze the request and provide the matching ID.
"""