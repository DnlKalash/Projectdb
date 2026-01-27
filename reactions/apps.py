from django.apps import AppConfig


class ReactionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reactions'

    def ready(self):
        """
        Автоматически создаёт таблицу reactions при старте
        """
        try:
            from . import sql_reactions
            sql_reactions.init_reactions_table()
        except Exception as e:
            print(f"⚠️ Could not initialize reactions: {e}")