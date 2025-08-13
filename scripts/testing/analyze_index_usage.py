#!/usr/bin/env python
"""
Database Index Usage Analysis Script
Analyzes index usage patterns before optimization
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

def analyze_index_usage():
    with connection.cursor() as cursor:
        print("📊 Database Index Usage Analysis")
        print("=" * 50)
        
        # Get index usage statistics
        cursor.execute("""
            SELECT 
                schemaname,
                relname as tablename,
                indexrelname as indexname,
                idx_scan as scans,
                idx_tup_read as tuples_read,
                idx_tup_fetch as tuples_fetched,
                CASE 
                    WHEN idx_scan = 0 THEN '🔴 UNUSED'
                    WHEN idx_scan < 10 THEN '🟡 LOW USAGE'
                    WHEN idx_scan < 100 THEN '🟢 MODERATE'
                    ELSE '🟢 HIGH USAGE'
                END as usage_level
            FROM pg_stat_user_indexes 
            WHERE schemaname = 'public'
            ORDER BY idx_scan DESC, relname, indexrelname
        """)
        
        indexes = cursor.fetchall()
        
        unused_count = 0
        low_usage_count = 0
        used_count = 0
        
        print("\n📈 Index Usage Report:")
        print("-" * 80)
        print(f"{'Table':<30} {'Index':<40} {'Scans':<10} {'Status'}")
        print("-" * 80)
        
        for schema, table, index, scans, tuples_read, tuples_fetched, usage_level in indexes:
            print(f"{table:<30} {index:<40} {scans:<10} {usage_level}")
            
            if scans == 0:
                unused_count += 1
            elif scans < 10:
                low_usage_count += 1
            else:
                used_count += 1
        
        print("\n📊 Summary:")
        print(f"🔴 Unused indexes: {unused_count}")
        print(f"🟡 Low usage indexes: {low_usage_count}")
        print(f"🟢 Active indexes: {used_count}")
        print(f"📋 Total indexes: {len(indexes)}")
        
        # Get table sizes
        print("\n📏 Table Sizes:")
        print("-" * 50)
        cursor.execute("""
            SELECT 
                tablename,
                pg_size_pretty(pg_total_relation_size('public.'||tablename)) as size,
                pg_total_relation_size('public.'||tablename) as size_bytes
            FROM pg_tables 
            WHERE schemaname = 'public'
              AND tablename LIKE 'sales_app_%' OR tablename LIKE 'accounting_app_%'
            ORDER BY size_bytes DESC
        """)
        
        tables = cursor.fetchall()
        for table, size, size_bytes in tables:
            print(f"{table:<40} {size}")
        
        # Get most expensive queries
        print("\n⚡ Query Performance Impact:")
        print("-" * 50)
        cursor.execute("""
            SELECT 
                query,
                calls,
                total_time,
                mean_time,
                (total_time/sum(total_time) OVER()) * 100 as percentage
            FROM pg_stat_statements 
            WHERE query LIKE '%sales_app%' OR query LIKE '%accounting_app%'
            ORDER BY total_time DESC
            LIMIT 10
        """)
        
        try:
            queries = cursor.fetchall()
            for query, calls, total_time, mean_time, percentage in queries:
                print(f"Calls: {calls}, Total: {total_time:.2f}ms, Mean: {mean_time:.2f}ms, Impact: {percentage:.1f}%")
                print(f"Query: {query[:100]}...")
                print("-" * 50)
        except Exception as e:
            print("⚠️  pg_stat_statements extension not available for query analysis")
            print("This is normal for many database configurations.")

if __name__ == "__main__":
    analyze_index_usage()
