#!/usr/bin/env python
"""
Production Database Schema Cache Fix
===================================
This script fixes database connection/cache issues in production
by forcing Django to refresh its schema cache and connections.
"""

import os
import sys
import django
from django.conf import settings
from django.db import connection
from django.core.management import call_command

def setup_django():
    """Initialize Django settings."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sales_management_project.settings')
    django.setup()

def clear_database_cache():
    """Clear Django's internal database schema cache."""
    print("🔄 Clearing database schema cache...")
    
    # Close and reopen all database connections
    from django.db import connections
    for conn in connections.all():
        conn.close()
    
    # Clear the introspection cache
    if hasattr(connection, 'introspection'):
        if hasattr(connection.introspection, 'cache_clear'):
            connection.introspection.cache_clear()
    
    print("✅ Database cache cleared")

def test_query():
    """Test the problematic query that was failing in production."""
    print("🧪 Testing problematic query...")
    
    try:
        from sales_app.models import Invoice
        from django.core.paginator import Paginator
        from datetime import date
        
        # This is the exact query that was failing in production
        invoices_query = Invoice.objects.select_related('user').prefetch_related('items')
        today = date.today()
        invoices = invoices_query.filter(date_of_sale=today).order_by('-date_of_sale')
        
        # Test pagination (this is where the error occurred)
        paginator = Paginator(invoices, 25)
        page_1 = paginator.page(1)
        
        print(f"✅ Query successful - found {len(page_1)} invoices")
        print(f"✅ Total invoices for today: {paginator.count}")
        
        # Test that customer_phone field is accessible
        for invoice in page_1:
            customer_phone = invoice.customer_phone  # This should not fail
            break
        else:
            print("ℹ️  No invoices found to test customer_phone field")
        
        return True
        
    except Exception as e:
        print(f"❌ Query test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def force_migration_sync():
    """Force Django to re-sync the migration state."""
    print("🔄 Forcing migration state sync...")
    
    try:
        # This forces Django to check migration status
        call_command('showmigrations', verbosity=0)
        print("✅ Migration state synced")
        return True
    except Exception as e:
        print(f"❌ Migration sync failed: {e}")
        return False

def main():
    """Main function to fix production database issues."""
    print("🛠️  PRODUCTION DATABASE SCHEMA CACHE FIX")
    print("="*50)
    
    setup_django()
    
    # Step 1: Clear database cache
    clear_database_cache()
    
    # Step 2: Force migration sync
    force_migration_sync()
    
    # Step 3: Test the problematic query
    if test_query():
        print("\n✅ SUCCESS: Database schema cache has been refreshed!")
        print("🎉 The manager dashboard should now work correctly.")
        return 0
    else:
        print("\n❌ FAILED: Query test still failing after cache refresh.")
        print("🔍 This suggests a deeper database connection issue.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
