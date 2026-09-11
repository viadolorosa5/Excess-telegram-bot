ALTER TABLE messages
    ADD COLUMN IF NOT EXISTS media_file_id TEXT;
