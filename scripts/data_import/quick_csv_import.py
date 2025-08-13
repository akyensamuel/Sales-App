#!/usr/bin/env python
"""
Quick CSV Import Fix for Production
==================================
For immediate use when regular import is stuck/buffering
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sales_management_project.settings')
django.setup()

from django.db import connection
import pandas as pd

def quick_import_small_csv(csv_file):
    """Quick import for small CSV files"""
    print(f"🚀 Quick importing: {csv_file}")
    
    try:
        # Read CSV
        df = pd.read_csv(csv_file)
        print(f"📊 Found {len(df)} rows")
        
        if len(df) > 500:
            print("⚠️ File too large for quick import. Use optimized_csv_import.py instead")
            return
            
        # Import in small chunks
        chunk_size = 20
        imported = 0
        
        for i in range(0, len(df), chunk_size):
            chunk = df.iloc[i:i+chunk_size]
            print(f"🔄 Processing rows {i+1}-{min(i+chunk_size, len(df))}")
            
            # Import chunk here based on your model
            # Example for products:
            from sales_app.models import Product
            
            for _, row in chunk.iterrows():
                try:
                    Product.objects.get_or_create(
                        name=row.get('name', f'Product_{imported}'),
                        defaults={
                            'price': float(row.get('price', 0)),
                            'quantity': int(row.get('quantity', 0)),
                            'description': row.get('description', '')
                        }
                    )
                    imported += 1
                except Exception as e:
                    print(f"⚠️ Row failed: {str(e)}")
                    
        print(f"✅ Quick import completed! Imported: {imported} items")
        
    except Exception as e:
        print(f"❌ Quick import failed: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        quick_import_small_csv(sys.argv[1])
    else:
        csv_file = input("Enter CSV file path: ").strip()
        quick_import_small_csv(csv_file)
