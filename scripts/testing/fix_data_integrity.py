"""
Data cleanup script to fix None dates in invoices
"""
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sales_management_project.settings')
django.setup()

from django.utils import timezone
from sales_app.models import Invoice

def fix_null_dates():
    """Fix invoices with null date_of_sale"""
    print("Checking for invoices with null dates...")
    
    # Find invoices with null dates
    null_date_invoices = Invoice.objects.filter(date_of_sale__isnull=True)
    count = null_date_invoices.count()
    
    if count == 0:
        print("✓ No invoices with null dates found")
        return
    
    print(f"Found {count} invoices with null dates")
    
    # Set them to today's date or creation date if available
    today = timezone.now().date()
    updated_count = 0
    
    for invoice in null_date_invoices:
        # Try to use a reasonable date
        if hasattr(invoice, 'created_at') and invoice.created_at:
            invoice.date_of_sale = invoice.created_at.date()
        else:
            invoice.date_of_sale = today
        
        invoice.save()
        updated_count += 1
        print(f"Fixed invoice {invoice.invoice_no or invoice.id} - set date to {invoice.date_of_sale}")
    
    print(f"✓ Updated {updated_count} invoices with proper dates")

def validate_data_integrity():
    """Validate other potential data integrity issues"""
    print("\nValidating data integrity...")
    
    # Check for other None values that might cause issues
    issues_found = 0
    
    # Check invoices with None customer names
    invoices_no_customer = Invoice.objects.filter(customer_name__isnull=True).count()
    if invoices_no_customer > 0:
        print(f"⚠️  {invoices_no_customer} invoices have null customer names")
        issues_found += 1
    
    # Check invoices with None totals
    invoices_no_total = Invoice.objects.filter(total__isnull=True).count()
    if invoices_no_total > 0:
        print(f"⚠️  {invoices_no_total} invoices have null totals")
        issues_found += 1
    
    # Check invoices with None payment status
    invoices_no_status = Invoice.objects.filter(payment_status__isnull=True).count()
    if invoices_no_status > 0:
        print(f"⚠️  {invoices_no_status} invoices have null payment status")
        issues_found += 1
    
    if issues_found == 0:
        print("✓ No data integrity issues found")
    else:
        print(f"Found {issues_found} potential data integrity issues")

def run_cleanup():
    """Run all cleanup operations"""
    print("=" * 50)
    print("DATA CLEANUP AND VALIDATION")
    print("=" * 50)
    
    try:
        fix_null_dates()
        validate_data_integrity()
        
        print("\n" + "=" * 50)
        print("✅ DATA CLEANUP COMPLETED")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ CLEANUP FAILED: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    run_cleanup()
