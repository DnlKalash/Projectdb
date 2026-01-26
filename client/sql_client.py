from django.db import connection
from psycopg2 import errors

def dict_fetchone(cursor):
    row = cursor.fetchone()
    if row is None:
        return None
    desc = cursor.description
    return {desc[i].name: row[i] for i in range(len(row))}

def make_avatar_url_longer():
    """Меняет тип avatar_url на TEXT"""
    with connection.cursor() as cursor:
        cursor.execute("""
            ALTER TABLE profile
            ALTER COLUMN avatar_url TYPE TEXT;
        """)
    print("avatar_url теперь TEXT — можно хранить любые URL/base64.")

def create_profile(user_id, avatar_url=None, bio=None):
    avatar_url = avatar_url or ""
    bio = bio or ""
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO profile (user_id, avatar_url, bio)
            VALUES (%s, %s, %s)
            RETURNING id, user_id, avatar_url, bio, reputation, created_at, updated_at
        """, (user_id, avatar_url, bio))
        return dict_fetchone(cursor)

def get_profile(user_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, user_id, avatar_url, bio, reputation, created_at, updated_at
            FROM profile
            WHERE user_id = %s
        """, (user_id,))
        return dict_fetchone(cursor)

def update_profile(user_id, avatar_url=None, bio=None, reputation=None):
    fields = []
    values = []

    if avatar_url is not None:
        fields.append("avatar_url = %s")
        values.append(avatar_url)
    if bio is not None:
        fields.append("bio = %s")
        values.append(bio)
    if reputation is not None:
        fields.append("reputation = %s")
        values.append(reputation)

    if not fields:
        return None

    query = f"""
        UPDATE profile
        SET {', '.join(fields)}, updated_at = NOW()
        WHERE user_id = %s
        RETURNING id, user_id, avatar_url, bio, reputation, created_at, updated_at
    """
    values.append(user_id)

    try:
        with connection.cursor() as cursor:
            cursor.execute(query, values)
            return dict_fetchone(cursor)
    except Exception as e:
        # ловим ошибку длины для avatar_url
        if isinstance(e.__cause__, errors.StringDataRightTruncation) and avatar_url is not None:
            print("Слишком длинный avatar_url, расширяем колонку...")
            make_avatar_url_longer()
            # повторяем запрос после изменения колонки
            with connection.cursor() as cursor:
                cursor.execute(query, values)
                return dict_fetchone(cursor)
        else:
            # пробрасываем остальные ошибки
            raise

def delete_profile(user_id):
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM profile WHERE user_id = %s RETURNING id", [user_id])
        return cursor.fetchone()
