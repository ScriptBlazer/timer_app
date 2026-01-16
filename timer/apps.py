from django.apps import AppConfig


class TimerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'timer'
    
    def ready(self):
        """Import signal handlers when app is ready"""
        import timer.signals  # noqa