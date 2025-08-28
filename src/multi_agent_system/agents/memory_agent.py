"""
Memory Management Agent

Intelligent storage and retrieval of memories and journal entries with:
- Relationship mapping between memories and people/events
- Timeline organization with smart clustering
- Importance scoring based on user patterns and interactions
- Search and retrieval by semantic similarity
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

# Add parent directories to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, parent_dir)

try:
    import google.generativeai as genai
    import config
    from base_agent import BaseAgent
except ImportError as e:
    logging.error(f"Failed to import required modules: {e}")
    raise

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MemoryAgent(BaseAgent):
    """Intelligent memory management and retrieval agent."""
    
    def __init__(self, supabase, ai_model, agent_name="MemoryAgent"):
        """Initialize the memory management agent."""
        super().__init__(supabase, ai_model, agent_name)
        self.memory_types = {
            'milestone': 0.9,      # Major life events
            'achievement': 0.85,   # Personal accomplishments
            'relationship': 0.8,   # Important social connections
            'experience': 0.7,     # Memorable experiences
            'learning': 0.6,       # Insights and lessons
            'general': 0.5         # General memories
        }
    
    async def process(self, user_input: str, context: Dict[str, Any], routing_info: Dict[str, Any] = None) -> str:
        """Process memory-related requests."""
        try:
            # Determine the memory operation
            operation = self._determine_operation(user_input, context)
            
            user_id = context.get('user_id')
            if not user_id:
                return "I need to identify you before I can help with your memories."
            
            if operation == 'store':
                return await self._store_memory(user_input, context)
            elif operation == 'retrieve':
                return await self._retrieve_memories(user_input, context)
            elif operation == 'search':
                return await self._search_memories(user_input, context)
            elif operation == 'timeline':
                return await self._generate_timeline(user_input, context)
            elif operation == 'relationships':
                return await self._analyze_relationships(user_input, context)
            else:
                return await self._help_with_memories()
                
        except Exception as e:
            logger.error(f"Error in memory processing: {e}")
            return "I'm having trouble with memory operations right now. Please try again later."
    
    async def _determine_operation(self, user_input: str, context: Dict[str, Any]) -> str:
        """AI-powered determination of memory operation intent."""
        try:
            system_prompt = """You are an expert at understanding user intent for memory operations.
            
            Analyze the user input and determine the operation type:
            - "store": User wants to save/remember something for the future
            - "search": User is looking for specific memories or information
            - "retrieve": User wants to recall general memories or experiences
            - "timeline": User wants chronological view of events or experiences
            - "relationships": User wants to explore connections between people/events
            
            Consider context, intent, and meaning regardless of specific words used.
            Return only one word: store, search, retrieve, timeline, or relationships"""
            
            user_prompt = f"Determine the memory operation for: {user_input}"
            
            response = self.ai_model.generate_content([system_prompt, user_prompt])
            operation = response.text.strip().lower()
            
            # Validate response
            valid_operations = ['store', 'search', 'retrieve', 'timeline', 'relationships']
            return operation if operation in valid_operations else 'store'
            
        except Exception as e:
            logger.error(f"Error in AI operation determination: {e}")
            return 'store'  # Safe default
    
    async def _store_memory(self, user_input: str, context: Dict[str, Any]) -> str:
        """Store a new memory with intelligent categorization and relationship mapping."""
        try:
            user_id = context['user_id']
            
            # Analyze the memory content
            analysis = await self._analyze_memory_content(user_input, context)
            
            # Store in database
            memory_data = {
                'user_id': user_id,
                'title': analysis['title'],
                'content': user_input,
                'memory_type': analysis['memory_type'],
                'importance_score': analysis['importance_score'],
                'emotional_tone': analysis['emotional_tone'],
                'tags': json.dumps(analysis['tags']),
                'relationships': json.dumps(analysis['relationships']),
                'locations': json.dumps(analysis['locations']),
                'time_context': analysis['time_context'],
                'created_at': datetime.now().isoformat()
            }
            
            result = self.supabase.table('memories').insert(memory_data).execute()
            
            if result.data:
                memory_id = result.data[0]['id']
                
                # Update relationship mappings
                await self._update_relationship_mappings(user_id, memory_id, analysis['relationships'])
                
                # Log the action
                self._log_action(user_id, 'create', 'memory', memory_id, 
                               {'title': analysis['title'], 'type': analysis['memory_type']})
                
                return f"I've saved your memory: '{analysis['title']}'. " + \
                       f"I've categorized it as a {analysis['memory_type']} memory " + \
                       f"with {len(analysis['relationships'])} relationship connections."
            else:
                raise Exception("Failed to store memory")
                
        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            return "I couldn't save that memory right now. Please try again."
    
    async def _retrieve_memories(self, user_input: str, context: Dict[str, Any]) -> str:
        """Retrieve memories based on user request."""
        try:
            user_id = context['user_id']
            
            # Get recent memories
            result = self.supabase.table('memories')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('importance_score', desc=True)\
                .order('created_at', desc=True)\
                .limit(10)\
                .execute()
            
            if not result.data:
                return "I don't have any memories stored yet. Share something important with me!"
            
            memories = result.data
            
            # Format the response
            response = "Here are your recent important memories:\n\n"
            
            for i, memory in enumerate(memories[:5], 1):
                created_date = datetime.fromisoformat(memory['created_at']).strftime("%B %d, %Y")
                memory_type = memory['memory_type'].replace('_', ' ').title()
                
                response += f"{i}. **{memory['title']}** ({memory_type})\n"
                response += f"   {memory['content'][:100]}{'...' if len(memory['content']) > 100 else ''}\n"
                response += f"   *Saved on {created_date}*\n\n"
            
            if len(memories) > 5:
                response += f"And {len(memories) - 5} more memories..."
            
            return response
            
        except Exception as e:
            logger.error(f"Error retrieving memories: {e}")
            return "I couldn't retrieve your memories right now. Please try again."
    
    async def _search_memories(self, user_input: str, context: Dict[str, Any]) -> str:
        """Search memories using semantic similarity."""
        try:
            user_id = context['user_id']
            
            # Extract search terms
            search_query = await self._extract_search_terms(user_input)
            
            # Search in database (simplified - would use vector search in production)
            result = self.supabase.table('memories')\
                .select('*')\
                .eq('user_id', user_id)\
                .execute()
            
            if not result.data:
                return "I don't have any memories to search through yet."
            
            # Score memories based on relevance
            scored_memories = []
            for memory in result.data:
                relevance_score = await self._calculate_relevance(memory, search_query)
                if relevance_score > 0.3:  # Threshold for relevance
                    scored_memories.append((memory, relevance_score))
            
            # Sort by relevance
            scored_memories.sort(key=lambda x: x[1], reverse=True)
            
            if not scored_memories:
                return f"I couldn't find any memories related to '{search_query}'. Try describing what you're looking for differently or with more context."
            
            # Format results
            response = f"Found {len(scored_memories)} memories related to '{search_query}':\n\n"
            
            for i, (memory, score) in enumerate(scored_memories[:3], 1):
                created_date = datetime.fromisoformat(memory['created_at']).strftime("%B %d, %Y")
                
                response += f"{i}. **{memory['title']}**\n"
                response += f"   {memory['content'][:150]}{'...' if len(memory['content']) > 150 else ''}\n"
                response += f"   *{created_date} - Relevance: {score:.0%}*\n\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Error searching memories: {e}")
            return "I had trouble searching your memories. Please try again."
    
    async def _generate_timeline(self, user_input: str, context: Dict[str, Any]) -> str:
        """Generate a chronological timeline of memories."""
        try:
            user_id = context['user_id']
            
            # Get memories ordered by creation date
            result = self.supabase.table('memories')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('created_at', desc=False)\
                .execute()
            
            if not result.data:
                return "You don't have any memories yet to create a timeline."
            
            memories = result.data
            
            # Group by time periods
            timeline = self._group_memories_by_period(memories)
            
            response = "## Your Memory Timeline\n\n"
            
            for period, period_memories in timeline.items():
                response += f"### {period}\n"
                for memory in period_memories:
                    memory_type = memory['memory_type'].replace('_', ' ').title()
                    created_date = datetime.fromisoformat(memory['created_at']).strftime("%B %d")
                    
                    response += f"• **{memory['title']}** ({memory_type}) - {created_date}\n"
                
                response += "\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating timeline: {e}")
            return "I couldn't generate your timeline right now. Please try again."
    
    async def _analyze_relationships(self, user_input: str, context: Dict[str, Any]) -> str:
        """Analyze relationship patterns in memories."""
        try:
            user_id = context['user_id']
            
            # Get all memories with relationships
            result = self.supabase.table('memories')\
                .select('*')\
                .eq('user_id', user_id)\
                .execute()
            
            if not result.data:
                return "You don't have any memories with relationship data yet."
            
            # Analyze relationship patterns
            relationship_data = {}
            for memory in result.data:
                if memory.get('relationships'):
                    try:
                        relationships = json.loads(memory['relationships'])
                        for person in relationships:
                            if person not in relationship_data:
                                relationship_data[person] = []
                            relationship_data[person].append(memory)
                    except json.JSONDecodeError:
                        continue
            
            if not relationship_data:
                return "I haven't found any relationship connections in your memories yet."
            
            # Format the response
            response = "## Your Relationship Connections\n\n"
            
            # Sort by number of memory connections
            sorted_relationships = sorted(relationship_data.items(), key=lambda x: len(x[1]), reverse=True)
            
            for person, memories in sorted_relationships[:5]:
                response += f"**{person}** - {len(memories)} memories connected\n"
                
                # Show recent memory with this person
                latest_memory = max(memories, key=lambda m: m['created_at'])
                response += f"   Latest: {latest_memory['title']} ({datetime.fromisoformat(latest_memory['created_at']).strftime('%B %d, %Y')})\n\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Error analyzing relationships: {e}")
            return "I couldn't analyze your relationships right now. Please try again."
    
    async def _analyze_memory_content(self, content: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze memory content to extract metadata."""
        try:
            prompt = f"""Analyze this memory content and extract metadata in JSON format:

Content: "{content}"

Extract:
{{
  "title": "Brief descriptive title (max 100 chars)",
  "memory_type": "milestone|achievement|relationship|experience|learning|general",
  "importance_score": 0.75,
  "emotional_tone": "positive|negative|neutral|mixed",
  "tags": ["tag1", "tag2", "tag3"],
  "relationships": ["person1", "person2"],
  "locations": ["location1"],
  "time_context": "today|this week|this month|specific date if mentioned"
}}

Return only the JSON:"""
            
            response = self.ai_model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean and parse JSON
            if response_text.startswith('```json'):
                response_text = response_text[7:-3]
            
            try:
                analysis = json.loads(response_text)
                
                # Validate and set defaults
                analysis['title'] = analysis.get('title', content[:100])
                analysis['memory_type'] = analysis.get('memory_type', 'general')
                analysis['importance_score'] = max(0.0, min(1.0, analysis.get('importance_score', 0.5)))
                analysis['emotional_tone'] = analysis.get('emotional_tone', 'neutral')
                analysis['tags'] = analysis.get('tags', [])
                analysis['relationships'] = analysis.get('relationships', [])
                analysis['locations'] = analysis.get('locations', [])
                analysis['time_context'] = analysis.get('time_context', 'today')
                
                return analysis
                
            except json.JSONDecodeError:
                # Fallback analysis
                return self._fallback_memory_analysis(content)
                
        except Exception as e:
            logger.error(f"Error analyzing memory content: {e}")
            return self._fallback_memory_analysis(content)
    
    def _fallback_memory_analysis(self, content: str) -> Dict[str, Any]:
        """Fallback analysis when AI analysis fails."""
        return {
            'title': content[:50] + ('...' if len(content) > 50 else ''),
            'memory_type': 'general',
            'importance_score': 0.5,
            'emotional_tone': 'neutral',
            'tags': ['unclassified'],
            'relationships': [],
            'locations': [],
            'time_context': 'today'
        }
    
    async def _update_relationship_mappings(self, user_id: str, memory_id: int, relationships: List[str]):
        """Update relationship mappings in the database."""
        try:
            for person in relationships:
                relationship_data = {
                    'user_id': user_id,
                    'memory_id': memory_id,
                    'person_name': person,
                    'connection_strength': 1.0,  # Could be calculated based on context
                    'created_at': datetime.now().isoformat()
                }
                
                self.supabase.table('memory_relationships').insert(relationship_data).execute()
                
        except Exception as e:
            logger.error(f"Error updating relationship mappings: {e}")
    
    async def _extract_search_terms(self, query: str) -> str:
        """AI-powered extraction of semantic search intent from user query."""
        try:
            system_prompt = """Extract the core search intent from this query.
            
            Remove filler words and focus on the main concepts the user wants to find.
            Return key concepts separated by spaces.
            
            Examples:
            "find my memories about my trip to Paris" → "trip Paris travel"
            "when did I graduate from college?" → "graduation college education"
            "tell me about memories with my mom" → "mom mother family relationship"
            
            Extract concepts from: "{query}"
            
            Return only the key concepts:"""
            
            response = self.ai_model.generate_content([system_prompt, query])
            search_terms = response.text.strip()
            
            # Fallback if AI response is empty or invalid
            if not search_terms or len(search_terms.split()) == 0:
                # Simple fallback: remove common stop words
                stop_words = {'find', 'search', 'look', 'for', 'about', 'when', 'did', 'i', 'me', 'my', 'tell', 'show'}
                words = query.lower().split()
                keywords = [word for word in words if word not in stop_words and len(word) > 2]
                search_terms = ' '.join(keywords)
            
            return search_terms
            
        except Exception as e:
            logger.error(f"Error in AI search term extraction: {e}")
            # Fallback to simple word extraction
            stop_words = {'find', 'search', 'look', 'for', 'about', 'when', 'did', 'i', 'me', 'my', 'tell', 'show'}
            words = query.lower().split()
            keywords = [word for word in words if word not in stop_words and len(word) > 2]
            return ' '.join(keywords)
    
    async def _calculate_relevance(self, memory: Dict[str, Any], search_query: str) -> float:
        """AI-powered calculation of semantic relevance between memory and search query."""
        try:
            memory_text = f"{memory['title']} {memory['content']}"
            
            system_prompt = """Rate the relevance between this memory and search query on a scale of 0.0 to 1.0.
            
            Consider:
            - Semantic similarity (not just exact keyword matches)
            - Contextual relevance and themes
            - Related concepts and synonyms
            - Overall topical alignment
            
            Memory: "{memory_text}"
            Search Query: "{search_query}"
            
            Respond with only a number between 0.0 and 1.0 (e.g., 0.85):"""
            
            response = self.ai_model.generate_content([system_prompt.format(memory_text=memory_text, search_query=search_query)])
            
            try:
                score = float(response.text.strip())
                return max(0.0, min(1.0, score))  # Ensure score is in valid range
            except ValueError:
                # Extract number from response if it contains extra text
                import re
                numbers = re.findall(r'\d+\.\d+|\d+', response.text)
                if numbers:
                    score = float(numbers[0])
                    return max(0.0, min(1.0, score))
                else:
                    return self._keyword_based_relevance_fallback(memory, search_query)
                    
        except Exception as e:
            logger.error(f"Error in AI relevance calculation: {e}")
            return self._keyword_based_relevance_fallback(memory, search_query)
    
    def _keyword_based_relevance_fallback(self, memory: Dict[str, Any], search_query: str) -> float:
        """Fallback keyword-based relevance calculation when AI fails."""
        memory_text = f"{memory['title']} {memory['content']}".lower()
        search_terms = search_query.lower().split()
        
        score = 0.0
        for term in search_terms:
            if term in memory_text:
                score += 1.0
        
        # Normalize by number of search terms
        return score / len(search_terms) if search_terms else 0.0
    
    def _group_memories_by_period(self, memories: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group memories by time periods."""
        timeline = {}
        
        for memory in memories:
            created_date = datetime.fromisoformat(memory['created_at'])
            
            # Group by month-year
            period = created_date.strftime("%B %Y")
            
            if period not in timeline:
                timeline[period] = []
            
            timeline[period].append(memory)
        
        return timeline
    
    async def _help_with_memories(self) -> str:
        """Provide help information about memory management."""
        return """I can help you with your memories in several ways:

**Storing Memories:**
• Just tell me something important and I'll remember it
• I'll automatically categorize it and find connections

**Finding Memories:**
• "Find memories about [topic]"
• "When did I [event]?"
• "Tell me about my memories with [person]"

**Timeline & Relationships:**
• "Show me my memory timeline"
• "What are my relationship connections?"

What would you like to do with your memories?"""