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
    return [
        {desc[i].name: row[i] for i in range(len(row))}
        for row in rows
    ]

# =========================
# Init reactions table + SQL logic
# =========================

def init_reactions_table():
    with connection.cursor() as cursor:
        # -------------------------
        # REACTIONS TABLE
        # -------------------------
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reactions (
            id SERIAL PRIMARY KEY,
            user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            reactable_type VARCHAR(20) NOT NULL CHECK (reactable_type IN ('post', 'comment')),
            reactable_id INT NOT NULL,
            reaction_type VARCHAR(20) NOT NULL CHECK (reaction_type IN ('like', 'love', 'dislike')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, reactable_type, reactable_id)
        )
        """)

        # Индексы для быстрого поиска
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_reactions_post 
        ON reactions(reactable_type, reactable_id) 
        WHERE reactable_type = 'post'
        """)
        
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_reactions_comment 
        ON reactions(reactable_type, reactable_id) 
        WHERE reactable_type = 'comment'
        """)

        # =========================
        # ADD OR UPDATE REACTION
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS add_or_update_reaction_func(INT, VARCHAR, INT, VARCHAR)")
        cursor.execute("""
        CREATE FUNCTION add_or_update_reaction_func(
            p_user_id INT,
            p_reactable_type VARCHAR,
            p_reactable_id INT,
            p_reaction_type VARCHAR
        )
        RETURNS TABLE(r_id INT, r_user_id INT, r_reactable_type VARCHAR, r_reactable_id INT, r_reaction_type VARCHAR) AS $$
        BEGIN
            RETURN QUERY
            INSERT INTO reactions(user_id, reactable_type, reactable_id, reaction_type, created_at)
            VALUES (p_user_id, p_reactable_type, p_reactable_id, p_reaction_type, NOW())
            ON CONFLICT (user_id, reactable_type, reactable_id) 
            DO UPDATE SET reaction_type = EXCLUDED.reaction_type, created_at = NOW()
            RETURNING reactions.id, reactions.user_id, reactions.reactable_type, reactions.reactable_id, reactions.reaction_type;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # REMOVE REACTION
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS remove_reaction_func(INT, VARCHAR, INT)")
        cursor.execute("""
        CREATE FUNCTION remove_reaction_func(
            p_user_id INT,
            p_reactable_type VARCHAR,
            p_reactable_id INT
        )
        RETURNS BOOLEAN AS $$
        DECLARE
            deleted BOOLEAN := FALSE;
        BEGIN
            DELETE FROM reactions 
            WHERE user_id = p_user_id 
              AND reactable_type = p_reactable_type 
              AND reactable_id = p_reactable_id;
            
            IF FOUND THEN
                deleted := TRUE;
            END IF;
            
            RETURN deleted;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # GET REACTIONS STATS FOR POST
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS get_post_reactions_stats_func(INT)")
        cursor.execute("""
        CREATE FUNCTION get_post_reactions_stats_func(p_post_id INT)
        RETURNS TABLE(reaction_type VARCHAR, count BIGINT) AS $$
        BEGIN
            RETURN QUERY
            SELECT r.reaction_type, COUNT(*) as count
            FROM reactions r
            WHERE r.reactable_type = 'post' AND r.reactable_id = p_post_id
            GROUP BY r.reaction_type;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # GET REACTIONS STATS FOR COMMENT
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS get_comment_reactions_stats_func(INT)")
        cursor.execute("""
        CREATE FUNCTION get_comment_reactions_stats_func(p_comment_id INT)
        RETURNS TABLE(reaction_type VARCHAR, count BIGINT) AS $$
        BEGIN
            RETURN QUERY
            SELECT r.reaction_type, COUNT(*) as count
            FROM reactions r
            WHERE r.reactable_type = 'comment' AND r.reactable_id = p_comment_id
            GROUP BY r.reaction_type;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # GET USER REACTION ON POST
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS get_user_reaction_on_post_func(INT, INT)")
        cursor.execute("""
        CREATE FUNCTION get_user_reaction_on_post_func(p_user_id INT, p_post_id INT)
        RETURNS VARCHAR AS $$
        DECLARE
            reaction VARCHAR;
        BEGIN
            SELECT reaction_type INTO reaction
            FROM reactions
            WHERE user_id = p_user_id 
              AND reactable_type = 'post' 
              AND reactable_id = p_post_id;
            
            RETURN reaction;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # GET USER REACTION ON COMMENT
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS get_user_reaction_on_comment_func(INT, INT)")
        cursor.execute("""
        CREATE FUNCTION get_user_reaction_on_comment_func(p_user_id INT, p_comment_id INT)
        RETURNS VARCHAR AS $$
        DECLARE
            reaction VARCHAR;
        BEGIN
            SELECT reaction_type INTO reaction
            FROM reactions
            WHERE user_id = p_user_id 
              AND reactable_type = 'comment' 
              AND reactable_id = p_comment_id;
            
            RETURN reaction;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # GET POSTS WITH REACTIONS
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS get_posts_with_reactions_func()")
        cursor.execute("""
        CREATE FUNCTION get_posts_with_reactions_func()
        RETURNS TABLE(
            id INT,
            title VARCHAR,
            content TEXT,
            author_id INT,
            created_at TIMESTAMP,
            likes_count BIGINT,
            loves_count BIGINT,
            dislikes_count BIGINT
        ) AS $$
        BEGIN
            RETURN QUERY
            SELECT 
                p.id,
                p.title,
                p.content,
                p.author_id,
                p.created_at,
                COUNT(CASE WHEN r.reaction_type = 'like' THEN 1 END) as likes_count,
                COUNT(CASE WHEN r.reaction_type = 'love' THEN 1 END) as loves_count,
                COUNT(CASE WHEN r.reaction_type = 'dislike' THEN 1 END) as dislikes_count
            FROM posts p
            LEFT JOIN reactions r ON r.reactable_type = 'post' AND r.reactable_id = p.id
            GROUP BY p.id, p.title, p.content, p.author_id, p.created_at
            ORDER BY p.created_at DESC;
        END;
        $$ LANGUAGE plpgsql;
        """)

    print("✔ reactions table + SQL functions initialized")

# =========================
# Python wrappers
# =========================

def add_or_update_reaction(user_id, reactable_type, reactable_id, reaction_type):
    """Добавить или обновить реакцию"""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM add_or_update_reaction_func(%s, %s, %s, %s)",
            (user_id, reactable_type, reactable_id, reaction_type)
        )
        return dict_fetchone(cursor)


def remove_reaction(user_id, reactable_type, reactable_id):
    """Удалить реакцию"""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT remove_reaction_func(%s, %s, %s)",
            (user_id, reactable_type, reactable_id)
        )
        return cursor.fetchone()[0]


def get_post_reactions_stats(post_id):
    """Получить статистику реакций для поста"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_post_reactions_stats_func(%s)", (post_id,))
        return dict_fetchall(cursor)


def get_comment_reactions_stats(comment_id):
    """Получить статистику реакций для комментария"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_comment_reactions_stats_func(%s)", (comment_id,))
        return dict_fetchall(cursor)


def get_user_reaction_on_post(user_id, post_id):
    """Получить реакцию пользователя на пост"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT get_user_reaction_on_post_func(%s, %s)", (user_id, post_id))
        result = cursor.fetchone()
        return result[0] if result else None


def get_user_reaction_on_comment(user_id, comment_id):
    """Получить реакцию пользователя на комментарий"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT get_user_reaction_on_comment_func(%s, %s)", (user_id, comment_id))
        result = cursor.fetchone()
        return result[0] if result else None


def get_posts_with_reactions():
    """Получить все посты с количеством реакций"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_posts_with_reactions_func()")
        return dict_fetchall(cursor)