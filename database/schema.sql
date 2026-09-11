CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chats (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    title TEXT,
    chat_type TEXT NOT NULL CHECK (
        chat_type IN ('private', 'group', 'supergroup', 'channel')
    ),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_settings (
    chat_id BIGINT PRIMARY KEY REFERENCES chats (id) ON DELETE CASCADE,
    silence_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    silence_threshold_minutes INTEGER NOT NULL DEFAULT 300 CHECK (
        silence_threshold_minutes > 0
    ),
    reminder_text TEXT NOT NULL DEFAULT 'Че молчите?',
    reminder_cooldown_minutes INTEGER NOT NULL DEFAULT 1440 CHECK (
        reminder_cooldown_minutes > 0
    ),
    babel_probability_percent INTEGER NOT NULL DEFAULT 20 CHECK (
        babel_probability_percent BETWEEN 0 AND 100
    ),
    glupy_probability_percent INTEGER NOT NULL DEFAULT 3 CHECK (
        glupy_probability_percent BETWEEN 0 AND 100
    ),
    glupy_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    glupy_order INTEGER NOT NULL DEFAULT 1 CHECK (glupy_order BETWEEN 1 AND 3),
    glupy_cooldown_minutes INTEGER NOT NULL DEFAULT 10 CHECK (glupy_cooldown_minutes >= 0),
    glupy_max_length INTEGER NOT NULL DEFAULT 200 CHECK (glupy_max_length BETWEEN 2 AND 4096),
    glupy_reply_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    timezone TEXT NOT NULL DEFAULT 'UTC',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_activity (
    chat_id BIGINT PRIMARY KEY REFERENCES chats (id) ON DELETE CASCADE,
    last_message_at TIMESTAMPTZ,
    last_reminder_at TIMESTAMPTZ,
    last_message_id BIGINT,
    glupy_last_sent_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS chat_members (
    chat_id BIGINT NOT NULL REFERENCES chats (id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'member' CHECK (
        role IN ('member', 'administrator', 'creator')
    ),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    joined_at TIMESTAMPTZ,
    left_at TIMESTAMPTZ,
    PRIMARY KEY (chat_id, user_id)
);

CREATE TABLE IF NOT EXISTS messages (
    id BIGSERIAL PRIMARY KEY,
    telegram_message_id BIGINT NOT NULL,
    chat_id BIGINT NOT NULL REFERENCES chats (id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES users (id) ON DELETE SET NULL,
    text TEXT,
    content_type TEXT NOT NULL DEFAULT 'text',
    emoji_count INTEGER NOT NULL DEFAULT 0,
    reaction_count INTEGER NOT NULL DEFAULT 0,
    media_file_id TEXT,
    sent_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (chat_id, telegram_message_id)
);

CREATE TABLE IF NOT EXISTS message_stats (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL REFERENCES chats (id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES users (id) ON DELETE SET NULL,
    period_date DATE NOT NULL,
    message_count INTEGER NOT NULL DEFAULT 0 CHECK (message_count >= 0),
    character_count BIGINT NOT NULL DEFAULT 0 CHECK (character_count >= 0),
    UNIQUE (chat_id, user_id, period_date)
);

CREATE TABLE IF NOT EXISTS quotes (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL REFERENCES chats (id) ON DELETE CASCADE,
    message_id BIGINT NOT NULL UNIQUE REFERENCES messages (id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_chat_sent_at
    ON messages (chat_id, sent_at DESC);

CREATE INDEX IF NOT EXISTS idx_messages_user_sent_at
    ON messages (user_id, sent_at DESC);

CREATE INDEX IF NOT EXISTS idx_message_stats_chat_period
    ON message_stats (chat_id, period_date DESC);

CREATE INDEX IF NOT EXISTS idx_chat_members_user
    ON chat_members (user_id);

CREATE INDEX IF NOT EXISTS idx_quotes_chat_created_at
    ON quotes (chat_id, created_at DESC);
