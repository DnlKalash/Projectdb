CREATE TABLE IF NOT EXISTS reactions (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reactable_type VARCHAR(20) NOT NULL CHECK (reactable_type IN ('post', 'comment')),
    reactable_id INT NOT NULL CHECK (reactable_id > 0),
    reaction_type VARCHAR(20) NOT NULL CHECK (reaction_type IN ('like', 'love', 'dislike')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, reactable_type, reactable_id)
);
