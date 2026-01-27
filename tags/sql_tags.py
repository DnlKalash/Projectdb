from django.db import connection

# =========================
# Утилиты
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
# Таблицы Tags и Post_Tags + SQL функции
# =========================
def create_tags_tables():
    with connection.cursor() as cursor:
        # Таблица тегов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            )
        """)

        # Изменить тип колонки, если она уже существует как VARCHAR
        cursor.execute("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_name = 'tags' 
                      AND column_name = 'name' 
                      AND data_type != 'text'
                ) THEN
                    ALTER TABLE tags ALTER COLUMN name TYPE TEXT;
                END IF;
            END $$;
        """)

        # Таблица связи постов и тегов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS post_tags (
                post_id INT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                tag_id INT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                PRIMARY KEY (post_id, tag_id)
            )
        """)

        # =========================
        # CREATE tag
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS create_tag_func(TEXT)")
        cursor.execute("""
            CREATE FUNCTION create_tag_func(p_name TEXT)
            RETURNS TABLE(id INT, name TEXT) AS $$
            BEGIN
                RETURN QUERY
                INSERT INTO tags(name)
                VALUES(p_name)
                RETURNING tags.id, tags.name;
            END;
            $$ LANGUAGE plpgsql;
        """)

        # =========================
        # READ tag by id
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS get_tag_func(INT)")
        cursor.execute("""
            CREATE FUNCTION get_tag_func(p_id INT)
            RETURNS TABLE(id INT, name TEXT) AS $$
            BEGIN
                RETURN QUERY
                SELECT tags.id, tags.name 
                FROM tags 
                WHERE tags.id = p_id;
            END;
            $$ LANGUAGE plpgsql;
        """)

        # =========================
        # READ all tags
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS get_all_tags_func()")
        cursor.execute("""
            CREATE FUNCTION get_all_tags_func()
            RETURNS TABLE(id INT, name TEXT) AS $$
            BEGIN
                RETURN QUERY
                SELECT tags.id, tags.name 
                FROM tags 
                ORDER BY tags.name;
            END;
            $$ LANGUAGE plpgsql;
        """)

        # =========================
        # DELETE tag
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS delete_tag_func(INT)")
        cursor.execute("""
            CREATE FUNCTION delete_tag_func(p_id INT)
            RETURNS INT AS $$
            DECLARE del_id INT;
            BEGIN
                DELETE FROM tags 
                WHERE id = p_id 
                RETURNING id INTO del_id;
                RETURN del_id;
            END;
            $$ LANGUAGE plpgsql;
        """)

        # =========================
        # ATTACH tag to post
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS attach_tag_to_post(INT, TEXT)")
        cursor.execute("""
            CREATE FUNCTION attach_tag_to_post(p_post_id INT, p_tag_name TEXT)
            RETURNS TABLE (
                post_id INT,
                tag_id INT,
                tag_name TEXT
            ) AS $$
            DECLARE
                t_id INT;
            BEGIN
                -- ищем тег по имени
                SELECT tags.id INTO t_id FROM tags WHERE tags.name = p_tag_name;

                -- если тега нет, создаём его
                IF t_id IS NULL THEN
                    INSERT INTO tags(name) VALUES (p_tag_name) RETURNING tags.id INTO t_id;
                END IF;

                -- создаём связь пост <-> тег (если её ещё нет)
                INSERT INTO post_tags(post_id, tag_id)
                VALUES (p_post_id, t_id)
                ON CONFLICT DO NOTHING;

                -- возвращаем результат для проверки
                RETURN QUERY
                SELECT p_post_id AS post_id, t_id AS tag_id, p_tag_name AS tag_name;
            END;
            $$ LANGUAGE plpgsql;
        """)

    print("✔ tags and post_tags tables + SQL functions ready")


# =========================
# Python wrappers
# =========================
def create_tag(name):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM create_tag_func(%s)", (name,))
        return dict_fetchone(cursor)

def get_tag(tag_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_tag_func(%s)", (tag_id,))
        return dict_fetchone(cursor)

def get_all_tags():
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_all_tags_func()")
        return dict_fetchall(cursor)

def delete_tag(tag_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT delete_tag_func(%s)", (tag_id,))
        result = cursor.fetchone()
        return result[0] if result else None

def update_tag(tag_id, name):
    """
    Обновляет имя тега по его ID.
    """
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE tags
            SET name = %s
            WHERE id = %s
            RETURNING id, name
        """, (name, tag_id))
        return cursor.fetchone()

def attach_tag_to_post(post_id, tag_name):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM attach_tag_to_post(%s, %s)", (post_id, tag_name))
        return dict_fetchall(cursor)