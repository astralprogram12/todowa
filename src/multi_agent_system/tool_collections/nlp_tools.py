# tool_collections/nlp_tools.py
# Collection of NLP-related tools

from ..tools import register_tool

@register_tool(
    name="extract_entities",
    category="nlp",
    description="Extract entities from text"
)
def extract_entities(text, entity_types=None):
    """Extract entities from text.
    
    Args:
        text: The text to extract entities from
        entity_types: Optional list of entity types to extract
        
    Returns:
        Dictionary of extracted entities
    """
    # This is a placeholder implementation
    # In a real implementation, this would use an NLP library like spaCy
    
    # Default entity types
    entity_types = entity_types or ['date', 'time', 'person', 'organization', 'location', 'money']
    
    # Simple rule-based entity extraction
    entities = {entity_type: [] for entity_type in entity_types}
    
    # Simple pattern matching
    import re
    
    # Date patterns
    if 'date' in entity_types:
        date_patterns = [
            r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',  # MM/DD/YYYY
            r'\b\d{1,2}-\d{1,2}-\d{2,4}\b',  # MM-DD-YYYY
            r'\b\d{4}-\d{1,2}-\d{1,2}\b',  # YYYY-MM-DD
            r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',  # Month DD, YYYY
            r'\b\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b'  # DD Month YYYY
        ]
        
        for pattern in date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                entities['date'].append(match.group())
    
    # Time patterns
    if 'time' in entity_types:
        time_patterns = [
            r'\b\d{1,2}:\d{2}\s*(?:AM|PM)?\b',  # HH:MM AM/PM
            r'\b\d{1,2}\s*(?:AM|PM)\b',  # HH AM/PM
            r'\b(?:at|around)\s+\d{1,2}(?::\d{2})?\s*(?:AM|PM)?\b'  # at/around HH:MM AM/PM
        ]
        
        for pattern in time_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                entities['time'].append(match.group())
    
    # Person patterns (very simplified)
    if 'person' in entity_types:
        person_patterns = [
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'  # First Last
        ]
        
        for pattern in person_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                entities['person'].append(match.group())
    
    # Money patterns
    if 'money' in entity_types:
        money_patterns = [
            r'\$\d+(?:\.\d{2})?',  # $XX.XX
            r'\b\d+\s+dollars\b',  # XX dollars
            r'\b\d+\s+USD\b'  # XX USD
        ]
        
        for pattern in money_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                entities['money'].append(match.group())
    
    # Remove duplicates
    for entity_type in entities:
        entities[entity_type] = list(set(entities[entity_type]))
    
    return entities

@register_tool(
    name="sentiment_analysis",
    category="nlp",
    description="Analyze sentiment of text"
)
def sentiment_analysis(text):
    """Analyze sentiment of text.
    
    Args:
        text: The text to analyze
        
    Returns:
        Dictionary with sentiment analysis results
    """
    # This is a placeholder implementation
    # In a real implementation, this would use an NLP library or API
    
    # Simple rule-based sentiment analysis
    positive_words = ['good', 'great', 'excellent', 'happy', 'like', 'love', 'positive', 
                     'wonderful', 'fantastic', 'nice', 'beautiful', 'perfect', 'best']
    negative_words = ['bad', 'terrible', 'awful', 'sad', 'dislike', 'hate', 'negative',
                     'horrible', 'worst', 'poor', 'annoying', 'disappointing', 'fail']
    
    # Convert to lowercase for case-insensitive matching
    text_lower = text.lower()
    
    # Count positive and negative words
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)
    
    # Calculate sentiment score (-1 to 1)
    total = positive_count + negative_count
    if total == 0:
        sentiment_score = 0  # Neutral
    else:
        sentiment_score = (positive_count - negative_count) / total
    
    # Determine sentiment label
    if sentiment_score > 0.3:
        sentiment = 'positive'
    elif sentiment_score < -0.3:
        sentiment = 'negative'
    else:
        sentiment = 'neutral'
    
    return {
        'sentiment': sentiment,
        'score': sentiment_score,
        'positive_words': positive_count,
        'negative_words': negative_count
    }
