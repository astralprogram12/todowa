import logging
import json
from typing import Dict, Any, Optional, List
from database import DatabaseManager

logger = logging.getLogger(__name__)

# --- GUARDRAIL CONSTANTS ---
# The maximum number of items to fetch for category-based search.
CATEGORY_SEARCH_LIMIT = 25 
# The maximum number of recent items to fetch for the fallback "brute-force" search.
RECENCY_SEARCH_LIMIT = 20

class FindingAgent:
    """
    An expert, multi-stage information retrieval agent. It uses a safe, dual-search
    strategy: first, a targeted category-based search, and second, a recency-based
    search. It always falls back to a web search if its internal search is
    unsuccessful.
    """
    def __init__(self, ai_model=None, supabase=None):
        self.ai_model = ai_model
        self.supabase = supabase

    # --- AI Planning & Matching Methods (Unchanged) ---
    def _create_search_plan(self, user_command: str, all_categories: Dict) -> Dict[str, Any]:
        """First AI Call: Creates a search term and selects relevant categories."""
        prompt = f"""
        You are an expert Search Strategist. Your job is to analyze a user's question and create an efficient search plan.

        **User's Question:** "{user_command}"
        **Available Data Categories:** {json.dumps(all_categories, indent=2)}

        **Your Task:**
        1.  Create a concise `search_term`.
        2.  Select the most promising categories from the available list.
        3.  If no categories seem relevant, return an empty list.

        **Respond ONLY with a valid JSON object:**
        {{
          "thought": "Your reasoning for the plan.",
          "search_term": "The concise search term.",
          "relevant_categories": ["category1", "category2", ...]
        }}
        """
        try:
            response = self.ai_model.generate_content(prompt)
            return json.loads(response.text.strip().replace('```json', '').replace('```', ''))
        except (json.JSONDecodeError, ValueError):
            return {"search_term": user_command, "relevant_categories": []}

    def _find_semantic_matches(self, search_term: str, candidates: List[Dict]) -> List[Dict]:
        """Second AI Call: Finds the best semantic matches from a candidate list."""
        prompt = f"""
        You are an expert Semantic Matcher. From the pre-filtered list of items below, find all items that are highly relevant to the user's search term.

        **User's Search Term:** "{search_term}"
        **Pre-filtered Candidate Items:** {json.dumps(candidates, indent=2)}

        **Instructions:**
        Return a JSON object with a single key, "matched_items", which is a list of objects. Each object must contain the "id" and "type" of a matched item.
        """
        try:
            response = self.ai_model.generate_content(prompt)
            return json.loads(response.text.strip().replace('```json', '').replace('```', '')).get("matched_items", [])
        except (json.JSONDecodeError, ValueError):
            return []

    # --- Database Helper Methods (Updated for Safety) ---
    def _get_all_category_metadata(self, db_manager: DatabaseManager) -> Dict:
        """Fetches all unique category names."""
        # This method is already efficient and safe. No changes needed.
        categories = {"tasks": [], "journals": []}
        try:
            tasks_res = db_manager.supabase.table('tasks').select('category').eq('user_id', db_manager.user_id).execute()
            if tasks_res.data: categories["tasks"] = list(set(t['category'] for t in tasks_res.data if t.get('category')))
            journals_res = db_manager.supabase.table('journals').select('category').eq('user_id', db_manager.user_id).execute()
            if journals_res.data: categories["journals"] = list(set(j['category'] for j in journals_res.data if j.get('category')))
        except Exception as e: logger.error(f"Failed to fetch category metadata: {e}")
        return categories

    def _fetch_candidates(self, db_manager: DatabaseManager, categories: Optional[List[str]] = None) -> List[Dict]:
        """
        Fetches a LIMITED list of candidates.
        - If categories are provided, it fetches the latest items from those categories.
        - If no categories are provided, it fetches the latest items overall.
        """
        candidates = []
        try:
            if categories:
                # Path A: Category-based search with a limit
                limit = CATEGORY_SEARCH_LIMIT
                task_query = db_manager.supabase.table('tasks').select('id, title, category').in_('category', categories).eq('user_id', db_manager.user_id).order('created_at', desc=True).limit(limit)
                journal_query = db_manager.supabase.table('journals').select('id, title, category').in_('category', categories).eq('user_id', db_manager.user_id).order('created_at', desc=True).limit(limit)
            else:
                # Path B: Recency-based search with a limit
                limit = RECENCY_SEARCH_LIMIT
                task_query = db_manager.supabase.table('tasks').select('id, title, category').eq('user_id', db_manager.user_id).order('created_at', desc=True).limit(limit)
                journal_query = db_manager.supabase.table('journals').select('id, title, category').eq('user_id', db_manager.user_id).order('created_at', desc=True).limit(limit)

            tasks_res = task_query.execute()
            if tasks_res.data:
                for item in tasks_res.data: item['type'] = 'Task'; candidates.append(item)
            journals_res = journal_query.execute()
            if journals_res.data:
                for item in journals_res.data: item['type'] = 'Journal'; candidates.append(item)
        except Exception as e:
            logger.error(f"Failed to fetch candidates: {e}")
        return candidates

    def _fetch_full_details(self, matched_items: List[Dict], db_manager: DatabaseManager) -> List[Dict]:
        """Fetches the full data for the final list of matched item IDs."""
        # This method is already safe as it only fetches by specific IDs. No changes needed.
        full_details, task_ids, journal_ids = [], [m['id'] for m in matched_items if m['type'] == 'Task'], [m['id'] for m in matched_items if m['type'] == 'Journal']
        try:
            if task_ids:
                res = db_manager.supabase.table('tasks').select('*').in_('id', task_ids).execute()
                if res.data:
                    for item in res.data: item['source'] = 'Tasks Database'; full_details.append(item)
            if journal_ids:
                res = db_manager.supabase.table('journals').select('*').in_('id', journal_ids).execute()
                if res.data:
                    for item in res.data: item['source'] = 'Journal Database'; full_details.append(item)
        except Exception as e: logger.error(f"Failed to fetch full details: {e}")
        return full_details

    # --- Main Orchestrator ---
    def process_command(self, user_command: str, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        user_id = user_context.get('user_info', {}).get('user_id')
        if not user_id: return {'success': False, 'actions': [], 'response': "I can't perform a search without a user ID."}

        db_manager = DatabaseManager(self.supabase, user_id)
        all_categories = self._get_all_category_metadata(db_manager)
        plan = self._create_search_plan(user_command, all_categories)
        search_term = plan.get("search_term")
        relevant_categories = plan.get("relevant_categories")

        if not search_term:
            return {'success': True, 'actions': [], 'response': "I'm not quite sure what you're asking me to find. Could you be more specific?"}

        # --- DUAL-SEARCH LOGIC ---
        database_results = []
        
        # Path A: Try the smart, category-based search first
        if relevant_categories:
            logger.info(f"Executing Path A: Category search in {relevant_categories}")
            candidates = self._fetch_candidates(db_manager, categories=relevant_categories)
            if candidates:
                matched_items = self._find_semantic_matches(search_term, candidates)
                if matched_items:
                    database_results = self._fetch_full_details(matched_items, db_manager)

        # Path B: If Path A failed, try the recency-based search
        if not database_results:
            logger.info("Path A failed or was skipped. Executing Path B: Recency search.")
            candidates = self._fetch_candidates(db_manager) # No categories = recency search
            if candidates:
                matched_items = self._find_semantic_matches(search_term, candidates)
                if matched_items:
                    database_results = self._fetch_full_details(matched_items, db_manager)

        # --- FINAL DECISION ---
        if database_results:
            # Success! One of our internal searches found something.
            response_message = f"I searched your personal database and found {len(database_results)} item(s) related to '{search_term}'."
            return {'success': True, 'actions': [], 'response': response_message, 'execution_result': {'found_data': database_results}}
        else:
            # Failure. Both internal searches failed. Fallback to the web.
            logger.info("Both Path A and Path B failed. Falling back to web search.")
            response_message = f"I couldn't find anything about '{search_term}' in your personal notes, so I'm searching the web for you."
            return {'success': True, 'actions': [{'type': 'internet_search', 'query': search_term}], 'response': response_message}