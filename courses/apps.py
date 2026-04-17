from django.apps import AppConfig


class CoursesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'courses'

    def ready(self):
        import notifications.signals  # noqa: F401
        import courses.signals  # noqa: F401
