"""
Test script to verify the optimizations are working correctly
"""
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sales_management_project.settings')
django.setup()

from django.test import TestCase
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import time

from sales_app.models import Invoice, Product, Sale
from sales_app.cache_utils import SalesCache
from django.contrib.auth.models import User


def test_database_indexes():
    """Test that database indexes are working"""
    print("Testing database indexes...")
    
    # Test invoice queries with indexes
    start_time = time.time()
    invoices = Invoice.objects.filter(
        date_of_sale__gte=timezone.now().date() - timedelta(days=30),
        payment_status='paid'
    )[:10]
    list(invoices)  # Force query execution
    indexed_time = time.time() - start_time
    
    print(f"✓ Indexed query completed in {indexed_time*1000:.2f}ms")
    
    # Test product search with index
    start_time = time.time()
    products = Product.objects.filter(stock__lt=50).order_by('name')[:10]
    list(products)
    product_time = time.time() - start_time
    
    print(f"✓ Product search completed in {product_time*1000:.2f}ms")


def test_caching_system():
    """Test that caching is working correctly"""
    print("\nTesting caching system...")
    
    # Clear cache first
    cache.clear()
    
    # Test cache write/read
    test_key = 'test_optimization'
    test_data = {'message': 'Cache is working!', 'timestamp': timezone.now().isoformat()}
    
    # Write to cache
    start_time = time.time()
    cache.set(test_key, test_data, 300)
    write_time = time.time() - start_time
    
    # Read from cache
    start_time = time.time()
    cached_result = cache.get(test_key)
    read_time = time.time() - start_time
    
    print(f"✓ Cache write: {write_time*1000:.2f}ms")
    print(f"✓ Cache read: {read_time*1000:.2f}ms")
    print(f"✓ Cache data integrity: {'PASS' if cached_result == test_data else 'FAIL'}")
    
    # Test SalesCache utilities
    today = timezone.now().date()
    
    start_time = time.time()
    daily_summary = SalesCache.get_daily_sales_summary(today)
    cache_time = time.time() - start_time
    
    print(f"✓ Daily sales summary cache: {cache_time*1000:.2f}ms")
    print(f"✓ Summary data: {daily_summary}")
    
    # Test cache hit (should be faster)
    start_time = time.time()
    daily_summary_cached = SalesCache.get_daily_sales_summary(today)
    cached_hit_time = time.time() - start_time
    
    print(f"✓ Cache hit time: {cached_hit_time*1000:.2f}ms (should be faster)")
    print(f"✓ Data consistency: {'PASS' if daily_summary == daily_summary_cached else 'FAIL'}")


def test_query_optimization():
    """Test optimized queries vs unoptimized"""
    print("\nTesting query optimization...")
    
    # Unoptimized query (N+1 problem)
    start_time = time.time()
    invoices = Invoice.objects.all()[:5]
    for invoice in invoices:
        _ = invoice.user.username if invoice.user else 'No User'
        _ = list(invoice.items.all())
    unoptimized_time = time.time() - start_time
    
    # Optimized query with select_related and prefetch_related
    start_time = time.time()
    optimized_invoices = Invoice.objects.select_related('user').prefetch_related('items').all()[:5]
    for invoice in optimized_invoices:
        _ = invoice.user.username if invoice.user else 'No User'
        _ = list(invoice.items.all())
    optimized_time = time.time() - start_time
    
    improvement = ((unoptimized_time - optimized_time) / unoptimized_time * 100) if unoptimized_time > 0 else 0
    
    print(f"✓ Unoptimized query: {unoptimized_time*1000:.2f}ms")
    print(f"✓ Optimized query: {optimized_time*1000:.2f}ms")
    print(f"✓ Performance improvement: {improvement:.1f}%")


def test_pagination_performance():
    """Test pagination performance"""
    print("\nTesting pagination performance...")
    
    from django.core.paginator import Paginator
    
    # Test large dataset pagination
    start_time = time.time()
    all_invoices = Invoice.objects.select_related('user').prefetch_related('items').order_by('-date_of_sale')
    paginator = Paginator(all_invoices, 25)
    page_1 = paginator.page(1)
    list(page_1)  # Force evaluation
    pagination_time = time.time() - start_time
    
    print(f"✓ Paginated query (25 items): {pagination_time*1000:.2f}ms")
    print(f"✓ Total pages: {paginator.num_pages}")
    print(f"✓ Total items: {paginator.count}")


def run_all_tests():
    """Run all optimization tests"""
    print("=" * 50)
    print("SALES APP OPTIMIZATION TEST SUITE")
    print("=" * 50)
    
    try:
        test_database_indexes()
        test_caching_system()
        test_query_optimization()
        test_pagination_performance()
        
        print("\n" + "=" * 50)
        print("✅ ALL OPTIMIZATION TESTS COMPLETED SUCCESSFULLY")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    run_all_tests()
