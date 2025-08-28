import json
import logging
import time
from typing import Dict, Any, Optional, List, Union

# from .journal_prompt_factory import JournalPromptFactory

logger = logging.getLogger(__name__)


class JournalAgent:
    """
    An intelligent agent for managing a user's journal, rebuilt for efficiency
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


    def _handle_batch_upsert(self, intent_details_list: List[Dict], user_id: str) -> Dict:
        """Handles creating multiple journal entries in a single efficient pass."""
        contents_to_analyze = [details.get('content') for details in intent_details_list if details.get('content')]
        if not contents_to_analyze:
            return {'actions': [], 'response': None}

        analyzed_details = self._analyze_batch_journal_details(contents_to_analyze, user_id)
        if len(analyzed_details) != len(contents_to_analyze):
            return {'actions': [], 'response': "There was an issue analyzing the new entries."}

        actions = []
        titles = []
        for content, analysis in zip(contents_to_analyze, analyzed_details):
            # *** THIS IS THE FIX ***
            # The action type must match the tool name in your registry.
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
        prompt = JournalPromptFactory.build_contextual_id_resolver_prompt(query, entries)
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
        prompt = JournalPromptFactory.build_chunking_prompt(user_command)
        response_text = self._make_ai_request_sync(prompt)
        try:
            data = json.loads(response_text.strip().replace('```json', '').replace('```', ''))
            return data.get("chunks", [user_command])
        except (json.JSONDecodeError, TypeError):
            return [user_command]

    def _determine_intent(self, user_command: str) -> Dict[str, Any]:
        prompt = JournalPromptFactory.build_intent_determination_prompt(user_command)
        response_text = self._make_ai_request_sync(prompt)
        try:
            return json.loads(response_text.strip().replace('```json', '').replace('```', ''))
        except (json.JSONDecodeError, TypeError):
            return {'intent': 'upsert', 'content': user_command}

    def _analyze_batch_journal_details(self, contents: List[str], user_id: str) -> List[Dict[str, str]]:
        custom_categories = self._get_user_custom_categories(user_id)
        all_categories = list(set(self.default_categories + custom_categories))
        prompt = JournalPromptFactory.build_batch_journal_analysis_prompt(contents, all_categories)
        response_text = self._make_ai_request_sync(prompt)
        try:
            analysis_list = json.loads(response_text.strip().replace('```json', '').replace('```', ''))
            return analysis_list if isinstance(analysis_list, list) else []
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Could not parse batch journal analysis. Response: {response_text}")
            return [{'category': 'note', 'title': 'Journal Entry'}] * len(contents)

    def _find_matching_entries_for_search(self, query: str, entries: List[Dict[str, str]]) -> List[str]:
        prompt = JournalPromptFactory.build_journal_search_filter_prompt(query, entries)
        response_text = self._make_ai_request_sync(prompt)
        try:
            result = json.loads(response_text.strip().replace('```json', '').replace('```', ''))
            return result.get('titles', [])
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Could not parse search filter response: {response_text}")
            return []

    def _find_single_match_with_context(self, query: str, possible_titles: List[str], context: str) -> Optional[str]:
        possible_entries = [{'title': title} for title in possible_titles]
        prompt = JournalPromptFactory.build_contextual_search_filter_prompt(query, possible_entries, context)
        response_text = self._make_ai_request_sync(prompt)
        try:
            result = json.loads(response_text.strip().replace('```json', '').replace('```', ''))
            return result.get('title')
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Could not parse contextual search filter response: {response_text}")
            return None

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