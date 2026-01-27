from django.apps import AppConfig


class CommentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'comments'

    def ready(self):
        try:
            from . import sql_comments
            sql_comments.init_comments_table()
        except Exception as e:
            # Игнорируем ошибки если БД еще не готова
            print(f"⚠️ Could not initialize comments: {e}")