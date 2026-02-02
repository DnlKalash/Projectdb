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

# =========================
# Posts View
# =========================
def create_posts_view():
    with connection.cursor() as cursor:
        cursor.execute("""
        DROP VIEW IF EXISTS posts_with_stats CASCADE;
        """)
        cursor.execute("""
        CREATE VIEW posts_with_stats AS
        SELECT 
            p.id,
            p.title,
            p.content,
            p.author_id,
            p.created_at,
            
            COUNT(DISTINCT c.id) AS comment_count,
            
            COUNT(DISTINCT pt.tag_id) AS tag_count,
            COALESCE(
                STRING_AGG(DISTINCT t.name, ', ' ORDER BY t.name), 
                'No tags'
            ) AS tag_list,
            
            COUNT(DISTINCT CASE WHEN r.reaction_type = 'like' THEN r.id END) AS likes_count,
            COUNT(DISTINCT CASE WHEN r.reaction_type = 'love' THEN r.id END) AS loves_count,
            COUNT(DISTINCT CASE WHEN r.reaction_type = 'dislike' THEN r.id END) AS dislikes_count,
            
            COUNT(DISTINCT r.id) AS total_reactions,
            
            (
                COUNT(DISTINCT CASE WHEN r.reaction_type = 'like' THEN r.id END) +
                2 * COUNT(DISTINCT CASE WHEN r.reaction_type = 'love' THEN r.id END) -
                COUNT(DISTINCT CASE WHEN r.reaction_type = 'dislike' THEN r.id END)
            ) AS engagement_score
        FROM posts p
        LEFT JOIN comments c ON c.post_id = p.id
        LEFT JOIN post_tags pt ON pt.post_id = p.id
        LEFT JOIN tags t ON t.id = pt.tag_id
        LEFT JOIN reactions r ON r.reactable_type = 'post' AND r.reactable_id = p.id
        GROUP BY p.id, p.title, p.content, p.author_id, p.created_at;
        """)
    connection.commit()
    print("✔ posts_with_stats view created")

# =========================
# posts_with_stats
# =========================
def get_posts_with_stats(limit=10, offset=0):
    create_posts_view()
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT * FROM posts_with_stats 
            ORDER BY created_at DESC 
            LIMIT %s OFFSET %s
        """, (limit, offset))
        return dict_fetchall(cursor)

def get_post_stats_by_id(post_id):

    create_posts_view()
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT * FROM posts_with_stats 
            WHERE id = %s
        """, (post_id,))
        return dict_fetchone(cursor)

def get_most_engaged_posts(limit=10):

    create_posts_view()
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT * FROM posts_with_stats 
            ORDER BY engagement_score DESC 
            LIMIT %s
        """, (limit,))
        return dict_fetchall(cursor)

def get_posts_by_tag_with_stats(tag_name, limit=10):

    create_posts_view()
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT * FROM posts_with_stats 
            WHERE tag_list LIKE %s
            ORDER BY created_at DESC 
            LIMIT %s
        """, (f'%{tag_name}%', limit))
        return dict_fetchall(cursor)
    
# =========================
# User Activity View
# =========================
def create_user_activity_view():
    with connection.cursor() as cursor:
        cursor.execute("""
        DROP VIEW IF EXISTS user_activity_summary CASCADE;
        """)
        cursor.execute("""
        CREATE VIEW user_activity_summary AS
        SELECT 
            u.id AS user_id,
            u.username,
            u.email,
            
            COALESCE(pr.reputation, 0) AS reputation,
            COALESCE(pr.bio, '') AS bio,
            COALESCE(pr.avatar_url, '') AS avatar_url,
            
            COUNT(DISTINCT p.id) AS posts_count,
            COUNT(DISTINCT c.id) AS comments_count,
            (COUNT(DISTINCT p.id) + COUNT(DISTINCT c.id)) AS total_contributions,
            
            COUNT(DISTINCT r.id) AS reactions_given,
            
            COUNT(DISTINCT rp.id) AS reactions_on_posts,
            
            COUNT(DISTINCT rc.id) AS reactions_on_comments,
            
            (COUNT(DISTINCT rp.id) + COUNT(DISTINCT rc.id)) AS total_reactions_received,
            
            COALESCE(pr.created_at, u.created_at) AS profile_created_at,
            GREATEST(
                MAX(p.created_at),
                MAX(c.created_at),
                MAX(r.created_at)
            ) AS last_activity_at
        FROM users u
        LEFT JOIN profile pr ON pr.user_id = u.id
        LEFT JOIN posts p ON p.author_id = u.id
        LEFT JOIN comments c ON c.user_id = u.id
        LEFT JOIN reactions r ON r.user_id = u.id
        LEFT JOIN reactions rp ON rp.reactable_type = 'post' 
            AND rp.reactable_id IN (SELECT id FROM posts WHERE author_id = u.id)
        LEFT JOIN reactions rc ON rc.reactable_type = 'comment' 
            AND rc.reactable_id IN (SELECT id FROM comments WHERE user_id = u.id)
        GROUP BY 
            u.id, 
            u.username, 
            u.email, 
            pr.reputation, 
            pr.bio, 
            pr.avatar_url, 
            pr.created_at, 
            u.created_at;
        """)
    connection.commit()
    print("✔ user_activity_summary view created")

# =========================
# user_activity_summary
# =========================
def get_user_activity(user_id):
    
    create_user_activity_view()
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT * FROM user_activity_summary 
            WHERE user_id = %s
        """, (user_id,))
        return dict_fetchone(cursor)

def get_top_users_by_reputation(limit=10):
    
    create_user_activity_view()
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT * FROM user_activity_summary 
            ORDER BY reputation DESC 
            LIMIT %s
        """, (limit,))
        return dict_fetchall(cursor)

def get_most_active_users(limit=10):
    
    create_user_activity_view()
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT * FROM user_activity_summary 
            ORDER BY total_contributions DESC 
            LIMIT %s
        """, (limit,))
        return dict_fetchall(cursor)

def get_all_users_activity():
    
    create_user_activity_view()
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT * FROM user_activity_summary 
            ORDER BY reputation DESC
        """)
        return dict_fetchall(cursor)