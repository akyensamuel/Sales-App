from django.core.management.base import BaseCommand
from django.db import connection
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Fix production database schema issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check-only',
            action='store_true',
            help='Only check for missing columns, do not apply fixes',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Checking production database schema...')
        )

        # Check if customer_phone column exists
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'sales_app_invoice' 
                AND column_name = 'customer_phone';
            """)
            customer_phone_exists = cursor.fetchone()

            if not customer_phone_exists:
                self.stdout.write(
                    self.style.WARNING('Missing customer_phone column in sales_app_invoice')
                )
                
                if not options['check_only']:
                    self.stdout.write('Applying migrations...')
                    call_command('migrate', 'sales_app', verbosity=2)
                    self.stdout.write(
                        self.style.SUCCESS('Migrations applied successfully!')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING('Run without --check-only to apply fixes')
                    )
            else:
                self.stdout.write(
                    self.style.SUCCESS('customer_phone column exists - schema is up to date')
                )

            # Check for cash tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name IN ('sales_app_cashproduct', 'sales_app_cashinvoice', 'sales_app_cashsale');
            """)
            cash_tables = cursor.fetchall()
            
            expected_tables = ['sales_app_cashproduct', 'sales_app_cashinvoice', 'sales_app_cashsale']
            existing_tables = [row[0] for row in cash_tables]
            missing_tables = [table for table in expected_tables if table not in existing_tables]
            
            if missing_tables:
                self.stdout.write(
                    self.style.WARNING(f'Missing cash department tables: {missing_tables}')
                )
                if not options['check_only']:
                    self.stdout.write('Applying migrations...')
                    call_command('migrate', 'sales_app', verbosity=2)
            else:
                self.stdout.write(
                    self.style.SUCCESS('All cash department tables exist')
                )
