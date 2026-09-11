CREATE TABLE IF NOT EXISTS quotes (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL REFERENCES chats (id) ON DELETE CASCADE,
    message_id BIGINT NOT NULL UNIQUE REFERENCES messages (id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_quotes_chat_created_at
    ON quotes (chat_id, created_at DESC);
