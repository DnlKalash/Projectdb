CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,

    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,

    author_id INTEGER NOT NULL
        REFERENCES users(id)
        ON DELETE CASCADE,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- CHECK constraints
    CHECK (char_length(title) >= 1),
    CHECK (char_length(content) >= 10)
);
