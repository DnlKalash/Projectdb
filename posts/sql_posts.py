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
# Init tables + SQL logic
# =========================

def init_posts_table():
    with connection.cursor() as cursor:

        # -------------------------
        # POSTS
        # -------------------------
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            content TEXT NOT NULL,
            author_id INTEGER NOT NULL
                REFERENCES users(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # -------------------------
        # TAGS
        # -------------------------
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        )
        """)

        # Изменить тип колонки name на TEXT, если она VARCHAR
        cursor.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'tags' AND column_name = 'name' 
                AND data_type != 'text'
            ) THEN
                ALTER TABLE tags ALTER COLUMN name TYPE TEXT;
            END IF;
        END $$;
        """)
        class Migration(migrations.Migration):
            initial = True
            dependencies = [
        
                ('users', '0001_initial'),
             ]
            operations = [
                migrations.RunPython(init_tables),
                ]

        # -------------------------
        # POST_TAGS (M2M)
        # -------------------------
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS post_tags (
            post_id INT NOT NULL
                REFERENCES posts(id) ON DELETE CASCADE,
            tag_id INT NOT NULL
                REFERENCES tags(id) ON DELETE CASCADE,
            PRIMARY KEY (post_id, tag_id)
        )
        """)

        # -------------------------
        # DELETE LOG
        # -------------------------
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS deleted_posts_log (
            id SERIAL PRIMARY KEY,
            post_id INT,
            deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # -------------------------
        # DELETE TRIGGER
        # -------------------------
        cursor.execute("""
        CREATE OR REPLACE FUNCTION log_deleted_post()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO deleted_posts_log(post_id)
            VALUES (OLD.id);
            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql;
        """)

        cursor.execute("DROP TRIGGER IF EXISTS trg_delete_posts ON posts")
        cursor.execute("""
        CREATE TRIGGER trg_delete_posts
        AFTER DELETE ON posts
        FOR EACH ROW
        EXECUTE FUNCTION log_deleted_post();
        """)

        # =========================
        # CREATE POST WITH TAGS
        # =========================
        cursor.execute("""
        DROP FUNCTION IF EXISTS create_post_with_tags_func(
            VARCHAR, TEXT, INT, TEXT[]
        )
        """)

        cursor.execute("""
        CREATE FUNCTION create_post_with_tags_func(
            p_title VARCHAR,
            p_content TEXT,
            p_author_id INT,
            p_tags TEXT[]
        )
        RETURNS TABLE (
            id INT,
            title VARCHAR,
            content TEXT,
            author_id INT,
            created_at TIMESTAMP,
            tag_names TEXT[]
        ) AS $$
        DECLARE
            new_post_id INT;
            t_name TEXT;
            t_id INT;
        BEGIN
            -- create post
            INSERT INTO posts(title, content, author_id, created_at)
            VALUES (p_title, p_content, p_author_id, NOW())
            RETURNING posts.id INTO new_post_id;

            -- attach tags
            FOREACH t_name IN ARRAY p_tags LOOP
                SELECT tags.id INTO t_id FROM tags WHERE tags.name = t_name;

                IF t_id IS NULL THEN
                    INSERT INTO tags(name)
                    VALUES (t_name)
                    RETURNING tags.id INTO t_id;
                END IF;

                INSERT INTO post_tags(post_id, tag_id)
                VALUES (new_post_id, t_id)
                ON CONFLICT DO NOTHING;
            END LOOP;

            -- return created post with tags
            RETURN QUERY
            SELECT
                p.id,
                p.title,
                p.content,
                p.author_id,
                p.created_at,
                COALESCE(ARRAY_AGG(t.name ORDER BY t.name) FILTER (WHERE t.name IS NOT NULL), ARRAY[]::TEXT[])
            FROM posts p
            LEFT JOIN post_tags pt ON pt.post_id = p.id
            LEFT JOIN tags t ON t.id = pt.tag_id
            WHERE p.id = new_post_id
            GROUP BY p.id, p.title, p.content, p.author_id, p.created_at;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # GET POSTS BY TAG
        # =========================
        cursor.execute("""
        DROP FUNCTION IF EXISTS get_posts_by_tag_func(TEXT)
        """)

        cursor.execute("""
        CREATE FUNCTION get_posts_by_tag_func(p_tag_name TEXT)
        RETURNS TABLE (
            id INT,
            title VARCHAR,
            content TEXT,
            author_id INT,
            created_at TIMESTAMP,
            tag_names TEXT[]
        ) AS $$
        BEGIN
            RETURN QUERY
            SELECT
                p.id,
                p.title,
                p.content,
                p.author_id,
                p.created_at,
                COALESCE(ARRAY_AGG(t2.name ORDER BY t2.name) FILTER (WHERE t2.name IS NOT NULL), ARRAY[]::TEXT[])
            FROM posts p
            JOIN post_tags pt1 ON pt1.post_id = p.id
            JOIN tags t ON t.id = pt1.tag_id
            LEFT JOIN post_tags pt2 ON pt2.post_id = p.id
            LEFT JOIN tags t2 ON t2.id = pt2.tag_id
            WHERE t.name = p_tag_name
            GROUP BY p.id, p.title, p.content, p.author_id, p.created_at
            ORDER BY p.created_at DESC;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # GET ALL POSTS
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS get_all_posts_func(INT, INT)")
        cursor.execute("""
        CREATE FUNCTION get_all_posts_func(p_limit INT, p_offset INT)
        RETURNS TABLE(id INT, title VARCHAR, content TEXT, author_id INT, created_at TIMESTAMP) AS $$
        BEGIN
            RETURN QUERY
            SELECT posts.id, posts.title, posts.content, posts.author_id, posts.created_at
            FROM posts
            ORDER BY posts.created_at DESC
            LIMIT p_limit OFFSET p_offset;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # GET POST BY ID
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS get_post_by_id_func(INT)")
        cursor.execute("""
        CREATE FUNCTION get_post_by_id_func(p_id INT)
        RETURNS TABLE(id INT, title VARCHAR, content TEXT, author_id INT, created_at TIMESTAMP) AS $$
        BEGIN
            RETURN QUERY
            SELECT posts.id, posts.title, posts.content, posts.author_id, posts.created_at
            FROM posts
            WHERE posts.id = p_id;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # GET POST WITH TAGS
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS get_post_with_tags_func(INT)")
        cursor.execute("""
        CREATE FUNCTION get_post_with_tags_func(p_id INT)
        RETURNS TABLE(
            id INT, 
            title VARCHAR, 
            content TEXT, 
            author_id INT, 
            created_at TIMESTAMP,
            tag_names TEXT[]
        ) AS $$
        BEGIN
            RETURN QUERY
            SELECT
                p.id,
                p.title,
                p.content,
                p.author_id,
                p.created_at,
                COALESCE(ARRAY_AGG(t.name ORDER BY t.name) FILTER (WHERE t.name IS NOT NULL), ARRAY[]::TEXT[]) AS tag_names
            FROM posts p
            LEFT JOIN post_tags pt ON pt.post_id = p.id
            LEFT JOIN tags t ON t.id = pt.tag_id
            WHERE p.id = p_id
            GROUP BY p.id, p.title, p.content, p.author_id, p.created_at;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # GET POSTS BY AUTHOR
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS get_posts_by_author_func(INT, INT, INT)")
        cursor.execute("""
        CREATE FUNCTION get_posts_by_author_func(p_author_id INT, p_limit INT, p_offset INT)
        RETURNS TABLE(id INT, title VARCHAR, content TEXT, author_id INT, created_at TIMESTAMP) AS $$
        BEGIN
            RETURN QUERY
            SELECT posts.id, posts.title, posts.content, posts.author_id, posts.created_at
            FROM posts
            WHERE posts.author_id = p_author_id
            ORDER BY posts.created_at DESC
            LIMIT p_limit OFFSET p_offset;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # UPDATE POST
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS update_post_func(INT, VARCHAR, TEXT)")
        cursor.execute("""
        CREATE FUNCTION update_post_func(
            p_id INT, p_title VARCHAR DEFAULT NULL, p_content TEXT DEFAULT NULL
        ) RETURNS TABLE(id INT, title VARCHAR, content TEXT, author_id INT, created_at TIMESTAMP) AS $$
        BEGIN
            RETURN QUERY
            UPDATE posts
            SET title = COALESCE(p_title, posts.title),
                content = COALESCE(p_content, posts.content)
            WHERE posts.id = p_id
            RETURNING posts.id, posts.title, posts.content, posts.author_id, posts.created_at;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # DELETE POST
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS delete_post_func(INT)")
        cursor.execute("""
        CREATE FUNCTION delete_post_func(p_id INT)
        RETURNS INT AS $$
        DECLARE del_id INT;
        BEGIN
            DELETE FROM posts WHERE id = p_id RETURNING id INTO del_id;
            RETURN del_id;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # ADD TAG TO POST
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS add_tag_to_post_func(INT, TEXT)")
        cursor.execute("""
        CREATE FUNCTION add_tag_to_post_func(
            p_post_id INT,
            p_tag_name TEXT
        )
        RETURNS TABLE(tag_id INT, tag_name TEXT, success BOOLEAN) AS $$
        DECLARE
            v_tag_id INT;
            v_exists BOOLEAN;
        BEGIN
            -- Проверить, существует ли уже эта связь
            SELECT EXISTS(
                SELECT 1 FROM post_tags pt
                JOIN tags t ON t.id = pt.tag_id
                WHERE pt.post_id = p_post_id AND t.name = p_tag_name
            ) INTO v_exists;
            
            IF v_exists THEN
                -- Связь уже существует
                SELECT t.id INTO v_tag_id FROM tags t WHERE t.name = p_tag_name;
                RETURN QUERY SELECT v_tag_id, p_tag_name, FALSE;
                RETURN;
            END IF;
            
            -- Найти или создать тег
            SELECT tags.id INTO v_tag_id FROM tags WHERE tags.name = p_tag_name;
            
            IF v_tag_id IS NULL THEN
                INSERT INTO tags(name)
                VALUES (p_tag_name)
                RETURNING tags.id INTO v_tag_id;
            END IF;
            
            -- Привязать тег к посту
            INSERT INTO post_tags(post_id, tag_id)
            VALUES (p_post_id, v_tag_id)
            ON CONFLICT DO NOTHING;
            
            RETURN QUERY SELECT v_tag_id, p_tag_name, TRUE;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # REMOVE TAG FROM POST
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS remove_tag_from_post_func(INT, TEXT)")
        cursor.execute("""
        CREATE FUNCTION remove_tag_from_post_func(
            p_post_id INT,
            p_tag_name TEXT
        )
        RETURNS BOOLEAN AS $$
        DECLARE
            v_tag_id INT;
            v_deleted BOOLEAN := FALSE;
        BEGIN
            -- Найти ID тега
            SELECT tags.id INTO v_tag_id FROM tags WHERE tags.name = p_tag_name;
            
            IF v_tag_id IS NOT NULL THEN
                DELETE FROM post_tags 
                WHERE post_id = p_post_id AND tag_id = v_tag_id;
                
                IF FOUND THEN
                    v_deleted := TRUE;
                END IF;
            END IF;
            
            RETURN v_deleted;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # GET ALL TAGS
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS get_all_tags_func()")
        cursor.execute("""
        CREATE FUNCTION get_all_tags_func()
        RETURNS TABLE(id INT, name TEXT, post_count BIGINT) AS $$
        BEGIN
            RETURN QUERY
            SELECT 
                tags.id, 
                tags.name::TEXT,
                COUNT(post_tags.post_id) as post_count
            FROM tags
            LEFT JOIN post_tags ON post_tags.tag_id = tags.id
            GROUP BY tags.id, tags.name
            ORDER BY tags.name;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # COUNT POSTS
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS count_posts_func()")
        cursor.execute("""
        CREATE FUNCTION count_posts_func()
        RETURNS INT AS $$
        DECLARE total INT;
        BEGIN
            SELECT COUNT(*) INTO total FROM posts;
            RETURN total;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # COUNT POSTS BY AUTHOR
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS count_posts_by_author_func(INT)")
        cursor.execute("""
        CREATE FUNCTION count_posts_by_author_func(p_author_id INT)
        RETURNS INT AS $$
        DECLARE total INT;
        BEGIN
            SELECT COUNT(*) INTO total FROM posts WHERE author_id = p_author_id;
            RETURN total;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # SEARCH POSTS
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS search_posts_func(VARCHAR, INT, INT)")
        cursor.execute("""
        CREATE FUNCTION search_posts_func(p_query VARCHAR, p_limit INT, p_offset INT)
        RETURNS TABLE(id INT, title VARCHAR, content TEXT, author_id INT, created_at TIMESTAMP) AS $$
        BEGIN
            RETURN QUERY
            SELECT posts.id, posts.title, posts.content, posts.author_id, posts.created_at
            FROM posts
            WHERE posts.title ILIKE '%' || p_query || '%'
               OR posts.content ILIKE '%' || p_query || '%'
            ORDER BY posts.created_at DESC
            LIMIT p_limit OFFSET p_offset;
        END;
        $$ LANGUAGE plpgsql;
        """)

    print("✔ posts, tags, post_tags + SQL functions initialized")


# =========================
# Python wrappers
# =========================


def create_post_with_tags(title, content, author_id, tag_names):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM create_post_with_tags_func(%s, %s, %s, %s)",
            (title, content, author_id, tag_names)
        )
        return dict_fetchone(cursor)


def get_posts_by_tag(tag_name):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM get_posts_by_tag_func(%s)",
            (tag_name,)
        )
        return dict_fetchall(cursor)


def create_post(title, content, author_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM create_post_with_tags_func(%s, %s, %s, %s)", 
                      (title, content, author_id, []))
        return dict_fetchone(cursor)


def get_post_by_id(post_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_post_by_id_func(%s)", (post_id,))
        return dict_fetchone(cursor)


def get_all_posts(limit=50, offset=0):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_all_posts_func(%s, %s)", (limit, offset))
        return dict_fetchall(cursor)


def get_posts_by_author(author_id, limit=50, offset=0):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_posts_by_author_func(%s, %s, %s)", 
                      (author_id, limit, offset))
        return dict_fetchall(cursor)


def update_post(post_id, title=None, content=None):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM update_post_func(%s, %s, %s)", 
                      (post_id, title, content))
        return dict_fetchone(cursor)


def delete_post(post_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT delete_post_func(%s)", (post_id,))
        return cursor.fetchone()[0]


def add_tag_to_post(post_id, tag_name):
    """Добавить тег к посту (создается автоматически если не существует)"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM add_tag_to_post_func(%s, %s)", 
                      (post_id, tag_name.strip()))
        result = dict_fetchone(cursor)
        return result


def remove_tag_from_post(post_id, tag_name):
    """Удалить тег из поста"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT remove_tag_from_post_func(%s, %s)", 
                      (post_id, tag_name))
        return cursor.fetchone()[0]


def get_post_with_tags(post_id):
    """Получить пост со всеми тегами"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_post_with_tags_func(%s)", (post_id,))
        return dict_fetchone(cursor)


def get_all_tags():
    """Получить все теги с количеством постов"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_all_tags_func()")
        return dict_fetchall(cursor)


def count_posts():
    with connection.cursor() as cursor:
        cursor.execute("SELECT count_posts_func()")
        return cursor.fetchone()[0]


def count_posts_by_author(author_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT count_posts_by_author_func(%s)", (author_id,))
        return cursor.fetchone()[0]


def search_posts(query_text, limit=50, offset=0):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM search_posts_func(%s, %s, %s)", 
                      (query_text, limit, offset))
        return dict_fetchall(cursor)