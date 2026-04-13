-- Create user_sessions table
CREATE TABLE user_sessions (
  session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_phone_number VARCHAR(20) NOT NULL UNIQUE,
  session_state VARCHAR(50) NOT NULL DEFAULT 'main_menu',
  conversation_context JSONB DEFAULT '{}'::JSONB,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP,
  CONSTRAINT valid_session_state CHECK (session_state IN ('main_menu', 'qna_active', 'closed'))
);

-- Create index on phone number for fast lookup
CREATE INDEX idx_user_phone_number ON user_sessions(user_phone_number);
CREATE INDEX idx_session_state ON user_sessions(session_state);
CREATE INDEX idx_expires_at ON user_sessions(expires_at);

-- Create conversation_history table
CREATE TABLE conversation_history (
  history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL,
  turn_number INTEGER NOT NULL,
  user_query TEXT NOT NULL,
  user_query_reformulated TEXT,
  intent_detected VARCHAR(100),
  retrieved_scheme_names JSONB DEFAULT '[]'::JSONB,
  bot_answer TEXT NOT NULL,
  latency_ms INTEGER,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES user_sessions(session_id) ON DELETE CASCADE
);

-- Create indexes for conversation history
CREATE INDEX idx_conversation_session_id ON conversation_history(session_id);
CREATE INDEX idx_conversation_turn_number ON conversation_history(session_id, turn_number);
CREATE INDEX idx_conversation_timestamp ON conversation_history(timestamp);

-- Enable RLS (Row Level Security) for sessions table
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_history ENABLE ROW LEVEL SECURITY;

-- Create RLS policies (allow all for now, can be restricted later)
CREATE POLICY "Enable all access to user_sessions" ON user_sessions
  FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Enable all access to conversation_history" ON conversation_history
  FOR ALL USING (true) WITH CHECK (true);

-- Function to auto-expire sessions
CREATE OR REPLACE FUNCTION expire_old_sessions()
RETURNS void AS $$
BEGIN
  UPDATE user_sessions
  SET session_state = 'closed'
  WHERE session_state != 'closed'
    AND expires_at IS NOT NULL
    AND expires_at < CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to set expires_at on session creation (30 min from now)
CREATE OR REPLACE FUNCTION set_session_expiry()
RETURNS TRIGGER AS $$
BEGIN
  NEW.expires_at := CURRENT_TIMESTAMP + INTERVAL '30 minutes';
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_set_session_expiry
BEFORE INSERT ON user_sessions
FOR EACH ROW
EXECUTE FUNCTION set_session_expiry();

-- Update last_message_at on conversation history insert
CREATE OR REPLACE FUNCTION update_session_last_message()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE user_sessions
  SET last_message_at = CURRENT_TIMESTAMP,
      expires_at = CURRENT_TIMESTAMP + INTERVAL '30 minutes'
  WHERE session_id = NEW.session_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_session_last_message
AFTER INSERT ON conversation_history
FOR EACH ROW
EXECUTE FUNCTION update_session_last_message();
