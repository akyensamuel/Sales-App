#!/usr/bin/env python
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

def test_manual_delete():
    print("=== MANUAL DELETE TEST ===")
    
    # Get a test invoice
    test_invoice = Invoice.objects.first()
    if not test_invoice:
        print("No invoices found to test with!")
        return
    
    print(f"Testing with Invoice: {test_invoice.invoice_no} (ID: {test_invoice.id})")
    print(f"Customer: {test_invoice.customer_name}")
    print(f"Items in invoice: {test_invoice.items.count()}")
    
    # Get the user
    user = User.objects.get(username='Akyen')
    
    try:
        with transaction.atomic():
            # Simulate the delete operation
            print("1. Restoring stock...")
            restore_stock_for_sale_items(test_invoice.items.all(), test_invoice.invoice_no)
            
            print("2. Creating admin log...")
            AdminLog.objects.create(
                user=user,
                action='Test Delete (Stock Restored)',
                details=f'Invoice ID: {test_invoice.id}, Customer: {test_invoice.customer_name}'
            )
            
            print("3. Simulating delete (NOT actually deleting)...")
            # test_invoice.delete()  # Comment this out to avoid actually deleting
            
            print("✅ Delete simulation completed successfully!")
            
    except Exception as e:
        print(f"❌ Error during delete simulation: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Check if admin log was created
    latest_log = AdminLog.objects.filter(action__contains='Test Delete').first()
    if latest_log:
        print(f"✅ Admin log created: {latest_log.action} by {latest_log.user.username}")
    else:
        print("❌ No admin log found")

if __name__ == '__main__':
    test_manual_delete()
