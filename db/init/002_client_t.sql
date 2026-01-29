CREATE TABLE IF NOT EXISTS profile (
    id SERIAL PRIMARY KEY,

    user_id INT UNIQUE NOT NULL
        REFERENCES users(id)
        ON DELETE CASCADE,

    avatar_url TEXT NOT NULL DEFAULT '',
    bio TEXT NOT NULL DEFAULT '',

    reputation INT NOT NULL DEFAULT 0,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

   
    CHECK (reputation >= 0),
    CHECK (char_length(bio) <= 500)
);

