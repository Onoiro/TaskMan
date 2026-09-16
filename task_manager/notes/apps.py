from django.apps import AppConfig


class NotesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'task_manager.notes'

    def ready(self):
        from task_manager.notes import signals  # noqa: F401
