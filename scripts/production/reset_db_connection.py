#!/usr/bin/env python
"""
Database Connection Reset Tool
=============================
Fixes stuck PostgreSQL transactions before CSV import
"""

import os
import sys
import django
from django.db import connection, transaction

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sales_management_project.settings')
django.setup()

def reset_database_connection():
    """Reset database connection and clear any stuck transactions"""
    print("🔧 Resetting database connection...")
    
    try:
        # Close existing connections
        connection.close()
        print("✅ Closed existing connections")
        
        # Force a new connection with rollback
        with connection.cursor() as cursor:
            # Rollback any pending transactions
            connection.rollback()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
        print("✅ New connection established successfully")
        print(f"📊 Connection test result: {result}")
        return True
        
    except Exception as e:
        print(f"❌ Connection reset failed: {str(e)}")
        return False

def test_database_operations():
    """Test basic database operations"""
    print("\n🧪 Testing database operations...")
    
    try:
        from sales_app.models import Product
        
        # Test query
        count = Product.objects.count()
        print(f"✅ Product count query successful: {count} products")
        
        # Test transaction
        with transaction.atomic():
            # Just test the transaction block
            pass
        print("✅ Transaction test successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Database operations test failed: {str(e)}")
        return False

def main():
    """Main reset function"""
    print("🚀 Database Connection Reset Tool")
    print("=" * 40)
    
    # Step 1: Reset connection
    if reset_database_connection():
        print("\n✅ Connection reset successful")
    else:
        print("\n❌ Connection reset failed")
        return
        
    # Step 2: Test operations
    if test_database_operations():
        print("\n🎉 Database is ready for CSV import!")
        print("\nYou can now run: python production_csv_import.py")
    else:
        print("\n❌ Database operations still failing")
        print("💡 Try running this script again, or restart your terminal")

if __name__ == "__main__":
    main()
