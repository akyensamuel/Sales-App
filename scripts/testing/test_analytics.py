#!/usr/bin/env python
"""
Test script for analytics functionality
"""
import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sales_management_project.settings')
django.setup()

from accounting_app.analytics import AnalyticsEngine
from accounting_app.models import ProductPerformance, SalesPersonPerformance
from sales_app.models import Sale, Product
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta

def test_analytics():
    """Test analytics functionality"""
    print("🔍 Testing Analytics System...")
    
    # Test AnalyticsEngine initialization
    engine = AnalyticsEngine()
    print("✅ AnalyticsEngine initialized successfully")
    
    # Test getting product performance (should work even with no data)
    try:
        product_data = engine.get_product_performance()
        print(f"✅ Product performance data retrieved: {len(product_data)} products")
    except Exception as e:
        print(f"❌ Product performance error: {e}")
        
    # Test getting salesperson performance
    try:
        sales_data = engine.get_salesperson_performance()
        print(f"✅ Salesperson performance data retrieved: {len(sales_data)} staff members")
    except Exception as e:
        print(f"❌ Salesperson performance error: {e}")
    
    # Test model creation
    try:
        # Check if we have any products
        products = Product.objects.all()
        print(f"📦 Found {products.count()} products in database")
        
        # Check if we have any users with required roles
        managers = User.objects.filter(groups__name='Managers')
        cashiers = User.objects.filter(groups__name='Cashiers')
        print(f"👥 Found {managers.count()} managers, {cashiers.count()} cashiers")
        
        # Test ProductPerformance model
        performance_count = ProductPerformance.objects.count()
        print(f"📊 Current ProductPerformance records: {performance_count}")
        
        # Test SalesPersonPerformance model  
        staff_count = SalesPersonPerformance.objects.count()
        print(f"👨‍💼 Current SalesPersonPerformance records: {staff_count}")
        
        print("✅ All analytics models accessible")
        
    except Exception as e:
        print(f"❌ Model test error: {e}")
        
    print("\n🎉 Analytics system test completed!")

if __name__ == '__main__':
    test_analytics()
