from django.db import connection

# =========================
# Utils
# =========================
def dict_fetchone(cursor):
    row = cursor.fetchone()
    if row is None:
        return None
    desc = cursor.description
    return {desc[i].name: row[i] for i in range(len(row))}

def dict_fetchall(cursor):
    rows = cursor.fetchall()
    desc = cursor.description
    return [{desc[i].name: row[i] for i in range(len(row))} for row in rows]

# =========================
# Profile table + SQL functions
# =========================
def create_profile_table_and_functions():
    with connection.cursor() as cursor:
        cursor.execute("""
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

            -- CHECK constraints
            CHECK (char_length(bio) <= 500)
        );

                """)

        # =========================
        # Триггер для обновления updated_at
        # =========================
        cursor.execute("""
        CREATE OR REPLACE FUNCTION update_profile_timestamp()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """)
        cursor.execute("DROP TRIGGER IF EXISTS trg_update_profile ON profile")
        cursor.execute("""
        CREATE TRIGGER trg_update_profile
        BEFORE UPDATE ON profile
        FOR EACH ROW
        EXECUTE FUNCTION update_profile_timestamp();
        """)

        # =========================
        # CREATE profile
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS create_profile_func(INT, TEXT, TEXT)")
        cursor.execute("""
        CREATE FUNCTION create_profile_func(
            p_user_id INT, p_avatar_url TEXT DEFAULT '', p_bio TEXT DEFAULT ''
        ) RETURNS TABLE(
            profile_id INT, profile_user_id INT, avatar_url TEXT, bio TEXT, reputation INT, created_at TIMESTAMP, updated_at TIMESTAMP
        ) AS $$
        BEGIN
            RETURN QUERY
            INSERT INTO profile(user_id, avatar_url, bio)
            VALUES(p_user_id, p_avatar_url, p_bio)
            RETURNING profile.id AS profile_id, profile.user_id AS profile_user_id, profile.avatar_url, profile.bio, profile.reputation, profile.created_at, profile.updated_at;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # READ profile
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS get_profile_func(INT)")
        cursor.execute("""
        CREATE FUNCTION get_profile_func(p_user_id INT)
        RETURNS TABLE(
            profile_id INT, profile_user_id INT, avatar_url TEXT, bio TEXT, reputation INT, created_at TIMESTAMP, updated_at TIMESTAMP
        ) AS $$
        BEGIN
            RETURN QUERY
            SELECT
                profile.id AS profile_id,
                profile.user_id AS profile_user_id,
                profile.avatar_url,
                profile.bio,
                profile.reputation,
                profile.created_at,
                profile.updated_at
            FROM profile
            WHERE profile.user_id = p_user_id;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # UPDATE profile
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS update_profile_func(INT, TEXT, TEXT, INT)")
        cursor.execute("""
        CREATE FUNCTION update_profile_func(
            p_user_id INT, p_avatar_url TEXT DEFAULT NULL, p_bio TEXT DEFAULT NULL, p_reputation INT DEFAULT NULL
        ) RETURNS TABLE(
            profile_id INT, profile_user_id INT, avatar_url TEXT, bio TEXT, reputation INT, created_at TIMESTAMP, updated_at TIMESTAMP
        ) AS $$
        BEGIN
            RETURN QUERY
            UPDATE profile
            SET avatar_url = COALESCE(p_avatar_url, profile.avatar_url),
                bio = COALESCE(p_bio, profile.bio),
                reputation = COALESCE(p_reputation, profile.reputation)
            WHERE user_id = p_user_id
            RETURNING
                profile.id AS profile_id,
                profile.user_id AS profile_user_id,
                profile.avatar_url,
                profile.bio,
                profile.reputation,
                profile.created_at,
                profile.updated_at;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # DELETE profile
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS delete_profile_func(INT)")
        cursor.execute("""
        CREATE FUNCTION delete_profile_func(p_user_id INT)
        RETURNS INT AS $$
        DECLARE del_id INT;
        BEGIN
            DELETE FROM profile WHERE user_id = p_user_id RETURNING id INTO del_id;
            RETURN del_id;
        END;
        $$ LANGUAGE plpgsql;
        """)

    print("✔ profile table and SQL functions ready")

# =========================
# Python wrappers
# =========================
def create_profile(user_id, avatar_url=None, bio=None):
    create_profile_table_and_functions()
    avatar_url = avatar_url or ''
    bio = bio or ''
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM create_profile_func(%s, %s, %s)", (user_id, avatar_url, bio))
        result = dict_fetchone(cursor)
    connection.commit()  
    return result

def get_profile(user_id):
    create_profile_table_and_functions()  
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_profile_func(%s)", (user_id,))
        return dict_fetchone(cursor)

def update_profile(user_id, avatar_url=None, bio=None):
    create_profile_table_and_functions()
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM update_profile_func(%s, %s, %s, %s)",
            (user_id, avatar_url, bio, None)  
        )
        result = dict_fetchone(cursor)
    connection.commit() 
    return result

def delete_profile(user_id):
    create_profile_table_and_functions()
    with connection.cursor() as cursor:
        cursor.execute("SELECT delete_profile_func(%s)", (user_id,))
        result = cursor.fetchone()[0]
    connection.commit()  
    return result