INSERT INTO chat_activity (chat_id, last_message_at, last_message_id)
SELECT
    chat_id,
    MAX(sent_at) AS last_message_at,
    (ARRAY_AGG(id ORDER BY sent_at DESC))[1] AS last_message_id
FROM messages
GROUP BY chat_id
ON CONFLICT (chat_id) DO UPDATE
SET
    last_message_at = EXCLUDED.last_message_at,
    last_message_id = EXCLUDED.last_message_id;

INSERT INTO chat_settings (chat_id, silence_enabled)
SELECT id, TRUE
FROM chats
ON CONFLICT (chat_id) DO NOTHING;
