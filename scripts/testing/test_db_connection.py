#!/usr/bin/env python
"""
Database Connection Test
========================
Test connection to production database and show current schema info.
"""

import os
import sys
import django
from django.conf import settings
from django.db import connection

def setup_django():
    """Initialize Django settings."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sales_management_project.settings')
    django.setup()

def test_connection():
    """Test database connection and show info."""
    print("🔍 Testing database connection...")
    
    try:
        with connection.cursor() as cursor:
            # Test basic connection
            cursor.execute("SELECT 1")
            print("✅ Database connection successful!")
            
            # Show database info
            db_settings = settings.DATABASES['default']
            print(f"\n📊 DATABASE INFO:")
            print(f"   Engine: {db_settings.get('ENGINE', 'Unknown')}")
            print(f"   Name: {db_settings.get('NAME', 'Unknown')}")
            print(f"   Host: {db_settings.get('HOST', 'Unknown')}")
            print(f"   Port: {db_settings.get('PORT', 'Unknown')}")
            print(f"   User: {db_settings.get('USER', 'Unknown')}")
            
            # Check if we're connected to PostgreSQL
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            print(f"   Version: {version}")
            
            # Check if sales_app_invoice table exists
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name = 'sales_app_invoice'
            """)
            if cursor.fetchone():
                print("\n✅ sales_app_invoice table exists")
                
                # Check for customer_phone column
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'sales_app_invoice' 
                    AND column_name = 'customer_phone'
                """)
                if cursor.fetchone():
                    print("✅ customer_phone column exists - NO MIGRATION NEEDED")
                else:
                    print("❌ customer_phone column MISSING - MIGRATION NEEDED")
            else:
                print("❌ sales_app_invoice table does not exist")
                
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    setup_django()
    return test_connection()

if __name__ == "__main__":
    if main():
        sys.exit(0)
    else:
        sys.exit(1)
