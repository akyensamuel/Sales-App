"""
Django signals to handle cache invalidation and other automated tasks
"""
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.core.cache import cache
from .models import Invoice, Product, Sale
from .cache_utils import SalesCache


@receiver(post_save, sender=Invoice)
def invoice_post_save(sender, instance, created, **kwargs):
    """Handle invoice creation/updates"""
    # Invalidate daily cache for the invoice date
    if instance.date_of_sale:
        SalesCache.invalidate_daily_cache(instance.date_of_sale)
    
    # Invalidate monthly cache
    if instance.date_of_sale:
        cache_key = f'monthly_summary_{instance.date_of_sale.year}_{instance.date_of_sale.month}'
        cache.delete(cache_key)
    
    # Invalidate sales-related caches
    SalesCache.invalidate_sales_cache()


@receiver(post_delete, sender=Invoice)
def invoice_post_delete(sender, instance, **kwargs):
    """Handle invoice deletion"""
    # Invalidate daily cache
    if instance.date_of_sale:
        SalesCache.invalidate_daily_cache(instance.date_of_sale)
    
    # Invalidate monthly cache
    if instance.date_of_sale:
        cache_key = f'monthly_summary_{instance.date_of_sale.year}_{instance.date_of_sale.month}'
        cache.delete(cache_key)
    
    # Invalidate sales-related caches
    SalesCache.invalidate_sales_cache()


@receiver(post_save, sender=Product)
def product_post_save(sender, instance, created, **kwargs):
    """Handle product creation/updates"""
    # Invalidate product-related caches
    SalesCache.invalidate_product_cache()
    
    # If stock changed, invalidate low stock cache
    if hasattr(instance, '_original_stock'):
        if instance._original_stock != instance.stock:
            SalesCache.invalidate_product_cache()


@receiver(pre_save, sender=Product)
def product_pre_save(sender, instance, **kwargs):
    """Store original stock value before save"""
    if instance.pk:
        try:
            original = Product.objects.get(pk=instance.pk)
            instance._original_stock = original.stock
        except Product.DoesNotExist:
            instance._original_stock = None
    else:
        instance._original_stock = None


@receiver(post_delete, sender=Product)
def product_post_delete(sender, instance, **kwargs):
    """Handle product deletion"""
    SalesCache.invalidate_product_cache()


@receiver(post_save, sender=Sale)
def sale_post_save(sender, instance, created, **kwargs):
    """Handle sale creation/updates"""
    # Invalidate sales-related caches
    SalesCache.invalidate_sales_cache()
    
    # Invalidate daily cache for the related invoice
    if instance.invoice and instance.invoice.date_of_sale:
        SalesCache.invalidate_daily_cache(instance.invoice.date_of_sale)


@receiver(post_delete, sender=Sale)
def sale_post_delete(sender, instance, **kwargs):
    """Handle sale deletion"""
    # Invalidate sales-related caches
    SalesCache.invalidate_sales_cache()
    
    # Invalidate daily cache for the related invoice
    if instance.invoice and instance.invoice.date_of_sale:
        SalesCache.invalidate_daily_cache(instance.invoice.date_of_sale)
