#!/usr/bin/env python
"""
Quick Delete Test Tool

Run this to test delete functionality directly:
python quick_delete_test.py [invoice_id]
"""
import os
import sys
import django

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sales_management_project.settings')
django.setup()

from sales_app.models import Invoice, AdminLog
from django.contrib.auth.models import User
from sales_app.views import restore_stock_for_sale_items
from django.db import transaction

def quick_delete_test(invoice_id=None):
    print("=== QUICK DELETE TEST ===")
    
    if not invoice_id:
        # Get the first invoice
        test_invoice = Invoice.objects.first()
        if not test_invoice:
            print("❌ No invoices found!")
            return
        invoice_id = test_invoice.id
    else:
        try:
            test_invoice = Invoice.objects.get(id=invoice_id)
        except Invoice.DoesNotExist:
            print(f"❌ Invoice with ID {invoice_id} not found!")
            return
    
    print(f"Testing delete of Invoice: {test_invoice.invoice_no} (ID: {invoice_id})")
    print(f"Customer: {test_invoice.customer_name}")
    
    user = User.objects.get(username='Akyen')
    
    # Ask for confirmation
    confirm = input("Are you sure you want to delete this invoice? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Delete cancelled.")
        return
    
    try:
        with transaction.atomic():
            print("1. Restoring stock...")
            restore_stock_for_sale_items(test_invoice.items.all(), test_invoice.invoice_no)
            
            print("2. Creating admin log...")
            AdminLog.objects.create(
                user=user,
                action='Manual Delete (Stock Restored)',
                details=f'Invoice ID: {invoice_id}, Customer: {test_invoice.customer_name}'
            )
            
            print("3. Deleting invoice...")
            test_invoice.delete()
            
            print("✅ Invoice deleted successfully!")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    invoice_id = sys.argv[1] if len(sys.argv) > 1 else None
    if invoice_id:
        try:
            invoice_id = int(invoice_id)
        except ValueError:
            print("Invalid invoice ID. Please provide a number.")
            sys.exit(1)
    
    quick_delete_test(invoice_id)
