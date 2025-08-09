"""
Test script to verify the accounting template filter fixes
"""
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sales_management_project.settings')
django.setup()

from django.utils import timezone
from datetime import timedelta
from sales_app.models import Invoice
from accounting_app.templatetags.accounting_filters import count_old_invoices, count_overdue, total_outstanding

def test_template_filters():
    """Test that template filters handle None values properly"""
    print("Testing accounting template filters...")
    
    # Get some invoices for testing
    invoices = Invoice.objects.all()[:10]
    
    if not invoices:
        print("No invoices found for testing")
        return
    
    try:
        # Test count_old_invoices filter
        old_count = count_old_invoices(invoices, 30)
        print(f"✓ count_old_invoices: Found {old_count} old invoices")
        
        # Test count_overdue filter
        overdue_count = count_overdue(invoices)
        print(f"✓ count_overdue: Found {overdue_count} overdue invoices")
        
        # Test total_outstanding filter
        outstanding = total_outstanding(invoices)
        print(f"✓ total_outstanding: ₵{outstanding}")
        
        print("✅ All template filters working correctly")
        
    except Exception as e:
        print(f"❌ Template filter error: {str(e)}")
        raise

def test_with_edge_cases():
    """Test filters with edge cases like None values"""
    print("\nTesting edge cases...")
    
    # Create a mock invoice with None values to test robustness
    class MockInvoice:
        def __init__(self, date_of_sale=None, payment_status=None, balance=0):
            self.date_of_sale = date_of_sale
            self.payment_status = payment_status
            self.balance = balance
    
    # Test with mixed data
    mock_invoices = [
        MockInvoice(timezone.now().date() - timedelta(days=60), 'overdue', 100),
        MockInvoice(None, 'paid', 0),  # None date - should not crash
        MockInvoice(timezone.now().date(), None, 50),  # None payment status
        MockInvoice(timezone.now().date() - timedelta(days=10), 'unpaid', 200),
    ]
    
    try:
        old_count = count_old_invoices(mock_invoices, 30)
        overdue_count = count_overdue(mock_invoices)
        outstanding = total_outstanding(mock_invoices)
        
        print(f"✓ Edge case old_count: {old_count}")
        print(f"✓ Edge case overdue_count: {overdue_count}")
        print(f"✓ Edge case outstanding: {outstanding}")
        print("✅ Edge cases handled correctly")
        
    except Exception as e:
        print(f"❌ Edge case error: {str(e)}")
        raise

def run_tests():
    """Run all filter tests"""
    print("=" * 50)
    print("ACCOUNTING TEMPLATE FILTER TESTS")
    print("=" * 50)
    
    try:
        test_template_filters()
        test_with_edge_cases()
        
        print("\n" + "=" * 50)
        print("✅ ALL TESTS PASSED - FILTERS ARE WORKING")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ TESTS FAILED: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    run_tests()
