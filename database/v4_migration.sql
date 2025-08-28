-- V4.0 Database Migration Script
-- This script adds all v4.0 tables if they don't exist and creates necessary indexes

-- Content Classifications Table
CREATE TABLE IF NOT EXISTS content_classifications (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES user_whatsapp(user_id) ON DELETE CASCADE,
    content_text TEXT NOT NULL,
    original_text TEXT,
    detected_language VARCHAR(50),
    translation_confidence DECIMAL(3,2),
    
    primary_category VARCHAR(50) NOT NULL CHECK (primary_category IN ('JOURNAL_ENTRY', 'MEMORY', 'TEMPORARY_INFO', 'KNOWLEDGE')),
    confidence_journal DECIMAL(3,2) DEFAULT 0.00,
    confidence_memory DECIMAL(3,2) DEFAULT 0.00,
    confidence_temporary DECIMAL(3,2) DEFAULT 0.00,
    confidence_knowledge DECIMAL(3,2) DEFAULT 0.00,
    
    emotional_tone VARCHAR(20) DEFAULT 'neutral' CHECK (emotional_tone IN ('positive', 'negative', 'neutral', 'mixed')),
    temporal_significance VARCHAR(20) DEFAULT 'short_term' CHECK (temporal_significance IN ('immediate', 'short_term', 'long_term', 'permanent')),
    importance_score DECIMAL(3,2) DEFAULT 0.50 CHECK (importance_score >= 0 AND importance_score <= 1),
    
    suggested_tags JSONB DEFAULT '[]'::jsonb,
    contains_personal_info BOOLEAN DEFAULT true,
    actionable_items JSONB DEFAULT '[]'::jsonb,
    relationships_mentioned JSONB DEFAULT '[]'::jsonb,
    locations_mentioned JSONB DEFAULT '[]'::jsonb,
    time_references JSONB DEFAULT '[]'::jsonb,
    
    classification_reasoning TEXT,
    processing_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    context_used BOOLEAN DEFAULT false,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Journal Entries Table (using new v4.0 name)
CREATE TABLE IF NOT EXISTS journal_entries (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES user_whatsapp(user_id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    
    mood_score DECIMAL(4,2) CHECK (mood_score >= 1 AND mood_score <= 10),
    emotional_tone VARCHAR(20) DEFAULT 'neutral' CHECK (emotional_tone IN ('very_positive', 'positive', 'neutral', 'negative', 'very_negative', 'mixed')),
    
    themes JSONB DEFAULT '[]'::jsonb,
    gratitude_elements JSONB DEFAULT '[]'::jsonb,
    challenges JSONB DEFAULT '[]'::jsonb,
    goals_mentioned JSONB DEFAULT '[]'::jsonb,
    
    privacy_level VARCHAR(20) DEFAULT 'private' CHECK (privacy_level IN ('private', 'personal', 'shareable')),
    promoted_to_memory BOOLEAN DEFAULT false,
    classification_id INTEGER REFERENCES content_classifications(id),
    
    word_count INTEGER,
    reading_time_minutes INTEGER,
    entry_type VARCHAR(20) DEFAULT 'free_form' CHECK (entry_type IN ('free_form', 'structured', 'prompted')),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Memories Table (using new v4.0 name) 
CREATE TABLE IF NOT EXISTS memories (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES user_whatsapp(user_id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    
    memory_type VARCHAR(50) DEFAULT 'general' CHECK (memory_type IN ('milestone', 'achievement', 'relationship', 'experience', 'learning', 'general')),
    importance_score DECIMAL(3,2) DEFAULT 0.50 CHECK (importance_score >= 0 AND importance_score <= 1),
    emotional_tone VARCHAR(20) DEFAULT 'neutral' CHECK (emotional_tone IN ('positive', 'negative', 'neutral', 'mixed')),
    
    tags JSONB DEFAULT '[]'::jsonb,
    relationships JSONB DEFAULT '[]'::jsonb,
    locations JSONB DEFAULT '[]'::jsonb,
    time_context VARCHAR(100),
    
    source VARCHAR(50) DEFAULT 'user_input' CHECK (source IN ('user_input', 'journal_entry', 'task_completion', 'ai_suggestion')),
    source_id INTEGER,
    classification_id INTEGER REFERENCES content_classifications(id),
    
    view_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP WITH TIME ZONE,
    search_frequency INTEGER DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Daily Mood Tracking Table
CREATE TABLE IF NOT EXISTS daily_mood_tracking (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES user_whatsapp(user_id) ON DELETE CASCADE,
    date DATE NOT NULL,
    
    mood_score DECIMAL(4,2) CHECK (mood_score >= 1 AND mood_score <= 10),
    dominant_tone VARCHAR(20) CHECK (dominant_tone IN ('very_positive', 'positive', 'neutral', 'negative', 'very_negative', 'mixed')),
    entry_count INTEGER DEFAULT 1,
    
    gratitude_count INTEGER DEFAULT 0,
    challenge_count INTEGER DEFAULT 0,
    goal_mentions INTEGER DEFAULT 0,
    
    UNIQUE(user_id, date),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create performance indexes
CREATE INDEX IF NOT EXISTS idx_content_classifications_user_category ON content_classifications(user_id, primary_category);
CREATE INDEX IF NOT EXISTS idx_content_classifications_timestamp ON content_classifications(processing_timestamp);

CREATE INDEX IF NOT EXISTS idx_journal_entries_user_date ON journal_entries(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_journal_entries_mood ON journal_entries(user_id, mood_score);

CREATE INDEX IF NOT EXISTS idx_memories_user_type ON memories(user_id, memory_type);  
CREATE INDEX IF NOT EXISTS idx_memories_user_importance ON memories(user_id, importance_score);
CREATE INDEX IF NOT EXISTS idx_memories_user_date ON memories(user_id, created_at);

CREATE INDEX IF NOT EXISTS idx_daily_mood_user_date ON daily_mood_tracking(user_id, date);

-- Create timestamp update function if it doesn't exist
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for automatic timestamp updates
DROP TRIGGER IF EXISTS update_journal_entries_updated_at ON journal_entries;
CREATE TRIGGER update_journal_entries_updated_at BEFORE UPDATE ON journal_entries FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_memories_updated_at ON memories;
CREATE TRIGGER update_memories_updated_at BEFORE UPDATE ON memories FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_content_classifications_updated_at ON content_classifications;
CREATE TRIGGER update_content_classifications_updated_at BEFORE UPDATE ON content_classifications FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_daily_mood_tracking_updated_at ON daily_mood_tracking;
CREATE TRIGGER update_daily_mood_tracking_updated_at BEFORE UPDATE ON daily_mood_tracking FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();