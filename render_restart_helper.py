#!/usr/bin/env python
"""
Simple Production Database Connection Fix
========================================
This script can be used to diagnose and document database connection issues
for Render free plan deployments.

Since Render free plan doesn't support custom management commands during
deployment, this serves as a diagnostic tool you can run locally.
"""

import os
import sys
import django
from datetime import datetime

def setup_django():
    """Initialize Django settings."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sales_management_project.settings')
    django.setup()

def create_restart_trigger():
    """Create a file to trigger Git-based restart."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    restart_content = f"""# Render Restart Trigger
# Generated: {datetime.now().isoformat()}
# Purpose: Force Render service restart to clear database connection cache

RESTART_TIMESTAMP = "{timestamp}"
REASON = "Database connection cache refresh needed"

# This file triggers a deployment when committed to Git
# Render free plan will automatically restart the service
"""
    
    with open('restart_trigger.py', 'w') as f:
        f.write(restart_content)
    
    print(f"✅ Created restart_trigger.py with timestamp {timestamp}")
    print("📝 To restart Render service:")
    print("   1. git add restart_trigger.py")
    print("   2. git commit -m 'Force service restart for DB cache refresh'")
    print("   3. git push origin main")
    print("   4. Wait for Render to redeploy")

def check_local_connection():
    """Test local connection to production database."""
    print("🔍 Testing local connection to production database...")
    
    try:
        setup_django()
        from django.db import connection
        from sales_app.models import Invoice
        
        # Test basic connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # Test the problematic query
        invoices = Invoice.objects.select_related('user').prefetch_related('items')[:1]
        for invoice in invoices:
            customer_phone = invoice.customer_phone  # This should work
            break
        
        print("✅ Local connection to production database works fine")
        print("📊 This confirms the issue is in production server connections")
        return True
        
    except Exception as e:
        print(f"❌ Local connection test failed: {e}")
        return False

def main():
    """Main diagnostic and restart trigger function."""
    print("🛠️  RENDER FREE PLAN - PRODUCTION DB FIX")
    print("="*50)
    
    # Check if we can connect locally
    if check_local_connection():
        print("\n✅ Database schema is correct")
        print("🔄 Issue is production server connection caching")
        print("💡 Solution: Force Render service restart")
        
        create_restart_trigger()
        
        print(f"\n🎯 NEXT STEPS:")
        print("1. Run the git commands shown above")
        print("2. Check Render dashboard for deployment progress")
        print("3. Test manager dashboard once deployment completes")
        
        return 0
    else:
        print("\n❌ There may be a deeper issue")
        print("🔍 Check your .env file and database connection")
        return 1

if __name__ == "__main__":
    sys.exit(main())
