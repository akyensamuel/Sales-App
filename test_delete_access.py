#!/usr/bin/env python
import os
import sys
import django

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sales_management_project.settings')
django.setup()

from django.test import RequestFactory, Client
from django.contrib.auth.models import User
from sales_app.views import manager_dashboard, is_manager
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.messages.middleware import MessageMiddleware

def test_manager_permissions():
    print("=== MANAGER PERMISSION TEST ===")
    
    # Get the user
    user = User.objects.get(username='Akyen')
    print(f"Testing user: {user.username}")
    print(f"User groups: {[g.name for g in user.groups.all()]}")
    print(f"Is manager: {is_manager(user)}")
    
    # Test manager dashboard access
    print("\n=== TESTING MANAGER DASHBOARD ACCESS ===")
    client = Client()
    
    # Login the user
    client.force_login(user)
    
    # Try to access manager dashboard
    response = client.get('/sales/manager_dashboard/')
    print(f"Manager dashboard response status: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ User can access manager dashboard")
        
        # Check if delete buttons are present in the response
        if b'delete_invoice_id' in response.content:
            print("✅ Delete forms are present in the page")
        else:
            print("❌ Delete forms are NOT present in the page")
            
        if b'btn delete' in response.content or b'Delete' in response.content:
            print("✅ Delete buttons are visible in the page")
        else:
            print("❌ Delete buttons are NOT visible in the page")
            
    else:
        print(f"❌ User cannot access manager dashboard. Status: {response.status_code}")
        print(f"Response content: {response.content[:500]}")

def test_delete_post():
    print("\n=== TESTING DELETE POST REQUEST ===")
    
    client = Client()
    user = User.objects.get(username='Akyen')
    client.force_login(user)
    
    # Get an invoice to test with
    from sales_app.models import Invoice
    test_invoice = Invoice.objects.first()
    
    if test_invoice:
        print(f"Testing delete of invoice: {test_invoice.invoice_no} (ID: {test_invoice.id})")
        
        # Simulate the POST request
        response = client.post('/sales/manager_dashboard/', {
            'delete_invoice_id': test_invoice.id
        })
        
        print(f"Delete POST response status: {response.status_code}")
        print(f"Delete POST redirect location: {response.get('Location', 'No redirect')}")
        
        # Check if the invoice still exists
        invoice_exists = Invoice.objects.filter(id=test_invoice.id).exists()
        print(f"Invoice still exists after delete attempt: {invoice_exists}")
        
    else:
        print("❌ No invoices found to test with")

if __name__ == '__main__':
    test_manager_permissions()
    test_delete_post()
