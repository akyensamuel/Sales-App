from django.apps import AppConfig


class SalesAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sales_app'
    
    def ready(self):
        """Import signal handlers when the app is ready"""
        import sales_app.signals
