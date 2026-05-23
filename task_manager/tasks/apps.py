from django.apps import AppConfig


class TasksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'task_manager.tasks'

    def ready(self):
        import task_manager.tasks.signals  # noqa: F401
