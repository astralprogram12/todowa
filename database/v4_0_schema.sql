-- V4.0 Journal and Memory Classification System Database Schema
-- Enhanced database schema for AI-powered content classification

-- Content Classifications Table
-- Stores AI classification results for all user content
CREATE TABLE IF NOT EXISTS content_classifications (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES user_whatsapp(user_id) ON DELETE CASCADE,
    content_text TEXT NOT NULL,
    original_text TEXT, -- Original text before translation
    detected_language VARCHAR(50),
    translation_confidence DECIMAL(3,2),
    
    -- Classification Results
    primary_category VARCHAR(50) NOT NULL CHECK (primary_category IN ('JOURNAL_ENTRY', 'MEMORY', 'TEMPORARY_INFO', 'KNOWLEDGE')),
    confidence_journal DECIMAL(3,2) DEFAULT 0.00,
    confidence_memory DECIMAL(3,2) DEFAULT 0.00,
    confidence_temporary DECIMAL(3,2) DEFAULT 0.00,
    confidence_knowledge DECIMAL(3,2) DEFAULT 0.00,
    
    -- Content Analysis
    emotional_tone VARCHAR(20) DEFAULT 'neutral' CHECK (emotional_tone IN ('positive', 'negative', 'neutral', 'mixed')),
    temporal_significance VARCHAR(20) DEFAULT 'short_term' CHECK (temporal_significance IN ('immediate', 'short_term', 'long_term', 'permanent')),
    importance_score DECIMAL(3,2) DEFAULT 0.50 CHECK (importance_score >= 0 AND importance_score <= 1),
    
    -- Extracted Metadata
    suggested_tags JSONB DEFAULT '[]'::jsonb,
    contains_personal_info BOOLEAN DEFAULT true,
    actionable_items JSONB DEFAULT '[]'::jsonb,
    relationships_mentioned JSONB DEFAULT '[]'::jsonb,
    locations_mentioned JSONB DEFAULT '[]'::jsonb,
    time_references JSONB DEFAULT '[]'::jsonb,
    
    -- Processing Info
    classification_reasoning TEXT,
    processing_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    context_used BOOLEAN DEFAULT false,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Journals Table
-- Enhanced for mood tracking and emotional pattern recognition
CREATE TABLE IF NOT EXISTS journal_entries (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES user_whatsapp(user_id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    
    -- Mood and Emotion Analysis
    mood_score DECIMAL(4,2) CHECK (mood_score >= 1 AND mood_score <= 10),
    emotional_tone VARCHAR(20) DEFAULT 'neutral' CHECK (emotional_tone IN ('very_positive', 'positive', 'neutral', 'negative', 'very_negative', 'mixed')),
    
    -- Content Analysis
    themes JSONB DEFAULT '[]'::jsonb, -- Main topics discussed
    gratitude_elements JSONB DEFAULT '[]'::jsonb, -- Things user is grateful for
    challenges JSONB DEFAULT '[]'::jsonb, -- Difficulties mentioned
    goals_mentioned JSONB DEFAULT '[]'::jsonb, -- Goals or aspirations noted
    
    -- Privacy and Classification
    privacy_level VARCHAR(20) DEFAULT 'private' CHECK (privacy_level IN ('private', 'personal', 'shareable')),
    promoted_to_memory BOOLEAN DEFAULT false,
    classification_id INTEGER REFERENCES content_classifications(id),
    
    -- Metadata
    word_count INTEGER,
    reading_time_minutes INTEGER,
    entry_type VARCHAR(20) DEFAULT 'free_form' CHECK (entry_type IN ('free_form', 'structured', 'prompted')),
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Memories Table
-- Enhanced for relationship mapping and timeline organization
CREATE TABLE IF NOT EXISTS memories (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES user_whatsapp(user_id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    
    -- Memory Classification
    memory_type VARCHAR(50) DEFAULT 'general' CHECK (memory_type IN ('milestone', 'achievement', 'relationship', 'experience', 'learning', 'general')),
    importance_score DECIMAL(3,2) DEFAULT 0.50 CHECK (importance_score >= 0 AND importance_score <= 1),
    emotional_tone VARCHAR(20) DEFAULT 'neutral' CHECK (emotional_tone IN ('positive', 'negative', 'neutral', 'mixed')),
    
    -- Relationship and Context Data
    tags JSONB DEFAULT '[]'::jsonb,
    relationships JSONB DEFAULT '[]'::jsonb, -- People involved
    locations JSONB DEFAULT '[]'::jsonb, -- Places associated
    time_context VARCHAR(100), -- Temporal context (today, last week, etc.)
    
    -- Source Information
    source VARCHAR(50) DEFAULT 'user_input' CHECK (source IN ('user_input', 'journal_entry', 'task_completion', 'ai_suggestion')),
    source_id INTEGER, -- Reference to source record
    classification_id INTEGER REFERENCES content_classifications(id),
    
    -- Interaction Tracking
    view_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP WITH TIME ZONE,
    search_frequency INTEGER DEFAULT 0,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Memory Relationships Table
-- Maps relationships between memories and people/events
CREATE TABLE IF NOT EXISTS memory_relationships (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES user_whatsapp(user_id) ON DELETE CASCADE,
    memory_id INTEGER REFERENCES memories(id) ON DELETE CASCADE,
    
    -- Relationship Data
    person_name VARCHAR(100) NOT NULL,
    relationship_type VARCHAR(50) DEFAULT 'mentioned' CHECK (relationship_type IN ('mentioned', 'involved', 'central', 'context')),
    connection_strength DECIMAL(3,2) DEFAULT 1.00 CHECK (connection_strength >= 0 AND connection_strength <= 1),
    
    -- Metadata
    context_note TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Daily Mood Tracking Table
-- Aggregates daily mood data from journal entries
CREATE TABLE IF NOT EXISTS daily_mood_tracking (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES user_whatsapp(user_id) ON DELETE CASCADE,
    date DATE NOT NULL,
    
    -- Mood Aggregation
    mood_score DECIMAL(4,2) CHECK (mood_score >= 1 AND mood_score <= 10),
    dominant_tone VARCHAR(20) CHECK (dominant_tone IN ('very_positive', 'positive', 'neutral', 'negative', 'very_negative', 'mixed')),
    entry_count INTEGER DEFAULT 1,
    
    -- Additional Metrics
    gratitude_count INTEGER DEFAULT 0,
    challenge_count INTEGER DEFAULT 0,
    goal_mentions INTEGER DEFAULT 0,
    
    -- Unique constraint for user-date combination
    UNIQUE(user_id, date),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Memory Timelines Table
-- Organizes memories into meaningful time-based clusters
CREATE TABLE IF NOT EXISTS memory_timelines (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES user_whatsapp(user_id) ON DELETE CASCADE,
    
    -- Timeline Information
    timeline_name VARCHAR(200) NOT NULL,
    description TEXT,
    time_period_start DATE,
    time_period_end DATE,
    
    -- Timeline Type
    timeline_type VARCHAR(50) DEFAULT 'chronological' CHECK (timeline_type IN ('chronological', 'thematic', 'relationship', 'location')),
    
    -- Associated Memories (JSONB array of memory IDs)
    memory_ids JSONB DEFAULT '[]'::jsonb,
    
    -- Metadata
    auto_generated BOOLEAN DEFAULT false,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User Content Preferences Table
-- Stores user preferences for content classification and privacy
CREATE TABLE IF NOT EXISTS user_content_preferences (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES user_whatsapp(user_id) ON DELETE CASCADE UNIQUE,
    
    -- Classification Preferences
    auto_classify_content BOOLEAN DEFAULT true,
    auto_promote_to_memory BOOLEAN DEFAULT true,
    memory_promotion_threshold DECIMAL(3,2) DEFAULT 0.75,
    
    -- Privacy Preferences
    default_privacy_level VARCHAR(20) DEFAULT 'private' CHECK (default_privacy_level IN ('private', 'personal', 'shareable')),
    allow_mood_analysis BOOLEAN DEFAULT true,
    allow_relationship_mapping BOOLEAN DEFAULT true,
    
    -- Journal Preferences
    journal_reminders_enabled BOOLEAN DEFAULT false,
    preferred_journal_time TIME,
    weekly_review_enabled BOOLEAN DEFAULT true,
    
    -- Memory Preferences
    memory_timeline_auto_generation BOOLEAN DEFAULT true,
    memory_search_include_journal BOOLEAN DEFAULT true,
    
    -- AI Preferences
    personalized_prompts BOOLEAN DEFAULT true,
    emotional_insights BOOLEAN DEFAULT true,
    pattern_analysis BOOLEAN DEFAULT true,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Content Search Index Table
-- For semantic search capabilities (simplified vector approach)
CREATE TABLE IF NOT EXISTS content_search_index (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES user_whatsapp(user_id) ON DELETE CASCADE,
    
    -- Source Information
    source_type VARCHAR(20) NOT NULL CHECK (source_type IN ('journal', 'memory', 'task')),
    source_id INTEGER NOT NULL,
    
    -- Search Data
    content_summary TEXT NOT NULL,
    keywords JSONB DEFAULT '[]'::jsonb,
    semantic_tags JSONB DEFAULT '[]'::jsonb,
    
    -- Search Metrics
    search_frequency INTEGER DEFAULT 0,
    last_searched TIMESTAMP WITH TIME ZONE,
    
    -- Indexing
    search_vector TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('english', content_summary)
    ) STORED,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_content_classifications_user_category ON content_classifications(user_id, primary_category);
CREATE INDEX IF NOT EXISTS idx_content_classifications_timestamp ON content_classifications(processing_timestamp);

CREATE INDEX IF NOT EXISTS idx_journal_entries_user_date ON journal_entries(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_journal_entries_mood ON journal_entries(user_id, mood_score);
CREATE INDEX IF NOT EXISTS idx_journal_entries_emotional_tone ON journal_entries(user_id, emotional_tone);

CREATE INDEX IF NOT EXISTS idx_memories_user_type ON memories(user_id, memory_type);
CREATE INDEX IF NOT EXISTS idx_memories_user_importance ON memories(user_id, importance_score);
CREATE INDEX IF NOT EXISTS idx_memories_user_date ON memories(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_memories_search_frequency ON memories(user_id, search_frequency);

CREATE INDEX IF NOT EXISTS idx_memory_relationships_user ON memory_relationships(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_relationships_person ON memory_relationships(user_id, person_name);

CREATE INDEX IF NOT EXISTS idx_daily_mood_user_date ON daily_mood_tracking(user_id, date);

CREATE INDEX IF NOT EXISTS idx_content_search_user_type ON content_search_index(user_id, source_type);
CREATE INDEX IF NOT EXISTS idx_content_search_vector ON content_search_index USING GIN(search_vector);

-- Create functions for automatic timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for automatic timestamp updates
CREATE TRIGGER update_content_classifications_updated_at BEFORE UPDATE ON content_classifications FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_journal_entries_updated_at BEFORE UPDATE ON journal_entries FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_memories_updated_at BEFORE UPDATE ON memories FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_daily_mood_tracking_updated_at BEFORE UPDATE ON daily_mood_tracking FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_memory_timelines_updated_at BEFORE UPDATE ON memory_timelines FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_content_preferences_updated_at BEFORE UPDATE ON user_content_preferences FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_content_search_index_updated_at BEFORE UPDATE ON content_search_index FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default content preferences for existing users
INSERT INTO user_content_preferences (user_id)
SELECT user_id FROM user_whatsapp 
WHERE user_id NOT IN (SELECT user_id FROM user_content_preferences)
ON CONFLICT (user_id) DO NOTHING;

-- Add RLS (Row Level Security) policies for data privacy
ALTER TABLE content_classifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE journal_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_mood_tracking ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_timelines ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_content_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_search_index ENABLE ROW LEVEL SECURITY;

-- Create RLS policies to ensure users can only access their own data
CREATE POLICY content_classifications_user_policy ON content_classifications FOR ALL USING (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY journal_entries_user_policy ON journal_entries FOR ALL USING (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY memories_user_policy ON memories FOR ALL USING (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY memory_relationships_user_policy ON memory_relationships FOR ALL USING (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY daily_mood_tracking_user_policy ON daily_mood_tracking FOR ALL USING (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY memory_timelines_user_policy ON memory_timelines FOR ALL USING (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY user_content_preferences_user_policy ON user_content_preferences FOR ALL USING (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY content_search_index_user_policy ON content_search_index FOR ALL USING (user_id = current_setting('app.current_user_id')::uuid);

-- Comments for documentation
COMMENT ON TABLE content_classifications IS 'AI-powered content classification results for all user content';
COMMENT ON TABLE journal_entries IS 'Personal journal entries with mood tracking and emotional analysis';
COMMENT ON TABLE memories IS 'Important events and experiences with relationship mapping';
COMMENT ON TABLE memory_relationships IS 'Relationship mappings between memories and people/events';
COMMENT ON TABLE daily_mood_tracking IS 'Daily aggregated mood data from journal entries';
COMMENT ON TABLE memory_timelines IS 'Organized timelines of memories for narrative structure';
COMMENT ON TABLE user_content_preferences IS 'User preferences for content classification and privacy';
COMMENT ON TABLE content_search_index IS 'Search index for semantic content retrieval';

COMMENT ON COLUMN content_classifications.primary_category IS 'AI-determined primary classification: JOURNAL_ENTRY, MEMORY, TEMPORARY_INFO, or KNOWLEDGE';
COMMENT ON COLUMN journal_entries.mood_score IS 'Mood score from 1 (very negative) to 10 (very positive)';
COMMENT ON COLUMN memories.importance_score IS 'AI-calculated importance score from 0 to 1';
COMMENT ON COLUMN memory_relationships.connection_strength IS 'Strength of relationship connection from 0 to 1';