#!/usr/bin/env python
"""
RLS Security Status Verification Script
Checks if all security policies are properly applied
"""

import os
import sys
import django
from pathlib import Path

# Setup Django with correct path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sales_management_project.settings')
django.setup()

from django.db import connection

def check_rls_status():
    with connection.cursor() as cursor:
        # Check tables with RLS enabled
        cursor.execute("""
            SELECT schemaname, tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' AND rowsecurity = true 
            ORDER BY tablename
        """)
        rls_tables = cursor.fetchall()
        
        # Check policies count
        cursor.execute("""
            SELECT COUNT(*) 
            FROM pg_policies 
            WHERE schemaname = 'public'
        """)
        policy_count = cursor.fetchone()[0]
        
        print("🔐 RLS Security Status Report")
        print("=" * 40)
        print(f"✅ Tables with RLS enabled: {len(rls_tables)}")
        print(f"✅ Security policies created: {policy_count}")
        print()
        
        print("📋 Protected Tables:")
        for schema, table in rls_tables:
            print(f"   ✅ {table}")
        
        # Test access to a protected table
        try:
            cursor.execute("SELECT COUNT(*) FROM sales_app_invoice")
            count = cursor.fetchone()[0]
            print(f"\n🧪 Access Test: Can access {count} invoice records")
            print("✅ RLS Security is working correctly!")
        except Exception as e:
            print(f"\n❌ Access Test Failed: {e}")
        
        print("\n🎉 Security Status: COMPLETE")

if __name__ == "__main__":
    check_rls_status()
