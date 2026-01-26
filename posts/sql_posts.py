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
# Table init
# =========================
def create_posts_table():
    with connection.cursor() as cursor:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            content TEXT NOT NULL,
            author_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    print("✔ posts table ready")

def posts_table_exists():
    with connection.cursor() as cursor:
        cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'posts'
        )
        """)
        return cursor.fetchone()[0]

def init_posts_table():
    if not posts_table_exists():
        create_posts_table()
    else:
        print("✔ posts table already exists")

# =========================
# CREATE
# =========================
def create_post(title, content, author_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO posts (title, content, author_id, created_at)
            VALUES (%s, %s, %s, NOW())
            RETURNING id
        """, (title, content, author_id))
        return cursor.fetchone()[0]

# =========================
# READ
# =========================
def get_post_by_id(post_id):
    with connection.cursor() as cursor:
        cursor.execute("""
        SELECT id, title, content, author_id, created_at
        FROM posts
        WHERE id = %s
        """, (post_id,))
        return dict_fetchone(cursor)

def get_all_posts(limit=50, offset=0):
    with connection.cursor() as cursor:
        cursor.execute("""
        SELECT id, title, content, author_id, created_at
        FROM posts
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
        """, (limit, offset))
        return dict_fetchall(cursor)

def get_posts_by_author(author_id):
    with connection.cursor() as cursor:
        cursor.execute("""
        SELECT id, title, content, author_id, created_at
        FROM posts
        WHERE author_id = %s
        ORDER BY created_at DESC
        """, (author_id,))
        return dict_fetchall(cursor)

# =========================
# UPDATE
# =========================
def update_post(post_id, title=None, content=None):
    fields = []
    values = []

    if title is not None:
        fields.append("title = %s")
        values.append(title)

    if content is not None:
        fields.append("content = %s")
        values.append(content)

    if not fields:
        return None

    query = f"""
        UPDATE posts
        SET {', '.join(fields)}
        WHERE id = %s
        RETURNING id, title, content, author_id, created_at
    """
    values.append(post_id)

    with connection.cursor() as cursor:
        cursor.execute(query, values)
        return dict_fetchone(cursor)

# =========================
# DELETE
# =========================
def delete_post(post_id):
    with connection.cursor() as cursor:
        cursor.execute("""
        DELETE FROM posts
        WHERE id = %s
        RETURNING id
        """, (post_id,))
        return cursor.fetchone()

def delete_posts_by_author(author_id):
    with connection.cursor() as cursor:
        cursor.execute("""
        DELETE FROM posts
        WHERE author_id = %s
        RETURNING id
        """, (author_id,))
        return cursor.fetchall()

# =========================
# EXTRA (полезно)
# =========================
def count_posts():
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM posts")
        return cursor.fetchone()[0]

def search_posts(query_text):
    with connection.cursor() as cursor:
        cursor.execute("""
        SELECT id, title, content, author_id, created_at
        FROM posts
        WHERE title ILIKE %s OR content ILIKE %s
        ORDER BY created_at DESC
        """, (f"%{query_text}%", f"%{query_text}%"))
        return dict_fetchall(cursor)
