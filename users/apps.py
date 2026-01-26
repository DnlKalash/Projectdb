from django.apps import AppConfig
from django.db import connection

class UsersConfig(AppConfig):
    name = 'users'

    def ready(self):
        with connection.cursor() as cursor:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(150) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
