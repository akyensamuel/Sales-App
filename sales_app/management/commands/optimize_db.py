"""
Django management command for database optimization and maintenance
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.core.cache import cache
from django.utils import timezone
from datetime import datetime, timedelta
from sales_app.models import Invoice, Product, Sale, AdminLog
from sales_app.cache_utils import SalesCache


class Command(BaseCommand):
    help = 'Perform database optimization and maintenance tasks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--analyze',
            action='store_true',
            help='Analyze database performance',
        )
        parser.add_argument(
            '--vacuum',
            action='store_true',
            help='Vacuum SQLite database (SQLite only)',
        )
        parser.add_argument(
            '--clear-cache',
            action='store_true',
            help='Clear all cached data',
        )
        parser.add_argument(
            '--cleanup-logs',
            type=int,
            default=90,
            help='Delete admin logs older than specified days (default: 90)',
        )
        parser.add_argument(
            '--warmup-cache',
            action='store_true',
            help='Pre-populate cache with commonly used data',
        )

    def handle(self, *args, **options):
        """Main command handler"""
        self.stdout.write(self.style.SUCCESS('Starting database optimization...'))

        if options['analyze']:
            self.analyze_database()

        if options['vacuum']:
            self.vacuum_database()

        if options['clear_cache']:
            self.clear_cache()

        if options['cleanup_logs']:
            self.cleanup_old_logs(options['cleanup_logs'])

        if options['warmup_cache']:
            self.warmup_cache()

        self.stdout.write(self.style.SUCCESS('Database optimization completed!'))

    def analyze_database(self):
        """Analyze database and provide performance insights"""
        self.stdout.write('Analyzing database performance...')
        
        with connection.cursor() as cursor:
            # Get database size info (SQLite specific)
            if 'sqlite' in connection.settings_dict['ENGINE']:
                cursor.execute("PRAGMA page_count;")
                page_count = cursor.fetchone()[0]
                cursor.execute("PRAGMA page_size;")
                page_size = cursor.fetchone()[0]
                db_size_mb = (page_count * page_size) / 1024 / 1024
                
                self.stdout.write(f'Database size: {db_size_mb:.2f} MB')
                
                # Analyze table statistics
                tables = ['sales_app_invoice', 'sales_app_product', 'sales_app_sale', 'sales_app_adminlog']
                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table};")
                        count = cursor.fetchone()[0]
                        self.stdout.write(f'{table}: {count:,} records')
                    except Exception as e:
                        self.stdout.write(f'Error analyzing {table}: {e}')

        # Application-level statistics
        self.stdout.write('\nApplication Statistics:')
        self.stdout.write(f'Total Invoices: {Invoice.objects.count():,}')
        self.stdout.write(f'Total Products: {Product.objects.count():,}')
        self.stdout.write(f'Total Sales Items: {Sale.objects.count():,}')
        self.stdout.write(f'Admin Log Entries: {AdminLog.objects.count():,}')
        
        # Find potential issues
        self.stdout.write('\nPotential Issues:')
        
        # Check for products with no stock
        no_stock = Product.objects.filter(stock=0).count()
        if no_stock > 0:
            self.stdout.write(f'⚠️  {no_stock} products have zero stock')
            
        # Check for invoices with no items
        empty_invoices = Invoice.objects.filter(items__isnull=True).count()
        if empty_invoices > 0:
            self.stdout.write(f'⚠️  {empty_invoices} invoices have no line items')
            
        # Check for old unpaid invoices
        old_unpaid = Invoice.objects.filter(
            payment_status='unpaid',
            date_of_sale__lt=timezone.now().date() - timedelta(days=30)
        ).count()
        if old_unpaid > 0:
            self.stdout.write(f'⚠️  {old_unpaid} invoices are unpaid and older than 30 days')

    def vacuum_database(self):
        """Vacuum SQLite database to reclaim space"""
        self.stdout.write('Vacuuming database...')
        
        if 'sqlite' in connection.settings_dict['ENGINE']:
            with connection.cursor() as cursor:
                cursor.execute("VACUUM;")
                self.stdout.write(self.style.SUCCESS('Database vacuumed successfully'))
        else:
            self.stdout.write(self.style.WARNING('VACUUM is SQLite-specific, skipping'))

    def clear_cache(self):
        """Clear all cached data"""
        self.stdout.write('Clearing cache...')
        cache.clear()
        self.stdout.write(self.style.SUCCESS('Cache cleared successfully'))

    def cleanup_old_logs(self, days):
        """Clean up old admin log entries"""
        self.stdout.write(f'Cleaning up admin logs older than {days} days...')
        
        cutoff_date = timezone.now() - timedelta(days=days)
        deleted_count = AdminLog.objects.filter(timestamp__lt=cutoff_date).count()
        
        if deleted_count > 0:
            AdminLog.objects.filter(timestamp__lt=cutoff_date).delete()
            self.stdout.write(self.style.SUCCESS(f'Deleted {deleted_count:,} old admin log entries'))
        else:
            self.stdout.write('No old admin logs to clean up')

    def warmup_cache(self):
        """Pre-populate cache with commonly used data"""
        self.stdout.write('Warming up cache...')
        
        today = timezone.now().date()
        
        # Pre-cache today's sales summary
        SalesCache.get_daily_sales_summary(today)
        self.stdout.write('✓ Cached today\'s sales summary')
        
        # Pre-cache low stock products
        SalesCache.get_low_stock_products(50)
        SalesCache.get_low_stock_products(25)
        SalesCache.get_low_stock_products(10)
        self.stdout.write('✓ Cached low stock products')
        
        # Pre-cache top products
        SalesCache.get_top_products(days=7, limit=10)
        SalesCache.get_top_products(days=30, limit=10)
        self.stdout.write('✓ Cached top products')
        
        # Pre-cache monthly summary
        SalesCache.get_monthly_summary()
        self.stdout.write('✓ Cached monthly summary')
        
        self.stdout.write(self.style.SUCCESS('Cache warmup completed'))

    def optimize_database_indexes(self):
        """Create additional indexes for better performance"""
        self.stdout.write('Optimizing database indexes...')
        
        with connection.cursor() as cursor:
            if 'sqlite' in connection.settings_dict['ENGINE']:
                # Additional indexes that might help
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_invoice_date_status ON sales_app_invoice(date_of_sale, payment_status);",
                    "CREATE INDEX IF NOT EXISTS idx_sale_item_invoice ON sales_app_sale(item, invoice_id);",
                    "CREATE INDEX IF NOT EXISTS idx_product_stock ON sales_app_product(stock);",
                    "CREATE INDEX IF NOT EXISTS idx_adminlog_timestamp ON sales_app_adminlog(timestamp);",
                ]
                
                for index_sql in indexes:
                    try:
                        cursor.execute(index_sql)
                        self.stdout.write(f'✓ Created index')
                    except Exception as e:
                        self.stdout.write(f'Index creation skipped: {e}')
                        
        self.stdout.write(self.style.SUCCESS('Database index optimization completed'))
