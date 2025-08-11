#!/usr/bin/env python
"""
CSV Import Debugger
===================
Debug tool to see exactly what data is being processed
"""

import os
import sys
import django
import csv

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sales_management_project.settings')
django.setup()

def debug_csv_content(csv_file_path, max_rows=5):
    """Show first few rows of CSV to understand the data"""
    print(f"🔍 Debugging CSV: {csv_file_path}")
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            print(f"📋 Column headers: {reader.fieldnames}")
            print("\n📊 Sample data:")
            print("-" * 80)
            
            for i, row in enumerate(reader):
                if i >= max_rows:
                    break
                    
                print(f"\nRow {i+1}:")
                for key, value in row.items():
                    if value and value.strip():  # Only show non-empty values
                        print(f"  {key}: '{value}'")
                        
            print(f"\n📈 Total rows in file: {sum(1 for line in open(csv_file_path)) - 1}")
            
    except Exception as e:
        print(f"❌ Debug failed: {str(e)}")

def test_field_mapping(csv_file_path):
    """Test the field mapping logic"""
    print(f"\n🧪 Testing field mapping...")
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            row = next(reader)  # Get first data row
            
            # Test product name extraction
            possible_product_keys = ['Item', 'product_name', 'item', 'product', 'name']
            product_name = None
            for key in possible_product_keys:
                if key in row and row[key]:
                    product_name = str(row[key]).strip()
                    print(f"✅ Product name found: '{product_name}' (from column: {key})")
                    break
                    
            if not product_name:
                print(f"❌ No product name found in keys: {possible_product_keys}")
                
            # Test quantity extraction  
            possible_qty_keys = ['Quantity', 'quantity', 'qty']
            quantity = None
            for key in possible_qty_keys:
                if key in row and row[key]:
                    try:
                        quantity = int(float(str(row[key]).replace(',', '').strip()))
                        print(f"✅ Quantity found: {quantity} (from column: {key})")
                        break
                    except:
                        continue
                        
            if not quantity:
                print(f"❌ No quantity found in keys: {possible_qty_keys}")
                
            # Test price extraction
            possible_price_keys = ['Unit Price', 'price', 'unit_price']
            price = None
            for key in possible_price_keys:
                if key in row and row[key]:
                    try:
                        price_str = str(row[key]).replace('₵', '').replace('$', '').replace(',', '').strip()
                        price = float(price_str)
                        print(f"✅ Price found: {price} (from column: {key})")
                        break
                    except:
                        continue
                        
            if not price:
                print(f"❌ No price found in keys: {possible_price_keys}")
                
    except Exception as e:
        print(f"❌ Field mapping test failed: {str(e)}")

if __name__ == "__main__":
    csv_file = r"D:\code\Sales_App_Unitary\SALES TABLE - SALES_TABLE.csv"
    
    print("🚀 CSV Import Debugger")
    print("=" * 50)
    
    debug_csv_content(csv_file, 3)
    test_field_mapping(csv_file)
