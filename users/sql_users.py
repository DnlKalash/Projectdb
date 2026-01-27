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
# Users table init + SQL functions
# =========================
def create_users_table():
    with connection.cursor() as cursor:
        # Таблица пользователей
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(150) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)


        # =========================
        # Регистрация нового пользователя с проверкой уникальности
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS register_user_func(VARCHAR, VARCHAR, VARCHAR)")
        cursor.execute("""
        CREATE FUNCTION register_user_func(
            p_username VARCHAR,
            p_email VARCHAR,
            p_password VARCHAR
        )
        RETURNS TABLE(user_id INT, username VARCHAR, email VARCHAR, created_at TIMESTAMP) AS $$
        BEGIN
            -- Проверка уникальности
            IF EXISTS(SELECT 1 FROM users u WHERE u.username = p_username OR u.email = p_email) THEN
                RAISE EXCEPTION 'Username or email already exists';
            END IF;

            -- Вставка нового пользователя
            RETURN QUERY
            INSERT INTO users AS u(username, email, password)
            VALUES (p_username, p_email, p_password)
            RETURNING u.id, u.username, u.email, u.created_at;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # Получение пользователя по username
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS get_user_by_username_func(VARCHAR)")
        cursor.execute("""
        CREATE FUNCTION get_user_by_username_func(p_username VARCHAR)
        RETURNS TABLE(user_id INT, username VARCHAR, password VARCHAR) AS $$
        BEGIN
            RETURN QUERY
            SELECT u.id, u.username, u.password
            FROM users u
            WHERE u.username = p_username;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # Получение пользователя по email
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS get_user_by_email_func(VARCHAR)")
        cursor.execute("""
        CREATE FUNCTION get_user_by_email_func(p_email VARCHAR)
        RETURNS TABLE(user_id INT, username VARCHAR, email VARCHAR, password VARCHAR) AS $$
        BEGIN
            RETURN QUERY
            SELECT u.id, u.username, u.email, u.password
            FROM users u
            WHERE u.email = p_email;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # Проверка существования пользователя по id
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS user_exists_func(INT)")
        cursor.execute("""
        CREATE FUNCTION user_exists_func(p_user_id INT)
        RETURNS BOOLEAN AS $$
        DECLARE exists_flag BOOLEAN;
        BEGIN
            SELECT EXISTS(SELECT 1 FROM users u WHERE u.id = p_user_id) INTO exists_flag;
            RETURN exists_flag;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # Подсчет всех пользователей
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS count_users_func()")
        cursor.execute("""
        CREATE FUNCTION count_users_func()
        RETURNS INT AS $$
        DECLARE total INT;
        BEGIN
            SELECT COUNT(*) INTO total FROM users;
            RETURN total;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # Обновление пользователя
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS update_user_func(INT, VARCHAR, VARCHAR, VARCHAR)")
        cursor.execute("""
        CREATE FUNCTION update_user_func(
            p_user_id INT,
            p_username VARCHAR DEFAULT NULL,
            p_email VARCHAR DEFAULT NULL,
            p_password VARCHAR DEFAULT NULL
        )
        RETURNS TABLE(user_id INT, username VARCHAR, email VARCHAR, password VARCHAR, created_at TIMESTAMP) AS $$
        BEGIN
            RETURN QUERY
            UPDATE users AS u
            SET
                username = COALESCE(p_username, u.username),
                email = COALESCE(p_email, u.email),
                password = COALESCE(p_password, u.password)
            WHERE u.id = p_user_id
            RETURNING u.id, u.username, u.email, u.password, u.created_at;
        END;
        $$ LANGUAGE plpgsql;
        """)

    print("✔ users table and SQL functions ready")


# =========================
# Python wrappers
# =========================
def register_user(username, email, password):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM register_user_func(%s, %s, %s)", (username, email, password))
        return dict_fetchone(cursor)

def get_user_by_username(username):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_user_by_username_func(%s)", (username,))
        return dict_fetchone(cursor)

def get_user_by_email(email):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_user_by_email_func(%s)", (email,))
        return dict_fetchone(cursor)

def user_exists(user_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT user_exists_func(%s)", (user_id,))
        return cursor.fetchone()[0]

def count_users():
    with connection.cursor() as cursor:
        cursor.execute("SELECT count_users_func()")
        return cursor.fetchone()[0]

def update_user(user_id, username=None, email=None, password=None):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM update_user_func(%s, %s, %s, %s)", (user_id, username, email, password))
        return dict_fetchone(cursor)
