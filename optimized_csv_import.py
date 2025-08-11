#!/usr/bin/env python
"""
Optimized CSV Import for Production Database
===========================================
Handles large datasets with batch processing, connection management,
and proper error handling for Supabase PostgreSQL.
"""

import os
import sys
import django
import pandas as pd
from django.db import transaction, connection
from django.core.management.base import BaseCommand
import time
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sales_management_project.settings')
django.setup()

# Import your models
from sales_app.models import Product, Sale, Invoice, Customer
from accounting_app.models import AccountingEntry

class OptimizedCSVImporter:
    def __init__(self, batch_size=100, max_retries=3):
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.imported_count = 0
        self.failed_count = 0
        
    def log(self, message):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def test_connection(self):
        """Test database connection"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            self.log("✅ Database connection successful")
            return True
        except Exception as e:
            self.log(f"❌ Database connection failed: {str(e)}")
            return False
            
    def import_products_csv(self, csv_file_path):
        """Import products with batch processing"""
        self.log(f"Starting product import from: {csv_file_path}")
        
        if not os.path.exists(csv_file_path):
            self.log(f"❌ File not found: {csv_file_path}")
            return False
            
        try:
            # Read CSV in chunks
            df = pd.read_csv(csv_file_path)
            total_rows = len(df)
            self.log(f"📊 Found {total_rows} rows to import")
            
            # Process in batches
            for i in range(0, total_rows, self.batch_size):
                batch = df.iloc[i:i+self.batch_size]
                batch_num = i // self.batch_size + 1
                total_batches = (total_rows + self.batch_size - 1) // self.batch_size
                
                self.log(f"🔄 Processing batch {batch_num}/{total_batches} ({len(batch)} rows)")
                
                success = self._import_product_batch(batch)
                if success:
                    self.imported_count += len(batch)
                    self.log(f"✅ Batch {batch_num} imported successfully")
                else:
                    self.failed_count += len(batch)
                    self.log(f"❌ Batch {batch_num} failed")
                    
                # Small delay to prevent overwhelming the database
                time.sleep(0.1)
                
            self.log(f"🎉 Import completed! Imported: {self.imported_count}, Failed: {self.failed_count}")
            return True
            
        except Exception as e:
            self.log(f"❌ Import failed: {str(e)}")
            return False
            
    def _import_product_batch(self, batch):
        """Import a single batch of products with retry logic"""
        for attempt in range(self.max_retries):
            try:
                with transaction.atomic():
                    products = []
                    for _, row in batch.iterrows():
                        product = Product(
                            name=row.get('name', ''),
                            price=float(row.get('price', 0)),
                            description=row.get('description', ''),
                            quantity=int(row.get('quantity', 0)),
                        )
                        products.append(product)
                    
                    # Bulk create for better performance
                    Product.objects.bulk_create(products, ignore_conflicts=True)
                    return True
                    
            except Exception as e:
                self.log(f"⚠️ Batch failed (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    
        return False
        
    def import_sales_csv(self, csv_file_path):
        """Import sales data with optimizations"""
        self.log(f"Starting sales import from: {csv_file_path}")
        
        if not os.path.exists(csv_file_path):
            self.log(f"❌ File not found: {csv_file_path}")
            return False
            
        try:
            df = pd.read_csv(csv_file_path)
            total_rows = len(df)
            self.log(f"📊 Found {total_rows} sales records to import")
            
            # Process in smaller batches for sales (more complex)
            sales_batch_size = max(50, self.batch_size // 2)
            
            for i in range(0, total_rows, sales_batch_size):
                batch = df.iloc[i:i+sales_batch_size]
                batch_num = i // sales_batch_size + 1
                total_batches = (total_rows + sales_batch_size - 1) // sales_batch_size
                
                self.log(f"🔄 Processing sales batch {batch_num}/{total_batches} ({len(batch)} rows)")
                
                success = self._import_sales_batch(batch)
                if success:
                    self.imported_count += len(batch)
                    self.log(f"✅ Sales batch {batch_num} imported successfully")
                else:
                    self.failed_count += len(batch)
                    self.log(f"❌ Sales batch {batch_num} failed")
                    
                time.sleep(0.2)  # Longer delay for sales
                
            return True
            
        except Exception as e:
            self.log(f"❌ Sales import failed: {str(e)}")
            return False
            
    def _import_sales_batch(self, batch):
        """Import sales batch with proper relationships"""
        for attempt in range(self.max_retries):
            try:
                with transaction.atomic():
                    for _, row in batch.iterrows():
                        # Create or get product
                        product_name = row.get('product_name', '')
                        product, _ = Product.objects.get_or_create(
                            name=product_name,
                            defaults={
                                'price': float(row.get('product_price', 0)),
                                'quantity': 0
                            }
                        )
                        
                        # Create sale
                        sale = Sale.objects.create(
                            item=product,
                            quantity=int(row.get('quantity', 1)),
                            discount=float(row.get('discount', 0)),
                            date=pd.to_datetime(row.get('date', 'today')).date() if pd.notna(row.get('date')) else None
                        )
                        
                        # Create invoice if needed
                        if row.get('invoice_number'):
                            Invoice.objects.get_or_create(
                                invoice_number=row.get('invoice_number'),
                                defaults={
                                    'customer_name': row.get('customer_name', ''),
                                    'customer_phone': row.get('customer_phone', ''),
                                    'due_date': pd.to_datetime(row.get('due_date', 'today')).date() if pd.notna(row.get('due_date')) else None,
                                    'payment_status': row.get('payment_status', 'pending')
                                }
                            )
                            
                    return True
                    
            except Exception as e:
                self.log(f"⚠️ Sales batch failed (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    
        return False

def main():
    """Main import function"""
    importer = OptimizedCSVImporter(batch_size=50)  # Smaller batches for production
    
    # Test connection first
    if not importer.test_connection():
        print("❌ Cannot connect to database. Check your connection.")
        return
        
    print("🚀 Optimized CSV Import Tool")
    print("=" * 40)
    
    import_type = input("What do you want to import? (products/sales/both): ").lower().strip()
    
    if import_type in ['products', 'both']:
        csv_path = input("Enter path to products CSV file: ").strip()
        if csv_path:
            importer.import_products_csv(csv_path)
            
    if import_type in ['sales', 'both']:
        csv_path = input("Enter path to sales CSV file: ").strip()
        if csv_path:
            importer.import_sales_csv(csv_path)
            
    print("\n🎉 Import process completed!")
    print(f"📊 Total imported: {importer.imported_count}")
    print(f"❌ Total failed: {importer.failed_count}")

if __name__ == "__main__":
    main()
