import json
import logging
import time
from typing import Dict, Any, Optional, List, Union

logger = logging.getLogger(__name__)


class JournalAgent:
    """
    An intelligent, self-contained agent for managing a user's journal.
    This class includes its own prompt-building logic and is designed for efficiency
    with ID-aware modifications, contextual understanding, and robust fallbacks.
    """
    def __init__(self, ai_model=None, supabase=None, api_key_manager=None):
        self.ai_model = ai_model
        self.supabase = supabase
        self.api_key_manager = api_key_manager
        self.last_api_call = 0
        self.rate_limit_seconds = 2
        self.category_cache = {}
        self.default_categories = ['contact', 'location', 'note', 'idea', 'memory']
        self.user_context = None # To store context per command

    # --------------------------------------------------------------------------
    # Core Agent Logic
    # --------------------------------------------------------------------------

    def process_command(self, user_command: str, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main entry point. Processes commands with an efficient, batch-first approach.
        """
        if not self.ai_model or not self.supabase:
            return self._error_response("Journal Agent is not properly initialized.")

        try:
            user_id = user_context.get('user_info', {}).get('user_id')
            if not user_id: return self._error_response("User ID is required.")

            self.user_context = user_context or {}

            chunks = self._split_command_into_chunks(user_command)
            
            intents_by_type = {'upsert': [], 'search': [], 'update': [], 'delete': []}
            for chunk in chunks:
                intent_details = self._determine_intent(chunk)
                intent = intent_details.get('intent', 'upsert')
                intents_by_type.setdefault(intent, []).append(intent_details)

            all_actions = []
            all_responses = []
            final_context_update = {}

            if intents_by_type['upsert']:
                result = self._handle_batch_upsert(intents_by_type['upsert'], user_id)
                all_actions.extend(result.get('actions', []))
                if result.get('response'): all_responses.append(result['response'])

            for intent_details in intents_by_type['search']:
                result = self._handle_search_intent(intent_details, user_id)
                all_actions.extend(result.get('actions', []))
                if result.get('response'): all_responses.append(result['response'])
                if result.get('context_update'): final_context_update.update(result['context_update'])

            for intent_details in intents_by_type['update']:
                result = self._handle_update_intent(intent_details, user_id)
                all_actions.extend(result.get('actions', []))
                if result.get('response'): all_responses.append(result['response'])
                
            for intent_details in intents_by_type['delete']:
                result = self._handle_delete_intent(intent_details, user_id)
                all_actions.extend(result.get('actions', []))
                if result.get('response'): all_responses.append(result['response'])

            if not all_actions and not all_responses:
                return self._error_response("I couldn't understand what you wanted to do.")

            final_response = "\n".join(all_responses)
            if len(all_responses) > 1:
                 final_response = f"Okay, I've handled {len(all_responses)} items for you:\n- " + "\n- ".join(all_responses)

            return {'success': bool(all_actions), 'actions': all_actions, 'response': final_response, 'context_update': final_context_update}
            
        except Exception as e:
            logger.exception(f"Journal processing failed unexpectedly: {e}")
            return self._error_response("An error occurred while processing your journal request.")

    # --------------------------------------------------------------------------
    # Intent Handlers
    # --------------------------------------------------------------------------

    def _handle_batch_upsert(self, intent_details_list: List[Dict], user_id: str) -> Dict:
        contents_to_analyze = [details.get('content') for details in intent_details_list if details.get('content')]
        if not contents_to_analyze:
            return {'actions': [], 'response': None}

        analyzed_details = self._analyze_batch_journal_details(contents_to_analyze, user_id)
        if len(analyzed_details) != len(contents_to_analyze):
            return {'actions': [], 'response': "There was an issue analyzing the new entries."}

        actions = []
        titles = []
        for content, analysis in zip(contents_to_analyze, analyzed_details):
            action = {
                'type': 'create_journal_entry', 'title': analysis['title'], 'content': content,
                'category': analysis['category'], 'entry_type': 'free_form'
            }
            actions.append(action)
            titles.append(analysis['title'])
        
        response = f"Saved {len(titles)} new entries, including '{titles[0]}'." if titles else ""
        return {'success': True, 'actions': actions, 'response': response}

    def _handle_search_intent(self, intent_details: Dict, user_id: str) -> Dict:
        """Handles finding notes and preparing for follow-up actions by remembering their IDs."""
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

        context_update = {
            'last_retrieved_journal_entries': [
                {'id': entry['id'], 'title': entry['title']} for entry in full_entries
            ]
        }
        
        action = {'type': 'retrieved_journal_data', 'data': full_entries}
        
        response = f"I found {len(full_entries)} note(s) related to '{query}'."
        if len(full_entries) == 1:
            response = f"Found it! Looking up '{full_entries[0]['title']}'."

        return {'success': True, 'actions': [action], 'response': response, 'context_update': context_update}
        
    def _handle_update_intent(self, intent_details: Dict, user_id: str) -> Dict:
        """Handles updating a note, prioritizing ID-based context first."""
        title_match_query = intent_details.get('title_match')
        new_content = intent_details.get('new_content')
        if not title_match_query or not new_content:
            return self._error_response("To update, please tell me which note to change and the new content.")
        
        last_retrieved = self.user_context.get('last_retrieved_journal_entries', [])
        if last_retrieved:
            entry_id = self._resolve_id_from_context(title_match_query, last_retrieved)
            if entry_id:
                analysis = self._analyze_batch_journal_details([new_content], user_id)[0]
                action = {
                    'type': 'update_journal_entry', 'id': entry_id,
                    'patch': { 'content': new_content, 'title': analysis['title'], 'category': analysis['category'] }
                }
                original_title = next((e['title'] for e in last_retrieved if e['id'] == entry_id), "the note")
                return {'success': True, 'actions': [action], 'response': f"Okay, updating '{original_title}'."}

        # Fallback to title matching
        resolved_titles = self._resolve_title_match(title_match_query, user_id, self.user_context)
        if not resolved_titles:
            return self._error_response(f"I couldn't find any note matching '{title_match_query}' to update.")
        if isinstance(resolved_titles, list):
            titles_str = "', '".join(resolved_titles)
            response = f"I found a few notes that could match: '{titles_str}'. Please be more specific."
            return {'success': False, 'actions': [], 'response': response}

        resolved_title = resolved_titles
        analysis = self._analyze_batch_journal_details([new_content], user_id)[0]
        action = {
            'type': 'update_journal_entry', 'titleMatch': resolved_title,
            'patch': { 'content': new_content, 'title': analysis['title'], 'category': analysis['category'] }
        }
        return {'success': True, 'actions': [action], 'response': f"Okay, attempting to update '{resolved_title}'."}

    def _handle_delete_intent(self, intent_details: Dict, user_id: str) -> Dict:
        """Handles deleting a note, prioritizing ID-based context first."""
        title_match_query = intent_details.get('title_match')
        if not title_match_query: return self._error_response("Please specify the title of the note to delete.")
        
        last_retrieved = self.user_context.get('last_retrieved_journal_entries', [])
        if last_retrieved:
            entry_id = self._resolve_id_from_context(title_match_query, last_retrieved)
            if entry_id:
                original_title = next((e['title'] for e in last_retrieved if e['id'] == entry_id), "the note")
                action = {'type': 'delete_journal_entry', 'id': entry_id}
                return {'success': True, 'actions': [action], 'response': f"Okay, I'll delete the note titled '{original_title}'."}

        # Fallback to title matching
        resolved_titles = self._resolve_title_match(title_match_query, user_id, self.user_context)
        if not resolved_titles:
            return self._error_response(f"I couldn't find any note matching '{title_match_query}' to delete.")
        if isinstance(resolved_titles, list):
            titles_str = "', '".join(resolved_titles)
            response = f"I found a few notes that could match: '{titles_str}'. Please be more specific."
            return {'success': False, 'actions': [], 'response': response}

        resolved_title = resolved_titles
        action = {'type': 'delete_journal_entry', 'titleMatch': resolved_title}
        return {'success': True, 'actions': [action], 'response': f"Okay, I'll delete the note titled '{resolved_title}'."}

    # --------------------------------------------------------------------------
    # Smart Helper Methods
    # --------------------------------------------------------------------------

    def _resolve_title_match(self, query: str, user_id: str, context: Optional[Dict] = None) -> Optional[Union[str, List[str]]]:
        logger.info(f"Resolving title for query: '{query}'")
        all_entries = self._get_all_titles_and_categories(user_id)
        if not all_entries: return None
        
        matching_titles = self._find_matching_entries_for_search(query, all_entries)
        
        if len(matching_titles) == 1:
            logger.info(f"Found exactly one match via general search: '{matching_titles[0]}'")
            return matching_titles[0]
        
        if len(matching_titles) > 1 and context:
            logger.info("Ambiguity detected. Using conversation context to resolve.")
            conversation_history = context.get('history', '')
            if conversation_history:
                single_title = self._find_single_match_with_context(query, matching_titles, conversation_history)
                if single_title:
                    logger.info(f"Context resolved ambiguity to: '{single_title}'")
                    return single_title
        
        return matching_titles if matching_titles else None

    def _resolve_id_from_context(self, query: str, entries: List[Dict]) -> Optional[int]:
        """Uses an AI call to resolve a vague query to a specific ID from a list of entries."""
        if not entries: return None
        prompt = self._build_contextual_id_resolver_prompt(query, entries)
        response_text = self._make_ai_request_sync(prompt)
        try:
            result = json.loads(response_text.strip().replace('```json', '').replace('```', ''))
            entry_id = result.get('id')
            if entry_id and entry_id in [e['id'] for e in entries]:
                return entry_id
            return None
        except (json.JSONDecodeError, TypeError, ValueError):
            logger.warning(f"Could not parse contextual ID resolver response: {response_text}")
            return None

    def _split_command_into_chunks(self, user_command: str) -> List[str]:
        prompt = self._build_chunking_prompt(user_command)
        response_text = self._make_ai_request_sync(prompt)
        try:
            data = json.loads(response_text.strip().replace('```json', '').replace('```', ''))
            return data.get("chunks", [user_command])
        except (json.JSONDecodeError, TypeError):
            return [user_command]

    def _determine_intent(self, user_command: str) -> Dict[str, Any]:
        prompt = self._build_intent_determination_prompt(user_command)
        response_text = self._make_ai_request_sync(prompt)
        try:
            return json.loads(response_text.strip().replace('```json', '').replace('```', ''))
        except (json.JSONDecodeError, TypeError):
            return {'intent': 'upsert', 'content': user_command}

    def _analyze_batch_journal_details(self, contents: List[str], user_id: str) -> List[Dict[str, str]]:
        custom_categories = self._get_user_custom_categories(user_id)
        all_categories = list(set(self.default_categories + custom_categories))
        prompt = self._build_batch_journal_analysis_prompt(contents, all_categories)
        response_text = self._make_ai_request_sync(prompt)
        try:
            analysis_list = json.loads(response_text.strip().replace('```json', '').replace('```', ''))
            return analysis_list if isinstance(analysis_list, list) else []
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Could not parse batch journal analysis. Response: {response_text}")
            return [{'category': 'note', 'title': 'Journal Entry'}] * len(contents)

    def _find_matching_entries_for_search(self, query: str, entries: List[Dict[str, str]]) -> List[str]:
        prompt = self._build_journal_search_filter_prompt(query, entries)
        response_text = self._make_ai_request_sync(prompt)
        try:
            result = json.loads(response_text.strip().replace('```json', '').replace('```', ''))
            return result.get('titles', [])
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Could not parse search filter response: {response_text}")
            return []

    def _find_single_match_with_context(self, query: str, possible_titles: List[str], context: str) -> Optional[str]:
        possible_entries = [{'title': title} for title in possible_titles]
        prompt = self._build_contextual_search_filter_prompt(query, possible_entries, context)
        response_text = self._make_ai_request_sync(prompt)
        try:
            result = json.loads(response_text.strip().replace('```json', '').replace('```', ''))
            return result.get('title')
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Could not parse contextual search filter response: {response_text}")
            return None

    # --------------------------------------------------------------------------
    # Database and Utility Methods
    # --------------------------------------------------------------------------

    def _get_user_custom_categories(self, user_id: str) -> List[str]:
        cache_key = f"journal_categories_{user_id}"
        if cache_key in self.category_cache and time.time() - self.category_cache[cache_key][0] < 300:
            return self.category_cache[cache_key][1]
        try:
            if not self.supabase: return []
            result = self.supabase.table('journals').select('category').eq('user_id', user_id).execute()
            if result.data:
                custom_cats = list(set(d['category'] for d in result.data if d.get('category')))
                self.category_cache[cache_key] = (time.time(), custom_cats)
                return custom_cats
        except Exception as e:
            logger.error(f"Error fetching custom journal categories: {e}")
        return []

    def _get_all_titles_and_categories(self, user_id: str) -> List[Dict[str, str]]:
        try:
            if not self.supabase: return []
            result = self.supabase.table('journals').select('title, category').eq('user_id', user_id).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error fetching all journal titles and categories: {e}")
            return []

    def _get_journal_details_by_titles(self, user_id: str, titles: List[str]) -> List[Dict[str, str]]:
        """Fetches the full content AND ID for a given list of journal titles."""
        try:
            if not self.supabase: return []
            result = self.supabase.table('journals').select('id, title, content, category').eq('user_id', user_id).in_('title', titles).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error fetching journal details by titles: {e}")
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
        if time_since_call < self.rate_limit_seconds:
            time.sleep(self.rate_limit_seconds - time_since_call)
        self.last_api_call = time.time()

    def _error_response(self, message: str) -> Dict[str, Any]:
        return {'success': False, 'actions': [], 'response': f"❌ {message}", 'error': message}

    # --------------------------------------------------------------------------
    # Internal Prompt Building Methods
    # --------------------------------------------------------------------------

    @staticmethod
    def _build_chunking_prompt(user_command: str) -> str:
        """Splits a user's command into a list of distinct thoughts."""
        return f"""Analyze the user's command and split it into a list of separate, complete thoughts or actions.
Each item in the list should be a standalone command. Return a JSON object with a single key "chunks" which contains a list of strings.

User Command: "{user_command}"
---
EXAMPLES:
- Command: "rumah farah di jl rosyid 23 , rumah adit di jl pupsa no 2"
  Response: {{"chunks": ["rumah farah di jl rosyid 23", "rumah adit di jl pupsa no 2"]}}
- Command: "ingatkan saya beli susu besok dan dimana alamat dinda?"
  Response: {{"chunks": ["ingatkan saya beli susu besok", "dimana alamat dinda?"]}}
---
"""

    @staticmethod
    def _build_intent_determination_prompt(user_command: str) -> str:
        """
        Determines user intent for a single command chunk with high accuracy,
        using detailed examples to handle ambiguity.
        """
        return f"""You are an expert at analyzing journal commands. Your goal is to extract the user's precise intent and the specific information needed to fulfill it.

User Command: "{user_command}"

**CRITICAL GOAL:** For 'update' and 'delete' commands, you MUST extract the most specific possible description of the note the user wants to target into the "title_match" field. Include as much detail from the user's command as possible to help the system find the exact note.

**JSON Field Definitions:**
- "intent": One of ['upsert', 'search', 'update', 'delete'].
- "content": The main information to be saved (for 'upsert').
- "query": The search term or question (for 'search').
- "title_match": A specific description of the note to change or delete.
- "new_content": The new information for an update.

---
**EXAMPLES**
---

### --- UPSERT (Saving Information) ---
# Note: The user is stating a fact. This is the default intent.

- "Farah's address is at Jl. Mawar No. 123, Bandung"
  Response: {{"intent": "upsert", "content": "Farah's address is at Jl. Mawar No. 123, Bandung"}}

- "My flight number for the Paris trip is AF123"
  Response: {{"intent": "upsert", "content": "My flight number for the Paris trip is AF123"}}

### --- SEARCH (Asking a Question) ---
# Note: The user is asking for information.

- "what is farah's address?"
  Response: {{"intent": "search", "query": "farah's address"}}

- "find all my notes about Project Alpha"
  Response: {{"intent": "search", "query": "all notes about Project Alpha"}}

### --- DELETE (Removing a Note) ---
# Note: Extract the most specific reference to the note.

- "delete the note about farah's address"
  Response: {{"intent": "delete", "title_match": "the note about farah's address"}}

# A more specific delete command
- "remove my note about the flight to Paris"
  Response: {{"intent": "delete", "title_match": "my note about the flight to Paris"}}

### --- UPDATE (Changing a Note) ---
# Note: This is the most complex. Be very specific with "title_match".

# User wants to change a note about Farah's address to a new one.
- "change the note about Farah's address in Bandung to say she now lives in Jakarta"
  Response: {{"intent": "update", "title_match": "note about Farah's address in Bandung", "new_content": "Farah now lives in Jakarta"}}

# User has notes "Project Alpha Ideas" and "Project Alpha Budget". This is a specific update.
- "in my project alpha budget note, set the total to $50,000"
  Response: {{"intent": "update", "title_match": "project alpha budget note", "new_content": "The total is $50,000"}}

---
Now, analyze the user's command carefully based on these detailed examples. Your response MUST be ONLY the raw JSON object.
"""

    @staticmethod
    def _build_batch_journal_analysis_prompt(contents: List[str], all_categories: List[str]) -> str:
        """Builds a prompt to analyze a batch of new journal entries."""
        formatted_contents = "\n".join([f'- "{item}"' for item in contents])
        return f"""You are an expert at summarizing content into a title and category. Analyze the following list of journal entries and generate a corresponding JSON array of analysis objects.

**Entries to Analyze:**
{formatted_contents}

**Categorization Rules (CRITICAL):**
1.  **PRIORITY 1: Use Existing Categories.** You MUST try to match each entry to one of the user's existing categories: {json.dumps(all_categories)}.
2.  **PRIORITY 2: Create a New, Specific Category.** If an entry does not fit an existing category, create a NEW, descriptive, topic-focused category.
    - GOOD examples: "Project Ideas", "Contact Information", "Meeting Notes", "Paris Trip Planning".
    - BAD examples: "Note", "General", "Info". Avoid vague terms.
3.  **Title Generation**: The title should be a concise, descriptive summary of the specific content.

**Response Format:**
- Your response MUST be a single JSON array.
- The number of objects in your array MUST exactly match the number of entries provided.
- Each object MUST contain "category" and "title" keys.

---
EXAMPLE:
- Entries: ["address of Farah at JL Oak No. 321", "Adit's phone number is 555-1234"]
- Existing Categories: ["contact", "location"]
- Response: [
    {{"category": "location", "title": "Farah's Address"}},
    {{"category": "contact", "title": "Adit's Phone Number"}}
  ]
---

Now, analyze the list of entries and provide your response.
"""

    @staticmethod
    def _build_journal_search_filter_prompt(query: str, entries: List[Dict[str, str]]) -> str:
        """Builds a prompt to find ALL matching entries for a natural language query."""
        formatted_entries = "\n".join([f"- Title: \"{entry['title']}\", Category: \"{entry['category']}\"" for entry in entries])
        return f"""You are a smart journal search filter. Find all entries that are relevant to the user's query from the list below.

User Query: "{query}"

Available Journal Entries:
{formatted_entries}

Instructions:
1.  Analyze the query's intent (e.g., are they asking about a person, a topic, a project?).
2.  Select ALL entries that are a logical match. It is okay to return multiple entries.
3.  Your response MUST be a JSON object with a single key: "titles".
4.  The value of "titles" must be a list of the exact titles of all matching entries.
5.  If no entries match, return an empty list: {{"titles": []}}.

---
EXAMPLE:
- Query: "everything about Farah"
- Entries: Title: "Farah's Address", Title: "Farah's Favorite Color", Title: "Adit's Phone"
- Response: {{"titles": ["Farah's Address", "Farah's Favorite Color"]}}
---
"""

    @staticmethod
    def _build_contextual_search_filter_prompt(query: str, entries: List[Dict[str, str]], context: str) -> str:
        """Builds a prompt to find a SINGLE matching entry title using conversation context."""
        formatted_entries = "\n".join([f"- Title: \"{entry['title']}\"" for entry in entries])
        return f"""You are an expert at resolving ambiguity. The user wants to select one of the following journal entries. Use the conversation context to determine the single most likely entry they are referring to.

**Available Journal Entries:**
{formatted_entries}

**Conversation Context:**
{context}

**User's Vague Request:**
"{query}"

**Instructions:**
1.  Read the context and the user's request carefully.
2.  Identify the single entry that the user is most clearly referring to.
3.  Your response MUST be a JSON object with a single key: "title".
4.  The value of "title" must be the exact title of the single best match.
5.  If you cannot confidently determine a single match, return null: {{"title": null}}.

---
EXAMPLE:
- Context: "Agent: I found two notes: 'Farah's Address' (in Bandung) and 'Farah's Location' (moved to Jakarta)."
- User Request: "delete the one in bandung"
- Response: {{"title": "Farah's Address"}}
---
"""

    @staticmethod
    def _build_contextual_id_resolver_prompt(query: str, entries: List[Dict[str, any]]) -> str:
        """
        Builds a prompt to resolve a user's vague command to a specific item ID
        from a list of previously retrieved items.
        """
        formatted_entries = "\n".join([f"- ID: {entry['id']}, Title: \"{entry['title']}\"" for entry in entries])
        return f"""You are an expert at understanding user follow-up commands. The user was just shown a list of journal entries and now wants to act on one of them. Your job is to identify the SINGLE entry they are referring to and return its unique ID.

**Entries the user is looking at:**
{formatted_entries}

**User's Command:**
"{query}"

**Instructions:**
1.  Analyze the user's command. They might refer to an entry by its position ("the first one", "the second note"), by a keyword from its title ("the one about the budget"), or by another characteristic.
2.  Determine the single, most likely entry they mean.
3.  Your response MUST be a JSON object with a single key: "id".
4.  The value of "id" must be the integer ID of the best match.
5.  If you cannot confidently determine a single match, return null: {{"id": null}}.

---
EXAMPLE 1: Positional Reference
- Entries:
  - ID: 101, Title: "Project Alpha Ideas"
  - ID: 102, Title: "Project Alpha Budget"
- User Command: "delete the second one"
- Response: {{"id": 102}}

EXAMPLE 2: Keyword Reference
- Entries:
  - ID: 101, Title: "Project Alpha Ideas"
  - ID: 102, Title: "Project Alpha Budget"
- User Command: "update the budget note"
- Response: {{"id": 102}}
---

Now, analyze the request and provide the matching ID.
"""