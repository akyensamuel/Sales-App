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
from django.contrib.auth.models import User, Group

def test_delete_permissions():
    print("=== DELETE FUNCTIONALITY TEST ===")
    
    # Check users and groups
    print("\n1. USERS AND GROUPS:")
    users = User.objects.all()
    for user in users:
        groups = user.groups.all()
        print(f"   User: {user.username} - Groups: {[g.name for g in groups]}")
    
    # Check invoices
    print("\n2. SAMPLE INVOICES:")
    invoices = Invoice.objects.all()[:5]
    for invoice in invoices:
        user_name = invoice.user.username if invoice.user else "NO USER ASSIGNED"
        print(f"   Invoice {invoice.id}: {invoice.invoice_no} - Customer: {invoice.customer_name} - User: {user_name}")
    
    # Check recent admin logs
    print("\n3. RECENT ADMIN LOGS:")
    logs = AdminLog.objects.all().order_by('-timestamp')[:5]
    for log in logs:
        print(f"   {log.timestamp} - {log.user.username}: {log.action}")
        if log.details:
            print(f"      Details: {log.details}")
    
    print("\n4. CHECKING MANAGERS GROUP:")
    try:
        managers_group = Group.objects.get(name='Managers')
        managers = managers_group.user_set.all()
        print(f"   Managers group exists with {managers.count()} members:")
        for manager in managers:
            print(f"      - {manager.username}")
    except Group.DoesNotExist:
        print("   ERROR: Managers group does not exist!")
    
    print("\nTest completed.")

if __name__ == '__main__':
    test_delete_permissions()
