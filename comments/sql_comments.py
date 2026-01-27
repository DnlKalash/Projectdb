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
# Init comments table + SQL logic
# =========================

def init_comments_table():
    with connection.cursor() as cursor:
        # -------------------------
        # COMMENTS TABLE
        # -------------------------
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id SERIAL PRIMARY KEY,
            post_id INT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
            user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            content TEXT NOT NULL,
            parent_id INT REFERENCES comments(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # -------------------------
        # ADD COMMENT FUNCTION
        # -------------------------
        cursor.execute("DROP FUNCTION IF EXISTS add_comment_func(INT, INT, TEXT, INT)")
        cursor.execute("""
        CREATE FUNCTION add_comment_func(
            p_post_id INT,
            p_user_id INT,
            p_content TEXT,
            p_parent_id INT DEFAULT NULL
        )
        RETURNS TABLE(
            id INT, 
            post_id INT, 
            user_id INT, 
            content TEXT, 
            parent_id INT, 
            created_at TIMESTAMP
        ) AS $$
        BEGIN
            RETURN QUERY
            INSERT INTO comments(post_id, user_id, content, parent_id, created_at)
            VALUES (p_post_id, p_user_id, p_content, p_parent_id, NOW())
            RETURNING comments.id, comments.post_id, comments.user_id, comments.content, comments.parent_id, comments.created_at;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # -------------------------
        # GET ONE COMMENT
        # -------------------------
        cursor.execute("DROP FUNCTION IF EXISTS get_comment_func(INT)")
        cursor.execute("""
        CREATE FUNCTION get_comment_func(p_id INT)
        RETURNS TABLE(
            id INT, 
            post_id INT, 
            user_id INT, 
            content TEXT, 
            parent_id INT, 
            created_at TIMESTAMP
        ) AS $$
        BEGIN
            RETURN QUERY
            SELECT comments.id, comments.post_id, comments.user_id, comments.content, comments.parent_id, comments.created_at
            FROM comments
            WHERE comments.id = p_id;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # -------------------------
        # GET COMMENTS TREE
        # -------------------------
        cursor.execute("DROP FUNCTION IF EXISTS get_comments_tree_func(INT)")
        cursor.execute("""
        CREATE FUNCTION get_comments_tree_func(p_post_id INT)
        RETURNS TABLE(
            id INT,
            post_id INT,
            user_id INT,
            content TEXT,
            parent_id INT,
            created_at TIMESTAMP,
            level INT
        ) AS $$
        BEGIN
            RETURN QUERY
            WITH RECURSIVE comments_tree AS (
                SELECT
                    c.id,
                    c.post_id,
                    c.user_id,
                    c.content,
                    c.parent_id,
                    c.created_at,
                    0 AS level,
                    ARRAY[c.id] AS path
                FROM comments c
                WHERE c.post_id = p_post_id AND c.parent_id IS NULL

                UNION ALL

                SELECT
                    c.id,
                    c.post_id,
                    c.user_id,
                    c.content,
                    c.parent_id,
                    c.created_at,
                    ct.level + 1 AS level,
                    ct.path || c.id
                FROM comments c
                INNER JOIN comments_tree ct ON c.parent_id = ct.id
            )
            SELECT ct.id, ct.post_id, ct.user_id, ct.content, ct.parent_id, ct.created_at, ct.level
            FROM comments_tree ct
            ORDER BY ct.path;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # -------------------------
        # DELETE COMMENT
        # -------------------------
        cursor.execute("DROP FUNCTION IF EXISTS delete_comment_func(INT)")
        cursor.execute("""
        CREATE FUNCTION delete_comment_func(p_id INT)
        RETURNS INT AS $$
        DECLARE del_id INT;
        BEGIN
            DELETE FROM comments WHERE comments.id = p_id RETURNING comments.id INTO del_id;
            RETURN del_id;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # -------------------------
        # COUNT COMMENTS BY POST
        # -------------------------
        cursor.execute("DROP FUNCTION IF EXISTS count_comments_by_post_func(INT)")
        cursor.execute("""
        CREATE FUNCTION count_comments_by_post_func(p_post_id INT)
        RETURNS INT AS $$
        DECLARE total INT;
        BEGIN
            SELECT COUNT(*) INTO total FROM comments WHERE post_id = p_post_id;
            RETURN total;
        END;
        $$ LANGUAGE plpgsql;
        """)

    print("✔ comments table + SQL functions initialized")

# =========================
# Python wrappers
# =========================

def add_comment(post_id, user_id, content, parent_id=None):
    """Добавить комментарий к посту или ответ на комментарий"""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM add_comment_func(%s, %s, %s, %s)",
            (post_id, user_id, content, parent_id)
        )
        return dict_fetchone(cursor)


def get_comment(comment_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_comment_func(%s)", (comment_id,))
        return dict_fetchone(cursor)


def get_comments_tree(post_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_comments_tree_func(%s)", (post_id,))
        return dict_fetchall(cursor)


def delete_comment(comment_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT delete_comment_func(%s)", (comment_id,))
        return cursor.fetchone()[0]


def count_comments_by_post(post_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT count_comments_by_post_func(%s)", (post_id,))
        return cursor.fetchone()[0]
    
