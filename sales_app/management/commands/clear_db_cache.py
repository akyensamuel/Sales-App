from django.core.management.base import BaseCommand
from django.db import connections


class Command(BaseCommand):
    help = 'Clear database connection cache to fix schema issues'

    def handle(self, *args, **options):
        self.stdout.write('🔄 Clearing database connection cache...')
        
        # Close all database connections
        for conn in connections.all():
            conn.close()
        
        # Clear introspection cache if available
        from django.db import connection
        if hasattr(connection, 'introspection'):
            if hasattr(connection.introspection, 'cache_clear'):
                connection.introspection.cache_clear()
        
        self.stdout.write(
            self.style.SUCCESS('✅ Database connection cache cleared successfully!')
        )
        self.stdout.write('🎉 Try accessing the manager dashboard now.')
