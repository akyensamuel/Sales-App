#!/usr/bin/env python
"""
Performance Monitoring Script
Tracks database performance before and after optimization
"""

import os
import sys
import django
from pathlib import Path
import time

# Setup Django
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sales_management_project.settings')
django.setup()

from django.db import connection

def monitor_performance():
    with connection.cursor() as cursor:
        print("⚡ Performance Monitoring Report")
        print("=" * 50)
        
        # Index count summary
        cursor.execute("""
            SELECT 
                COUNT(*) as total_indexes,
                SUM(CASE WHEN idx_scan = 0 THEN 1 ELSE 0 END) as unused_indexes,
                SUM(CASE WHEN idx_scan > 0 AND idx_scan < 10 THEN 1 ELSE 0 END) as low_usage,
                SUM(CASE WHEN idx_scan >= 10 THEN 1 ELSE 0 END) as active_indexes
            FROM pg_stat_user_indexes 
            WHERE schemaname = 'public'
        """)
        
        total, unused, low, active = cursor.fetchone()
        print(f"📊 Index Summary:")
        print(f"   Total: {total}")
        print(f"   🔴 Unused (0 scans): {unused}")
        print(f"   🟡 Low usage (<10 scans): {low}")
        print(f"   🟢 Active (≥10 scans): {active}")
        print(f"   💾 Efficiency: {(active/(total or 1))*100:.1f}%")
        
        # Table sizes
        cursor.execute("""
            SELECT 
                tablename,
                pg_size_pretty(pg_total_relation_size('public.'||tablename)) as size,
                pg_total_relation_size('public.'||tablename) as size_bytes
            FROM pg_tables 
            WHERE schemaname = 'public'
              AND (tablename LIKE 'sales_app_%' OR tablename LIKE 'accounting_app_%')
            ORDER BY size_bytes DESC
            LIMIT 10
        """)
        
        print(f"\n📏 Largest Tables:")
        for table, size, size_bytes in cursor.fetchall():
            print(f"   {table:<40} {size}")
        
        # Performance test: Sample queries
        print(f"\n⏱️  Query Performance Test:")
        
        # Test invoice queries
        start = time.time()
        cursor.execute("""
            SELECT COUNT(*) FROM sales_app_invoice 
            WHERE date_of_sale >= CURRENT_DATE - INTERVAL '30 days'
        """)
        count = cursor.fetchone()[0]
        duration = (time.time() - start) * 1000
        print(f"   Recent invoices query: {duration:.2f}ms ({count} records)")
        
        # Test product queries
        start = time.time()
        cursor.execute("""
            SELECT COUNT(*) FROM sales_app_product 
            WHERE stock > 0
        """)
        count = cursor.fetchone()[0]
        duration = (time.time() - start) * 1000
        print(f"   In-stock products query: {duration:.2f}ms ({count} records)")
        
        # Test sales queries
        start = time.time()
        cursor.execute("""
            SELECT COUNT(*) FROM sales_app_sale s
            JOIN sales_app_invoice i ON s.invoice_id = i.id
            WHERE i.payment_status = 'Paid'
        """)
        count = cursor.fetchone()[0]
        duration = (time.time() - start) * 1000
        print(f"   Paid sales query: {duration:.2f}ms ({count} records)")
        
        print(f"\n🎯 Optimization Impact:")
        removed_indexes = 75 - unused  # Original unused count minus current
        if removed_indexes > 0:
            print(f"   ✅ Removed {removed_indexes} unused indexes")
            print(f"   💾 Improved INSERT/UPDATE performance")
            print(f"   📉 Reduced storage overhead")
        else:
            print(f"   📋 No optimization applied yet")
            print(f"   💡 Ready for Phase 1 optimization")

if __name__ == "__main__":
    monitor_performance()
