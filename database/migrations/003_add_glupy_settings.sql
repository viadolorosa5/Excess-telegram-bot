ALTER TABLE chat_settings
    ADD COLUMN IF NOT EXISTS glupy_probability_percent INTEGER NOT NULL DEFAULT 3;

ALTER TABLE chat_settings
    ADD COLUMN IF NOT EXISTS glupy_enabled BOOLEAN NOT NULL DEFAULT TRUE;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chat_settings_glupy_probability_check'
    ) THEN
        ALTER TABLE chat_settings
            ADD CONSTRAINT chat_settings_glupy_probability_check
            CHECK (glupy_probability_percent BETWEEN 0 AND 100);
    END IF;
END $$;

ALTER TABLE chat_settings
    ADD COLUMN IF NOT EXISTS glupy_order INTEGER NOT NULL DEFAULT 1;

ALTER TABLE chat_settings
    ADD COLUMN IF NOT EXISTS glupy_cooldown_minutes INTEGER NOT NULL DEFAULT 10;

ALTER TABLE chat_settings
    ADD COLUMN IF NOT EXISTS glupy_max_length INTEGER NOT NULL DEFAULT 200;

ALTER TABLE chat_activity
    ADD COLUMN IF NOT EXISTS glupy_last_sent_at TIMESTAMPTZ;
