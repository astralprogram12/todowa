"""
Journal Agent

Handles daily journal entries and personal reflections with:
- Mood tracking and emotional pattern recognition
- Integration with memory system for significant entries
- Privacy-focused design with secure storage
- Support for both structured and free-form journaling
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

class JournalAgent(BaseAgent):
    """Intelligent journal management agent with mood tracking and privacy focus."""
    
    def __init__(self, supabase, ai_model, agent_name="JournalAgent"):
        """Initialize the journal agent."""
        super().__init__(supabase, ai_model, agent_name)
        # AI-powered mood analysis - no hardcoded keywords needed
        self.mood_scale = {
            'very_positive': {'score': 9.0, 'range': (8.0, 10.0)},
            'positive': {'score': 7.0, 'range': (6.0, 7.9)},
            'neutral': {'score': 5.0, 'range': (4.0, 5.9)},
            'negative': {'score': 3.0, 'range': (2.0, 3.9)},
            'very_negative': {'score': 1.0, 'range': (0.0, 1.9)}
        }
    
    async def process(self, user_input: str, context: Dict[str, Any], routing_info: Dict[str, Any] = None) -> str:
        """Process journal-related requests."""
        try:
            # Determine the journal operation
            operation = self._determine_operation(user_input, context)
            
            user_id = context.get('user_id')
            if not user_id:
                return "I need to identify you before I can help with your journal."
            
            if operation == 'create':
                return await self._create_journal_entry(user_input, context)
            elif operation == 'read':
                return await self._read_journal_entries(user_input, context)
            elif operation == 'mood_analysis':
                return await self._analyze_mood_patterns(user_input, context)
            elif operation == 'weekly_review':
                return await self._generate_weekly_review(user_input, context)
            elif operation == 'prompts':
                return await self._provide_journal_prompts(user_input, context)
            else:
                return await self._help_with_journaling()
                
        except Exception as e:
            logger.error(f"Error in journal processing: {e}")
            return "I'm having trouble with journaling right now. Please try again later."
    
    async def _determine_operation(self, user_input: str, context: Dict[str, Any]) -> str:
        """AI-powered determination of journal operation intent."""
        try:
            system_prompt = """You are an expert at understanding user intent for journaling operations.
            
            Analyze the user input and determine the operation type:
            - "create": User wants to write a new journal entry or reflection
            - "read": User wants to view past journal entries
            - "mood_analysis": User wants to understand emotional patterns or mood trends
            - "weekly_review": User wants a summary or review of their week
            - "prompts": User needs inspiration or ideas for what to write about
            
            Consider context, emotional tone, and intent regardless of specific words used.
            Return only one word: create, read, mood_analysis, weekly_review, or prompts"""
            
            user_prompt = f"Determine the journal operation for: {user_input}"
            
            response = self.ai_model.generate_content([system_prompt, user_prompt])
            operation = response.text.strip().lower()
            
            # Validate response
            valid_operations = ['create', 'read', 'mood_analysis', 'weekly_review', 'prompts']
            return operation if operation in valid_operations else 'create'
            
        except Exception as e:
            logger.error(f"Error in AI operation determination: {e}")
            return 'create'  # Safe default
    
    async def _create_journal_entry(self, user_input: str, context: Dict[str, Any]) -> str:
        """Create a new journal entry with mood analysis."""
        try:
            user_id = context['user_id']
            
            # Analyze the journal entry
            analysis = await self._analyze_journal_content(user_input, context)
            
            # Create the journal entry
            entry_data = {
                'user_id': user_id,
                'title': analysis['title'],
                'content': user_input,
                'mood_score': analysis['mood_score'],
                'emotional_tone': analysis['emotional_tone'],
                'themes': json.dumps(analysis['themes']),
                'gratitude_elements': json.dumps(analysis['gratitude_elements']),
                'challenges': json.dumps(analysis['challenges']),
                'goals_mentioned': json.dumps(analysis['goals_mentioned']),
                'privacy_level': 'private',  # Always private for journal entries
                'created_at': datetime.now().isoformat()
            }
            
            result = self.supabase.table('journal_entries').insert(entry_data).execute()
            
            if result.data:
                entry_id = result.data[0]['id']
                
                # Check if this entry should become a memory
                if analysis['memory_worthy']:
                    await self._promote_to_memory(user_id, result.data[0], analysis)
                
                # Update mood tracking
                await self._update_mood_tracking(user_id, analysis['mood_score'], analysis['emotional_tone'])
                
                # Log the action
                self._log_action(user_id, 'create', 'journal_entry', entry_id,
                               {'title': analysis['title'], 'mood': analysis['emotional_tone']})
                
                response = f"✍️ Journal entry saved: '{analysis['title']}'\n\n"
                response += f"🎭 Detected mood: {analysis['emotional_tone']} (score: {analysis['mood_score']:.1f}/10)\n"
                
                if analysis['gratitude_elements']:
                    response += f"🙏 Gratitude noted: {len(analysis['gratitude_elements'])} elements\n"
                
                if analysis['challenges']:
                    response += f"💪 Challenges identified: {len(analysis['challenges'])}\n"
                
                if analysis['memory_worthy']:
                    response += f"⭐ This entry was promoted to your memories!\n"
                
                return response
            else:
                raise Exception("Failed to save journal entry")
                
        except Exception as e:
            logger.error(f"Error creating journal entry: {e}")
            return "I couldn't save your journal entry right now. Please try again."
    
    async def _read_journal_entries(self, user_input: str, context: Dict[str, Any]) -> str:
        """Read recent journal entries."""
        try:
            user_id = context['user_id']
            
            # Parse request for specific timeframe
            timeframe = self._extract_timeframe(user_input)
            
            # Build query based on timeframe
            query = self.supabase.table('journal_entries')\
                .select('*')\
                .eq('user_id', user_id)
            
            if timeframe['days']:
                cutoff_date = (datetime.now() - timedelta(days=timeframe['days'])).isoformat()
                query = query.gte('created_at', cutoff_date)
            
            result = query.order('created_at', desc=True).limit(10).execute()
            
            if not result.data:
                return "You don't have any journal entries yet. Would you like to start journaling?"
            
            entries = result.data
            
            # Format the response
            response = f"📖 Your recent journal entries ({len(entries)} entries):\n\n"
            
            for i, entry in enumerate(entries, 1):
                created_date = datetime.fromisoformat(entry['created_at']).strftime("%B %d, %Y")
                mood_emoji = self._get_mood_emoji(entry['emotional_tone'])
                
                response += f"{i}. **{entry['title']}** {mood_emoji}\n"
                response += f"   {entry['content'][:150]}{'...' if len(entry['content']) > 150 else ''}\n"
                response += f"   *{created_date} - Mood: {entry['emotional_tone']} ({entry['mood_score']:.1f}/10)*\n\n"
            
            # Add mood insights
            avg_mood = sum(entry['mood_score'] for entry in entries) / len(entries)
            response += f"📊 Average mood over this period: {avg_mood:.1f}/10"
            
            return response
            
        except Exception as e:
            logger.error(f"Error reading journal entries: {e}")
            return "I couldn't retrieve your journal entries right now. Please try again."
    
    async def _analyze_mood_patterns(self, user_input: str, context: Dict[str, Any]) -> str:
        """Analyze mood patterns over time."""
        try:
            user_id = context['user_id']
            
            # Get entries from last 30 days
            cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()
            result = self.supabase.table('journal_entries')\
                .select('*')\
                .eq('user_id', user_id)\
                .gte('created_at', cutoff_date)\
                .order('created_at', desc=False)\
                .execute()
            
            if not result.data:
                return "I need more journal entries to analyze your mood patterns. Keep journaling!"
            
            entries = result.data
            
            # Analyze patterns
            mood_analysis = self._calculate_mood_patterns(entries)
            
            response = "🎭 **Your Mood Analysis (Last 30 Days)**\n\n"
            response += f"📈 **Overall Trend:** {mood_analysis['trend']}\n"
            response += f"📊 **Average Mood:** {mood_analysis['average']:.1f}/10\n"
            response += f"🎯 **Most Common Mood:** {mood_analysis['most_common']}\n\n"
            
            response += "📅 **Weekly Breakdown:**\n"
            for week, data in mood_analysis['weekly'].items():
                response += f"   Week {week}: {data['average']:.1f}/10 ({data['dominant_mood']})\n"
            
            response += f"\n🌟 **Best Days:** {', '.join(mood_analysis['best_days'])}\n"
            response += f"💙 **Growth Areas:** {', '.join(mood_analysis['improvement_areas'])}\n"
            
            if mood_analysis['patterns']:
                response += f"\n🔍 **Patterns Noticed:**\n"
                for pattern in mood_analysis['patterns']:
                    response += f"   • {pattern}\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Error analyzing mood patterns: {e}")
            return "I couldn't analyze your mood patterns right now. Please try again."
    
    async def _generate_weekly_review(self, user_input: str, context: Dict[str, Any]) -> str:
        """Generate a weekly journal review."""
        try:
            user_id = context['user_id']
            
            # Get entries from last 7 days
            cutoff_date = (datetime.now() - timedelta(days=7)).isoformat()
            result = self.supabase.table('journal_entries')\
                .select('*')\
                .eq('user_id', user_id)\
                .gte('created_at', cutoff_date)\
                .order('created_at', desc=False)\
                .execute()
            
            if not result.data:
                return "You haven't journaled this week yet. Start writing to get a weekly review!"
            
            entries = result.data
            
            # Generate review using AI
            review = await self._ai_generate_weekly_review(entries)
            
            return review
            
        except Exception as e:
            logger.error(f"Error generating weekly review: {e}")
            return "I couldn't generate your weekly review right now. Please try again."
    
    async def _provide_journal_prompts(self, user_input: str, context: Dict[str, Any]) -> str:
        """Provide personalized journal prompts."""
        try:
            user_id = context['user_id']
            
            # Get recent entries to personalize prompts
            result = self.supabase.table('journal_entries')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('created_at', desc=True)\
                .limit(5)\
                .execute()
            
            recent_themes = []
            if result.data:
                for entry in result.data:
                    if entry.get('themes'):
                        try:
                            themes = json.loads(entry['themes'])
                            recent_themes.extend(themes)
                        except json.JSONDecodeError:
                            continue
            
            # Generate personalized prompts
            prompts = await self._generate_personalized_prompts(recent_themes, context)
            
            response = "✨ **Journal Prompts for You**\n\n"
            
            for i, prompt in enumerate(prompts, 1):
                response += f"{i}. {prompt}\n\n"
            
            response += "💡 Choose one that resonates with you, or let them inspire your own reflection!"
            
            return response
            
        except Exception as e:
            logger.error(f"Error providing journal prompts: {e}")
            return "I couldn't generate journal prompts right now. Please try again."
    
    async def _analyze_journal_content(self, content: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze journal content for mood, themes, and significance."""
        try:
            prompt = f"""Analyze this journal entry and extract insights in JSON format:

Content: "{content}"

Extract:
{{
  "title": "Brief descriptive title (max 80 chars)",
  "mood_score": 7.5,
  "emotional_tone": "positive|negative|neutral|mixed",
  "themes": ["theme1", "theme2"],
  "gratitude_elements": ["thing1", "thing2"],
  "challenges": ["challenge1"],
  "goals_mentioned": ["goal1"],
  "memory_worthy": true,
  "significance_reason": "Why this might be memory-worthy"
}}

Guidelines:
- mood_score: 1-10 scale (1=very negative, 10=very positive)
- themes: Main topics/subjects discussed
- gratitude_elements: Things the person is grateful for
- challenges: Difficulties or obstacles mentioned
- goals_mentioned: Any aspirations or objectives noted
- memory_worthy: true if this contains significant life events/milestones

Return only the JSON:"""
            
            response = self.ai_model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean and parse JSON
            if response_text.startswith('```json'):
                response_text = response_text[7:-3]
            
            try:
                analysis = json.loads(response_text)
                
                # Validate and set defaults
                analysis['title'] = analysis.get('title', content[:50])
                analysis['mood_score'] = max(1.0, min(10.0, analysis.get('mood_score', 5.0)))
                analysis['emotional_tone'] = analysis.get('emotional_tone', 'neutral')
                analysis['themes'] = analysis.get('themes', [])
                analysis['gratitude_elements'] = analysis.get('gratitude_elements', [])
                analysis['challenges'] = analysis.get('challenges', [])
                analysis['goals_mentioned'] = analysis.get('goals_mentioned', [])
                analysis['memory_worthy'] = analysis.get('memory_worthy', False)
                analysis['significance_reason'] = analysis.get('significance_reason', '')
                
                return analysis
                
            except json.JSONDecodeError:
                return await self._fallback_journal_analysis(content)
                
        except Exception as e:
            logger.error(f"Error analyzing journal content: {e}")
            return await self._fallback_journal_analysis(content)
    
    async def _fallback_journal_analysis(self, content: str) -> Dict[str, Any]:
        """AI-powered fallback analysis when primary AI analysis fails."""
        try:
            # Simplified AI prompt for fallback
            simple_prompt = f"""Analyze this text briefly:

Text: "{content}"

Provide mood score (1-10) and emotional tone (positive/negative/neutral/mixed). Respond with just:
score: X.X
tone: emotion"""
            
            response = self.ai_model.generate_content(simple_prompt)
            response_lines = response.text.strip().split('\n')
            
            mood_score = 5.0
            emotional_tone = 'neutral'
            
            for line in response_lines:
                if 'score:' in line.lower():
                    try:
                        mood_score = float(line.split(':')[1].strip())
                    except (ValueError, IndexError):
                        pass
                elif 'tone:' in line.lower():
                    emotional_tone = line.split(':')[1].strip().lower()
            
            return {
                'title': content[:50] + ('...' if len(content) > 50 else ''),
                'mood_score': max(1.0, min(10.0, mood_score)),
                'emotional_tone': emotional_tone,
                'themes': ['unclassified'],
                'gratitude_elements': [],
                'challenges': [],
                'goals_mentioned': [],
                'memory_worthy': False,
                'significance_reason': ''
            }
            
        except Exception as e:
            logger.error(f"Error in AI fallback analysis: {e}")
            # Ultimate fallback with neutral values
            return {
                'title': content[:50] + ('...' if len(content) > 50 else ''),
                'mood_score': 5.0,
                'emotional_tone': 'neutral',
                'themes': ['unclassified'],
                'gratitude_elements': [],
                'challenges': [],
                'goals_mentioned': [],
                'memory_worthy': False,
                'significance_reason': ''
            }
    
    async def _promote_to_memory(self, user_id: str, entry: Dict[str, Any], analysis: Dict[str, Any]):
        """Promote a significant journal entry to memories."""
        try:
            memory_data = {
                'user_id': user_id,
                'title': f"Journal Memory: {analysis['title']}",
                'content': entry['content'],
                'memory_type': 'experience',
                'importance_score': min(analysis['mood_score'] / 10, 1.0),
                'emotional_tone': analysis['emotional_tone'],
                'tags': json.dumps(analysis['themes'] + ['journal']),
                'source': 'journal_entry',
                'source_id': entry['id'],
                'created_at': entry['created_at']
            }
            
            self.supabase.table('memories').insert(memory_data).execute()
            
        except Exception as e:
            logger.error(f"Error promoting journal to memory: {e}")
    
    async def _update_mood_tracking(self, user_id: str, mood_score: float, emotional_tone: str):
        """Update mood tracking statistics."""
        try:
            today = datetime.now().date().isoformat()
            
            # Check if there's already a mood entry for today
            existing = self.supabase.table('daily_mood_tracking')\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('date', today)\
                .execute()
            
            if existing.data:
                # Update existing entry with average
                current = existing.data[0]
                new_avg_score = (current['mood_score'] + mood_score) / 2
                
                self.supabase.table('daily_mood_tracking')\
                    .update({
                        'mood_score': new_avg_score,
                        'dominant_tone': emotional_tone,
                        'entry_count': current['entry_count'] + 1
                    })\
                    .eq('id', current['id'])\
                    .execute()
            else:
                # Create new entry
                mood_data = {
                    'user_id': user_id,
                    'date': today,
                    'mood_score': mood_score,
                    'dominant_tone': emotional_tone,
                    'entry_count': 1
                }
                
                self.supabase.table('daily_mood_tracking').insert(mood_data).execute()
                
        except Exception as e:
            logger.error(f"Error updating mood tracking: {e}")
    
    def _extract_timeframe(self, text: str) -> Dict[str, Any]:
        """Extract timeframe from user request."""
        text_lower = text.lower()
        
        if 'today' in text_lower:
            return {'days': 1}
        elif 'week' in text_lower or 'last 7 days' in text_lower:
            return {'days': 7}
        elif 'month' in text_lower or 'last 30 days' in text_lower:
            return {'days': 30}
        else:
            return {'days': 7}  # Default to last week
    
    def _get_mood_emoji(self, emotional_tone: str) -> str:
        """Get emoji representation of mood."""
        mood_emojis = {
            'very positive': '😄',
            'positive': '😊',
            'neutral': '😐',
            'negative': '😔',
            'very negative': '😢',
            'mixed': '😅'
        }
        return mood_emojis.get(emotional_tone, '😐')
    
    def _calculate_mood_patterns(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate mood patterns from journal entries."""
        if not entries:
            return {}
        
        # Basic pattern analysis
        total_score = sum(entry['mood_score'] for entry in entries)
        average_mood = total_score / len(entries)
        
        # Find most common emotional tone
        tone_counts = {}
        for entry in entries:
            tone = entry['emotional_tone']
            tone_counts[tone] = tone_counts.get(tone, 0) + 1
        
        most_common = max(tone_counts, key=tone_counts.get)
        
        # Determine trend (simplified)
        first_half = entries[:len(entries)//2]
        second_half = entries[len(entries)//2:]
        
        if first_half and second_half:
            first_avg = sum(e['mood_score'] for e in first_half) / len(first_half)
            second_avg = sum(e['mood_score'] for e in second_half) / len(second_half)
            
            if second_avg > first_avg + 0.5:
                trend = "Improving ⬆️"
            elif first_avg > second_avg + 0.5:
                trend = "Declining ⬇️"
            else:
                trend = "Stable ➡️"
        else:
            trend = "Stable ➡️"
        
        # Find best days
        best_entries = sorted(entries, key=lambda x: x['mood_score'], reverse=True)[:3]
        best_days = [datetime.fromisoformat(e['created_at']).strftime('%B %d') for e in best_entries]
        
        return {
            'average': average_mood,
            'most_common': most_common,
            'trend': trend,
            'weekly': {},  # Would implement weekly breakdown
            'best_days': best_days,
            'improvement_areas': ['Consider more gratitude practices'] if average_mood < 6 else [],
            'patterns': ['You tend to write more when feeling reflective']
        }
    
    async def _ai_generate_weekly_review(self, entries: List[Dict[str, Any]]) -> str:
        """Generate an AI-powered weekly review."""
        try:
            # Prepare entry summaries for AI
            entry_summaries = []
            for entry in entries:
                created_date = datetime.fromisoformat(entry['created_at']).strftime('%A, %B %d')
                entry_summaries.append(f"{created_date}: {entry['title']} (Mood: {entry['mood_score']}/10)")
            
            prompt = f"""Create a thoughtful weekly journal review based on these entries:

{chr(10).join(entry_summaries)}

Provide a warm, encouraging review that includes:
1. Overall week summary
2. Mood patterns observed
3. Key themes or insights
4. Growth areas
5. Encouragement for next week

Write in a personal, supportive tone as if you're a caring friend reviewing their week."""
            
            response = self.ai_model.generate_content(prompt)
            
            return f"📝 **Your Weekly Journal Review**\n\n{response.text.strip()}"
            
        except Exception as e:
            logger.error(f"Error generating weekly review: {e}")
            return "I couldn't generate your weekly review, but I can see you've been journaling regularly. Keep up the great work!"
    
    async def _generate_personalized_prompts(self, recent_themes: List[str], context: Dict[str, Any]) -> List[str]:
        """Generate personalized journal prompts based on user's recent themes."""
        base_prompts = [
            "What are three things you're grateful for today, and why do they matter to you?",
            "Describe a moment from this week that made you smile.",
            "What's one challenge you're facing, and what's one small step you could take?",
            "If you could give your past self advice, what would you say?",
            "What's something new you learned about yourself recently?",
            "Describe your ideal tomorrow. What would make it special?",
            "What's a relationship in your life you're thankful for, and why?",
            "What's one goal you're working towards, and how did you progress today?",
            "Describe a place that makes you feel peaceful.",
            "What's one act of kindness you witnessed or performed recently?"
        ]
        
        # For now, return base prompts. Could be enhanced with AI personalization
        return base_prompts[:5]
    
    async def _help_with_journaling(self) -> str:
        """Provide help information about journaling."""
        return """✍️ **Journal Features Available:**

**Creating Entries:**
• Just start writing your thoughts - I'll automatically save and analyze
• Tell me how your day went or what you're feeling
• I'll track your mood and identify themes

**Reading & Analysis:**
• "Show my recent entries" - View past journal entries
• "Analyze my mood" - Get mood pattern insights
• "Weekly review" - Get an AI-generated summary

**Journal Prompts:**
• "Give me journal prompts" - Get personalized writing ideas
• I'll suggest topics based on your recent entries

**Privacy:**
• All journal entries are completely private
• Only significant entries are promoted to memories (with your permission)

What would you like to journal about today?"""