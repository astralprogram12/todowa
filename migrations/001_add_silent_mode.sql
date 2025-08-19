-- Migration: Add Silent Mode functionality
-- Date: 2025-08-19
-- Description: Creates silent_sessions table and adds silent mode fields to user_whatsapp table

-- Create silent_sessions table to track silent mode periods
CREATE TABLE IF NOT EXISTS silent_sessions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    start_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    end_time TIMESTAMPTZ,
    duration_minutes INTEGER NOT NULL,
    trigger_type VARCHAR(20) NOT NULL CHECK (trigger_type IN ('manual', 'auto', 'scheduled')),
    is_active BOOLEAN NOT NULL DEFAULT true,
    accumulated_actions JSONB DEFAULT '[]',
    action_count INTEGER DEFAULT 0,
    exit_reason VARCHAR(50) CHECK (exit_reason IN ('expired', 'manual_exit', 'error', 'system')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_silent_sessions_user_id ON silent_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_silent_sessions_active ON silent_sessions(user_id, is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_silent_sessions_start_time ON silent_sessions(start_time);

-- Add silent mode preferences to user_whatsapp table
ALTER TABLE user_whatsapp 
ADD COLUMN IF NOT EXISTS auto_silent_enabled BOOLEAN DEFAULT true,
ADD COLUMN IF NOT EXISTS auto_silent_start_hour INTEGER DEFAULT 7 CHECK (auto_silent_start_hour >= 0 AND auto_silent_start_hour <= 23),
ADD COLUMN IF NOT EXISTS auto_silent_end_hour INTEGER DEFAULT 11 CHECK (auto_silent_end_hour >= 0 AND auto_silent_end_hour <= 23),
ADD COLUMN IF NOT EXISTS last_silent_summary_sent TIMESTAMPTZ;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_silent_sessions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for updated_at
CREATE TRIGGER update_silent_sessions_updated_at
BEFORE UPDATE ON silent_sessions
FOR EACH ROW
EXECUTE PROCEDURE update_silent_sessions_updated_at();

-- Create function to automatically end expired silent sessions
CREATE OR REPLACE FUNCTION end_expired_silent_sessions()
RETURNS INTEGER AS $$
DECLARE
    ended_count INTEGER;
BEGIN
    UPDATE silent_sessions 
    SET 
        is_active = false,
        end_time = NOW(),
        exit_reason = 'expired',
        updated_at = NOW()
    WHERE 
        is_active = true 
        AND start_time + (duration_minutes || ' minutes')::INTERVAL < NOW();
    
    GET DIAGNOSTICS ended_count = ROW_COUNT;
    RETURN ended_count;
END;
$$ language 'plpgsql';

COMMENT ON TABLE silent_sessions IS 'Tracks silent mode periods for users';
COMMENT ON FUNCTION end_expired_silent_sessions() IS 'Automatically ends expired silent sessions, returns count of ended sessions';
