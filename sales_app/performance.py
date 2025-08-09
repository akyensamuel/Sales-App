"""
Performance monitoring and metrics API for sales app
"""
import time
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import connection
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from .models import Invoice, Product, Sale, AdminLog
from .cache_utils import SalesCache


def is_manager(user):
    """Check if user is a manager"""
    return user.is_authenticated and user.groups.filter(name='Managers').exists()


@login_required
@user_passes_test(is_manager)
@require_http_methods(["GET"])
def performance_metrics(request):
    """API endpoint to get performance metrics"""
    start_time = time.time()
    
    try:
        # Database metrics
        db_metrics = get_database_metrics()
        
        # Cache metrics
        cache_metrics = get_cache_metrics()
        
        # Application metrics
        app_metrics = get_application_metrics()
        
        # Response time for this endpoint
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        return JsonResponse({
            'status': 'success',
            'timestamp': timezone.now().isoformat(),
            'response_time_ms': round(response_time, 2),
            'database': db_metrics,
            'cache': cache_metrics,
            'application': app_metrics
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=500)


def get_database_metrics():
    """Get database performance metrics"""
    metrics = {}
    
    try:
        # Get database size and basic stats
        with connection.cursor() as cursor:
            if 'sqlite' in connection.settings_dict['ENGINE']:
                cursor.execute("PRAGMA page_count;")
                page_count = cursor.fetchone()[0]
                cursor.execute("PRAGMA page_size;")
                page_size = cursor.fetchone()[0]
                metrics['size_mb'] = round((page_count * page_size) / 1024 / 1024, 2)
                
                # Get table sizes
                tables = {
                    'invoices': 'sales_app_invoice',
                    'products': 'sales_app_product', 
                    'sales': 'sales_app_sale',
                    'admin_logs': 'sales_app_adminlog'
                }
                
                metrics['table_counts'] = {}
                for name, table in tables.items():
                    cursor.execute(f"SELECT COUNT(*) FROM {table};")
                    metrics['table_counts'][name] = cursor.fetchone()[0]
        
        # Query performance test
        start = time.time()
        Invoice.objects.select_related('user').prefetch_related('items').count()
        metrics['query_time_ms'] = round((time.time() - start) * 1000, 2)
        
    except Exception as e:
        metrics['error'] = str(e)
    
    return metrics


def get_cache_metrics():
    """Get cache performance metrics"""
    metrics = {}
    
    try:
        # Test cache performance
        test_key = 'performance_test'
        test_data = {'test': 'data', 'timestamp': timezone.now().isoformat()}
        
        # Write test
        start = time.time()
        cache.set(test_key, test_data, 60)
        write_time = (time.time() - start) * 1000
        
        # Read test
        start = time.time()
        retrieved = cache.get(test_key)
        read_time = (time.time() - start) * 1000
        
        # Clean up
        cache.delete(test_key)
        
        metrics['write_time_ms'] = round(write_time, 2)
        metrics['read_time_ms'] = round(read_time, 2)
        metrics['working'] = retrieved is not None
        
        # Cache hit ratio estimate (simplified)
        metrics['estimated_hit_ratio'] = 'N/A (LocMemCache doesn\'t provide stats)'
        
    except Exception as e:
        metrics['error'] = str(e)
    
    return metrics


def get_application_metrics():
    """Get application-level performance metrics"""
    metrics = {}
    
    try:
        today = timezone.now().date()
        
        # Recent activity metrics
        metrics['today_invoices'] = Invoice.objects.filter(date_of_sale=today).count()
        metrics['this_week_invoices'] = Invoice.objects.filter(
            date_of_sale__gte=today - timedelta(days=7)
        ).count()
        metrics['this_month_invoices'] = Invoice.objects.filter(
            date_of_sale__year=today.year,
            date_of_sale__month=today.month
        ).count()
        
        # Stock levels
        metrics['low_stock_count'] = Product.objects.filter(stock__lt=50).count()
        metrics['out_of_stock_count'] = Product.objects.filter(stock=0).count()
        
        # Payment status distribution
        metrics['payment_status'] = {}
        for status, _ in Invoice.PAYMENT_STATUS_CHOICES:
            metrics['payment_status'][status] = Invoice.objects.filter(
                payment_status=status
            ).count()
        
        # Average response times for key operations (simulated)
        test_times = {}
        
        # Test dashboard load time
        start = time.time()
        invoices = Invoice.objects.select_related('user').prefetch_related('items').filter(
            date_of_sale=today
        )[:25]
        list(invoices)  # Force evaluation
        test_times['dashboard_load_ms'] = round((time.time() - start) * 1000, 2)
        
        # Test product search
        start = time.time()
        products = Product.objects.filter(name__icontains='a').order_by('name')[:50]
        list(products)
        test_times['product_search_ms'] = round((time.time() - start) * 1000, 2)
        
        metrics['operation_times'] = test_times
        
    except Exception as e:
        metrics['error'] = str(e)
    
    return metrics


@login_required
@user_passes_test(is_manager)
@require_http_methods(["GET"])
def cache_status(request):
    """API endpoint to get cache status and statistics"""
    try:
        today = timezone.now().date()
        
        # Check what's currently cached
        cached_items = {}
        
        # Test if common cache keys exist
        cache_keys = [
            f'daily_sales_{today}',
            'low_stock_products_50',
            'top_products_7d_10',
            'top_products_30d_10',
            f'monthly_summary_{today.year}_{today.month}'
        ]
        
        for key in cache_keys:
            cached_items[key] = cache.get(key) is not None
        
        return JsonResponse({
            'status': 'success',
            'timestamp': timezone.now().isoformat(),
            'cache_backend': connection.settings_dict.get('CACHE', 'default'),
            'cached_items': cached_items,
            'cache_working': True
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=500)


@login_required
@user_passes_test(is_manager)
@require_http_methods(["POST"])
def clear_cache(request):
    """API endpoint to clear cache"""
    try:
        cache.clear()
        return JsonResponse({
            'status': 'success',
            'message': 'Cache cleared successfully',
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=500)


@login_required
@user_passes_test(is_manager)
@require_http_methods(["POST"])
def warmup_cache(request):
    """API endpoint to warm up cache"""
    try:
        today = timezone.now().date()
        
        # Pre-populate common cache entries
        SalesCache.get_daily_sales_summary(today)
        SalesCache.get_low_stock_products(50)
        SalesCache.get_top_products(days=7, limit=10)
        SalesCache.get_monthly_summary()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Cache warmed up successfully',
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=500)
