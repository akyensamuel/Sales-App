#!/usr/bin/env python
"""
Simple CSV Import for Production Database
========================================
Uses only Django built-in CSV module - no external dependencies
Optimized for Supabase PostgreSQL production environment
"""

import os
import sys
import django
import csv
from decimal import Decimal
from datetime import datetime, date
from django.db import transaction, connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sales_management_project.settings')
django.setup()

from sales_app.models import Product, Sale, Invoice

class ProductionCSVImporter:
    def __init__(self):
        self.batch_size = 50  # Small batches for production
        self.imported_count = 0
        self.error_count = 0
        
    def log(self, message):
        """Simple logging with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def test_connection(self):
        """Test database connection"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
            self.log("✅ Database connection successful")
            return True
        except Exception as e:
            self.log(f"❌ Database connection failed: {str(e)}")
            return False
            
    def import_products_csv(self, csv_file_path):
        """Import products from CSV"""
        self.log(f"Starting product import: {csv_file_path}")
        
        if not os.path.exists(csv_file_path):
            self.log(f"❌ File not found: {csv_file_path}")
            return False
            
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                # Detect if file has header
                sample = file.read(1024)
                file.seek(0)
                
                # Try to detect delimiter
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                
                reader = csv.DictReader(file, delimiter=delimiter)
                
                # Show detected columns
                fieldnames = reader.fieldnames
                self.log(f"📋 Detected columns: {fieldnames}")
                
                # Process in batches
                batch = []
                total_rows = 0
                
                for row in reader:
                    batch.append(row)
                    total_rows += 1
                    
                    if len(batch) >= self.batch_size:
                        self._import_product_batch(batch, total_rows)
                        batch = []
                        
                # Import remaining rows
                if batch:
                    self._import_product_batch(batch, total_rows)
                    
                self.log(f"🎉 Import completed! Total rows: {total_rows}, Imported: {self.imported_count}, Errors: {self.error_count}")
                return True
                
        except Exception as e:
            self.log(f"❌ Import failed: {str(e)}")
            return False
            
    def _import_product_batch(self, batch, current_row):
        """Import a batch of products"""
        self.log(f"🔄 Processing batch ending at row {current_row} ({len(batch)} items)")
        
        try:
            with transaction.atomic():
                for row in batch:
                    try:
                        # Flexible field mapping - adjust these based on your CSV columns
                        name = self._safe_get(row, ['name', 'product_name', 'item_name', 'Name'])
                        price = self._safe_decimal(row, ['price', 'cost', 'amount', 'Price'])
                        stock = self._safe_int(row, ['stock', 'quantity', 'qty', 'Quantity'])
                        
                        if not name:
                            name = f"Product_{current_row}_{self.imported_count}"
                            
                        # Create or update product (using correct field names)
                        product, created = Product.objects.get_or_create(
                            name=name,
                            defaults={
                                'price': price,
                                'stock': stock
                            }
                        )
                        
                        if created:
                            self.imported_count += 1
                        else:
                            # Update existing product
                            if price > 0:
                                product.price = price
                            if stock >= 0:
                                product.stock = stock
                            product.save()
                            self.imported_count += 1
                            
                    except Exception as e:
                        self.error_count += 1
                        self.log(f"⚠️ Row error: {str(e)}")
                        
            self.log(f"✅ Batch completed successfully")
            
        except Exception as e:
            self.error_count += len(batch)
            self.log(f"❌ Batch failed: {str(e)}")
            
    def _safe_get(self, row, possible_keys):
        """Safely get value from row with multiple possible keys"""
        for key in possible_keys:
            if key in row and row[key]:
                return str(row[key]).strip()
        return ""
        
    def _safe_decimal(self, row, possible_keys):
        """Safely convert to decimal"""
        for key in possible_keys:
            if key in row and row[key]:
                try:
                    value = str(row[key]).replace('₵', '').replace('$', '').replace(',', '').strip()
                    return Decimal(value) if value else Decimal('0')
                except:
                    continue
        return Decimal('0')
        
    def _safe_int(self, row, possible_keys):
        """Safely convert to integer"""
        for key in possible_keys:
            if key in row and row[key]:
                try:
                    value = str(row[key]).replace(',', '').strip()
                    return int(float(value)) if value else 0
                except:
                    continue
        return 0
        
    def import_sales_csv(self, csv_file_path):
        """Import sales from CSV"""
        self.log(f"Starting sales import: {csv_file_path}")
        
        if not os.path.exists(csv_file_path):
            self.log(f"❌ File not found: {csv_file_path}")
            return False
            
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                fieldnames = reader.fieldnames
                self.log(f"📋 Detected sales columns: {fieldnames}")
                
                batch = []
                total_rows = 0
                
                for row in reader:
                    batch.append(row)
                    total_rows += 1
                    
                    if len(batch) >= 30:  # Smaller batches for sales
                        self._import_sales_batch(batch, total_rows)
                        batch = []
                        
                if batch:
                    self._import_sales_batch(batch, total_rows)
                    
                self.log(f"🎉 Sales import completed! Total: {total_rows}, Imported: {self.imported_count}, Errors: {self.error_count}")
                return True
                
        except Exception as e:
            self.log(f"❌ Sales import failed: {str(e)}")
            return False
            
    def _import_sales_batch(self, batch, current_row):
        """Import sales batch"""
        self.log(f"🔄 Processing sales batch ending at row {current_row}")
        
        try:
            with transaction.atomic():
                for row in batch:
                    try:
                        # Get product name from CSV
                        product_name = self._safe_get(row, ['Item', 'product_name', 'item', 'product', 'name'])
                        if not product_name:
                            self.log(f"⚠️ Skipping row - no product name found")
                            continue
                        
                        # Get other sale data
                        quantity_sold = self._safe_int(row, ['Quantity', 'quantity', 'qty']) or 1
                        unit_price = self._safe_decimal(row, ['Unit Price', 'price', 'unit_price'])
                        discount = self._safe_decimal(row, ['discount'])
                        
                        # Create or get product for reference (Sales uses CharField, not FK)
                        Product.objects.get_or_create(
                            name=product_name,
                            defaults={
                                'price': unit_price,
                                'stock': 0
                            }
                        )
                        
                        # Create sale record (Sale.item is CharField, not ForeignKey)
                        sale = Sale.objects.create(
                            item=product_name,  # CharField, not Product object
                            unit_price=unit_price,
                            quantity=quantity_sold,
                            discount=discount,
                            total_price=unit_price * quantity_sold - discount
                        )
                        
                        # Create invoice if invoice number exists
                        invoice_no = self._safe_get(row, ['Invoice No', 'invoice_number', 'invoice_no'])
                        if invoice_no and invoice_no.strip() and invoice_no != ';':
                            customer_name = self._safe_get(row, ['Customer Name', 'customer_name', 'customer'])
                            customer_phone = self._safe_get(row, ['CUSTOMER NO', 'customer_phone', 'phone'])
                            
                            # Calculate payment status
                            balance = self._safe_decimal(row, ['BAL TO BE PAID'])
                            payment_status = 'paid' if balance == 0 else 'partial' if balance < unit_price * quantity_sold else 'unpaid'
                            
                            invoice, invoice_created = Invoice.objects.get_or_create(
                                invoice_no=invoice_no,
                                defaults={
                                    'customer_name': customer_name or 'Unknown Customer',
                                    'customer_phone': customer_phone or '',
                                    'payment_status': payment_status,
                                    'total': unit_price * quantity_sold,
                                    'amount_paid': self._safe_decimal(row, ['AMT PAID'])
                                }
                            )
                            
                            # Link sale to invoice
                            sale.invoice = invoice
                            sale.save()
                        
                        self.imported_count += 1
                        
                    except Exception as e:
                        self.error_count += 1
                        self.log(f"⚠️ Sales row error: {str(e)}")
                        
        except Exception as e:
            self.error_count += len(batch)
            self.log(f"❌ Sales batch failed: {str(e)}")

def main():
    """Main function"""
    importer = ProductionCSVImporter()
    
    print("🚀 Production CSV Import Tool")
    print("=" * 40)
    
    # Test connection first
    if not importer.test_connection():
        print("❌ Database connection failed. Check your settings.")
        return
        
    print("\nWhat would you like to import?")
    print("1. Products")
    print("2. Sales") 
    print("3. Both")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice in ['1', '3']:
        csv_path = input("Enter path to products CSV: ").strip().replace('"', '')
        if csv_path and os.path.exists(csv_path):
            importer.import_products_csv(csv_path)
        else:
            print("❌ Products CSV file not found")
            
    if choice in ['2', '3']:
        csv_path = input("Enter path to sales CSV: ").strip().replace('"', '')
        if csv_path and os.path.exists(csv_path):
            importer.import_sales_csv(csv_path)
        else:
            print("❌ Sales CSV file not found")
            
    print(f"\n🎉 Import completed!")
    print(f"✅ Successfully imported: {importer.imported_count}")
    print(f"❌ Errors encountered: {importer.error_count}")

if __name__ == "__main__":
    main()
