ALTER TABLE chat_settings
ADD COLUMN IF NOT EXISTS babel_probability_percent INTEGER NOT NULL DEFAULT 20;

ALTER TABLE chat_settings
ADD CONSTRAINT chat_settings_babel_probability_check
CHECK (babel_probability_percent BETWEEN 0 AND 100);
