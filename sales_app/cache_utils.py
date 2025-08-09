"""
Caching utilities for sales app to improve performance
"""
from django.core.cache import cache
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Invoice, Product, Sale, AdminLog


class SalesCache:
    """Centralized caching for sales data"""
    
    # Cache timeout settings (in seconds)
    CACHE_TIMEOUT_SHORT = 300   # 5 minutes
    CACHE_TIMEOUT_MEDIUM = 900  # 15 minutes
    CACHE_TIMEOUT_LONG = 3600   # 1 hour
    
    @classmethod
    def get_daily_sales_summary(cls, date=None):
        """Get cached daily sales summary"""
        if date is None:
            date = timezone.now().date()
        
        cache_key = f'daily_sales_{date}'
        cached_data = cache.get(cache_key)
        
        if cached_data is None:
            # Calculate and cache the data
            invoices = Invoice.objects.filter(date_of_sale=date)
            summary = {
                'total_sales': invoices.aggregate(Sum('total'))['total__sum'] or 0,
                'total_invoices': invoices.count(),
                'paid_invoices': invoices.filter(payment_status='paid').count(),
                'unpaid_invoices': invoices.filter(payment_status='unpaid').count(),
                'partial_invoices': invoices.filter(payment_status='partial').count(),
            }
            cache.set(cache_key, summary, cls.CACHE_TIMEOUT_MEDIUM)
            cached_data = summary
        
        return cached_data
    
    @classmethod
    def get_low_stock_products(cls, threshold=50):
        """Get cached list of low stock products"""
        cache_key = f'low_stock_products_{threshold}'
        cached_data = cache.get(cache_key)
        
        if cached_data is None:
            products = list(Product.objects.filter(
                stock__lt=threshold
            ).order_by('stock', 'name').values('id', 'name', 'stock'))
            
            cache.set(cache_key, products, cls.CACHE_TIMEOUT_SHORT)
            cached_data = products
        
        return cached_data
    
    @classmethod
    def get_top_products(cls, days=30, limit=10):
        """Get cached list of top selling products"""
        cache_key = f'top_products_{days}d_{limit}'
        cached_data = cache.get(cache_key)
        
        if cached_data is None:
            start_date = timezone.now().date() - timedelta(days=days)
            
            # Get top products by quantity sold
            top_products = Sale.objects.filter(
                invoice__date_of_sale__gte=start_date
            ).values('item').annotate(
                total_quantity=Sum('quantity'),
                total_revenue=Sum('total_price')
            ).order_by('-total_quantity')[:limit]
            
            cached_data = list(top_products)
            cache.set(cache_key, cached_data, cls.CACHE_TIMEOUT_LONG)
        
        return cached_data
    
    @classmethod
    def get_monthly_summary(cls, year=None, month=None):
        """Get cached monthly sales summary"""
        if year is None:
            year = timezone.now().year
        if month is None:
            month = timezone.now().month
            
        cache_key = f'monthly_summary_{year}_{month}'
        cached_data = cache.get(cache_key)
        
        if cached_data is None:
            invoices = Invoice.objects.filter(
                date_of_sale__year=year,
                date_of_sale__month=month
            )
            
            summary = {
                'total_revenue': invoices.aggregate(Sum('total'))['total__sum'] or 0,
                'total_invoices': invoices.count(),
                'paid_amount': invoices.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0,
                'outstanding_amount': (
                    invoices.aggregate(Sum('total'))['total__sum'] or 0
                ) - (
                    invoices.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
                ),
                'payment_status_breakdown': {
                    status: invoices.filter(payment_status=status).count()
                    for status, _ in Invoice.PAYMENT_STATUS_CHOICES
                }
            }
            
            # Cache for longer if it's a past month
            current_month = timezone.now().replace(day=1).date()
            target_month = datetime(year, month, 1).date()
            
            timeout = cls.CACHE_TIMEOUT_LONG if target_month < current_month else cls.CACHE_TIMEOUT_MEDIUM
            cache.set(cache_key, summary, timeout)
            cached_data = summary
        
        return cached_data
    
    @classmethod
    def invalidate_daily_cache(cls, date=None):
        """Invalidate daily cache when new sales are made"""
        if date is None:
            date = timezone.now().date()
        
        cache_key = f'daily_sales_{date}'
        cache.delete(cache_key)
    
    @classmethod
    def invalidate_product_cache(cls):
        """Invalidate product-related caches"""
        # This could be improved with a more sophisticated cache key pattern
        cache.delete_many([
            'low_stock_products_50',
            'low_stock_products_25',
            'low_stock_products_10',
        ])
    
    @classmethod
    def invalidate_sales_cache(cls):
        """Invalidate sales-related caches"""
        # Clear top products cache
        for days in [7, 30, 90]:
            for limit in [5, 10, 20]:
                cache.delete(f'top_products_{days}d_{limit}')
        
        # Clear today's daily summary
        cls.invalidate_daily_cache()


def cache_expensive_query(cache_key, query_func, timeout=SalesCache.CACHE_TIMEOUT_MEDIUM):
    """
    Generic function to cache expensive database queries
    
    Usage:
        result = cache_expensive_query(
            'my_expensive_query',
            lambda: SomeModel.objects.complex_query(),
            timeout=900
        )
    """
    cached_result = cache.get(cache_key)
    
    if cached_result is None:
        cached_result = query_func()
        cache.set(cache_key, cached_result, timeout)
    
    return cached_result


def get_dashboard_stats(user=None):
    """Get optimized dashboard statistics"""
    today = timezone.now().date()
    
    # Use caching for expensive aggregations
    stats = cache_expensive_query(
        f'dashboard_stats_{today}_{user.id if user else "all"}',
        lambda: {
            'today_sales': SalesCache.get_daily_sales_summary(today),
            'low_stock_count': len(SalesCache.get_low_stock_products()),
            'top_products': SalesCache.get_top_products(days=7, limit=5),
            'monthly_summary': SalesCache.get_monthly_summary(),
        },
        timeout=SalesCache.CACHE_TIMEOUT_SHORT
    )
    
    return stats
