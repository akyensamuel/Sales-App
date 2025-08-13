#!/usr/bin/env python
"""
Production Migration Script
==========================
This script applies pending migrations to the production database safely.
It connects to the production database using the DATABASE_URL from .env file.

SAFETY MEASURES:
- Shows pending migrations before applying
- Creates a migration plan
- Allows you to confirm before execution
- Uses Django's built-in migration system

PREREQUISITES:
- Ensure your .env file has the correct production DATABASE_URL
- Backup your database before running (recommended)
- Test in a staging environment first (if available)
"""

import os
import sys
import django
from django.conf import settings
from django.core.management import call_command, execute_from_command_line
from django.db import connection
from django.core.management.color import no_style

def setup_django():
    """Initialize Django settings."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sales_management_project.settings')
    django.setup()

def check_database_connection():
    """Verify we can connect to the database."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        print("✅ Database connection successful")
        
        # Show database info
        db_settings = settings.DATABASES['default']
        print(f"🔗 Connected to: {db_settings.get('NAME', 'Unknown')}")
        print(f"🏠 Host: {db_settings.get('HOST', 'Unknown')}")
        print(f"⚙️  Engine: {db_settings.get('ENGINE', 'Unknown')}")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def show_pending_migrations():
    """Show which migrations are pending."""
    print("\n" + "="*60)
    print("🔍 CHECKING PENDING MIGRATIONS")
    print("="*60)
    
    try:
        # Show migration status
        call_command('showmigrations', verbosity=1)
        return True
    except Exception as e:
        print(f"❌ Error checking migrations: {e}")
        return False

def show_migration_plan():
    """Show what the migrate command will do."""
    print("\n" + "="*60)
    print("📋 MIGRATION PLAN")
    print("="*60)
    
    try:
        # Show migration plan without applying
        call_command('migrate', '--plan', verbosity=1)
        return True
    except Exception as e:
        print(f"❌ Error showing migration plan: {e}")
        return False

def apply_migrations():
    """Apply the migrations."""
    print("\n" + "="*60)
    print("🚀 APPLYING MIGRATIONS")
    print("="*60)
    
    try:
        # Apply migrations
        call_command('migrate', verbosity=2)
        print("\n✅ Migrations applied successfully!")
        return True
    except Exception as e:
        print(f"❌ Error applying migrations: {e}")
        return False

def verify_customer_phone_column():
    """Verify that the customer_phone column was added."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'sales_app_invoice' 
                AND column_name = 'customer_phone';
            """)
            result = cursor.fetchone()
            
            if result:
                print("✅ customer_phone column exists in sales_app_invoice table")
                return True
            else:
                print("❌ customer_phone column NOT found in sales_app_invoice table")
                return False
    except Exception as e:
        print(f"❌ Error verifying customer_phone column: {e}")
        return False

def main():
    """Main function to run the migration process."""
    print("🔄 PRODUCTION MIGRATION SCRIPT")
    print("="*60)
    print("⚠️  WARNING: This will modify your production database!")
    print("📖 Make sure you have a backup before proceeding.")
    print("="*60)
    
    # Setup Django
    setup_django()
    
    # Check database connection
    if not check_database_connection():
        return 1
    
    # Show current migration status
    if not show_pending_migrations():
        return 1
    
    # Show migration plan
    if not show_migration_plan():
        return 1
    
    # Ask for confirmation
    print("\n" + "⚠️ "*20)
    print("FINAL CONFIRMATION")
    print("⚠️ "*20)
    response = input("\n🤔 Do you want to apply these migrations to PRODUCTION? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("❌ Migration cancelled by user.")
        return 1
    
    # Apply migrations
    if not apply_migrations():
        return 1
    
    # Verify the specific fix
    print("\n" + "="*60)
    print("🔍 VERIFYING FIXES")
    print("="*60)
    verify_customer_phone_column()
    
    print("\n✅ Migration process completed!")
    print("🎉 Your production database should now be up to date.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
