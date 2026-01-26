from django.apps import AppConfig
from django.db import connection

class ClientConfig(AppConfig):
    name = 'client'

    def ready(self):
        with connection.cursor() as cursor:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS profile (
                id SERIAL PRIMARY KEY,
                user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                avatar_url VARCHAR(255),
                bio TEXT,
                reputation INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
