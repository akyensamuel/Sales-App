"""
Analytics utilities for product and sales person performance tracking
"""
from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone
from django.contrib.auth.models import User, Group
from datetime import datetime, timedelta
from decimal import Decimal

from sales_app.models import Invoice, Sale, Product
from .models import ProductPerformance, SalesPersonPerformance


class AnalyticsEngine:
    """Core analytics engine for performance calculations"""
    
    @staticmethod
    def get_date_ranges():
        """Get common date ranges for analytics"""
        today = timezone.now().date()
        return {
            'today': (today, today),
            'this_week': (today - timedelta(days=today.weekday()), today),
            'this_month': (today.replace(day=1), today),
            'last_month': (
                (today.replace(day=1) - timedelta(days=1)).replace(day=1),
                today.replace(day=1) - timedelta(days=1)
            ),
            'this_quarter': (
                today.replace(month=((today.month-1)//3)*3+1, day=1),
                today
            ),
            'this_year': (today.replace(month=1, day=1), today),
            'last_30_days': (today - timedelta(days=30), today),
            'last_90_days': (today - timedelta(days=90), today),
        }
    
    @staticmethod
    def calculate_product_performance(start_date, end_date, update_db=True):
        """Calculate product performance metrics for a given period"""
        # Get all sales within the date range
        sales_data = Sale.objects.filter(
            invoice__date_of_sale__range=[start_date, end_date]
        ).values('item').annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('total_price'),
            avg_price=Avg('unit_price'),
            sale_count=Count('id'),
            invoice_count=Count('invoice', distinct=True)
        ).order_by('-total_revenue')
        
        performance_data = []
        
        for item_data in sales_data:
            product_name = item_data['item']
            if not product_name:
                continue
                
            # Calculate profit (simplified - using current product cost if available)
            try:
                product = Product.objects.get(name=product_name)
                # Assume 30% cost margin for profit calculation if no cost field
                estimated_cost_per_unit = float(product.price) * 0.7 if product.price else 0
                total_cost = estimated_cost_per_unit * item_data['total_quantity']
                total_profit = float(item_data['total_revenue']) - total_cost
            except Product.DoesNotExist:
                total_profit = float(item_data['total_revenue']) * 0.3  # 30% profit margin estimate
            
            perf_data = {
                'product_name': product_name,
                'period_start': start_date,
                'period_end': end_date,
                'total_quantity_sold': item_data['total_quantity'] or 0,
                'total_revenue': item_data['total_revenue'] or 0,
                'total_profit': Decimal(str(total_profit)),
                'average_selling_price': item_data['avg_price'] or 0,
                'number_of_sales': item_data['sale_count'] or 0,
            }
            
            performance_data.append(perf_data)
            
            # Update database if requested
            if update_db:
                ProductPerformance.objects.update_or_create(
                    product_name=product_name,
                    period_start=start_date,
                    period_end=end_date,
                    defaults=perf_data
                )
        
        return performance_data
    
    @staticmethod
    def calculate_salesperson_performance(start_date, end_date, update_db=True):
        """Calculate sales person performance metrics for a given period"""
        # Get managers and cashiers
        managers_group = Group.objects.get(name='Managers')
        cashiers_group = Group.objects.get(name='Cashiers')
        
        sales_users = User.objects.filter(
            Q(groups=managers_group) | Q(groups=cashiers_group)
        ).distinct()
        
        performance_data = []
        
        for user in sales_users:
            # Get user's invoices in the period
            user_invoices = Invoice.objects.filter(
                user=user,
                date_of_sale__range=[start_date, end_date]
            )
            
            # Calculate metrics
            total_sales = user_invoices.aggregate(
                total_amount=Sum('total'),
                total_paid=Sum('amount_paid'),
                invoice_count=Count('id')
            )
            
            # Get total items sold
            total_items = Sale.objects.filter(
                invoice__in=user_invoices
            ).aggregate(
                item_count=Sum('quantity')
            )['item_count'] or 0
            
            # Calculate averages
            total_amount = total_sales['total_amount'] or 0
            invoice_count = total_sales['invoice_count'] or 0
            avg_sale_value = total_amount / invoice_count if invoice_count > 0 else 0
            
            # Calculate conversion rate (paid vs total)
            paid_invoices = user_invoices.filter(payment_status='paid').count()
            conversion_rate = (paid_invoices / invoice_count * 100) if invoice_count > 0 else 0
            
            # Calculate commission (example: 2% of total sales)
            commission = total_amount * Decimal('0.02')
            
            perf_data = {
                'user': user,
                'period_start': start_date,
                'period_end': end_date,
                'total_sales_amount': total_amount,
                'total_invoices': invoice_count,
                'total_items_sold': total_items,
                'average_sale_value': Decimal(str(avg_sale_value)),
                'conversion_rate': Decimal(str(conversion_rate)),
                'commission_earned': commission,
            }
            
            performance_data.append(perf_data)
            
            # Update database if requested
            if update_db:
                perf_obj, created = SalesPersonPerformance.objects.update_or_create(
                    user=user,
                    period_start=start_date,
                    period_end=end_date,
                    defaults=perf_data
                )
        
        return sorted(performance_data, key=lambda x: x['total_sales_amount'], reverse=True)
    
    @staticmethod
    def get_top_products(period='this_month', limit=10):
        """Get top performing products"""
        date_ranges = AnalyticsEngine.get_date_ranges()
        start_date, end_date = date_ranges.get(period, date_ranges['this_month'])
        
        return ProductPerformance.objects.filter(
            period_start=start_date,
            period_end=end_date
        ).order_by('-total_revenue')[:limit]
    
    @staticmethod
    def get_top_salespeople(period='this_month', limit=10):
        """Get top performing sales people"""
        date_ranges = AnalyticsEngine.get_date_ranges()
        start_date, end_date = date_ranges.get(period, date_ranges['this_month'])
        
        return SalesPersonPerformance.objects.filter(
            period_start=start_date,
            period_end=end_date
        ).order_by('-total_sales_amount')[:limit]
    
    @staticmethod
    def get_product_trends(product_name, months=6):
        """Get product performance trends over time"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=months * 30)
        
        return ProductPerformance.objects.filter(
            product_name=product_name,
            period_start__gte=start_date
        ).order_by('period_start')
    
    @staticmethod
    def get_salesperson_trends(user_id, months=6):
        """Get salesperson performance trends over time"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=months * 30)
        
        return SalesPersonPerformance.objects.filter(
            user_id=user_id,
            period_start__gte=start_date
        ).order_by('period_start')
    
    @staticmethod
    def generate_analytics_summary(period='this_month'):
        """Generate comprehensive analytics summary"""
        date_ranges = AnalyticsEngine.get_date_ranges()
        start_date, end_date = date_ranges.get(period, date_ranges['this_month'])
        
        # Update performance data
        product_data = AnalyticsEngine.calculate_product_performance(start_date, end_date)
        salesperson_data = AnalyticsEngine.calculate_salesperson_performance(start_date, end_date)
        
        # Get summaries
        total_revenue = sum(item['total_revenue'] for item in product_data)
        total_profit = sum(item['total_profit'] for item in product_data)
        total_items_sold = sum(item['total_quantity_sold'] for item in product_data)
        
        total_sales_by_people = sum(item['total_sales_amount'] for item in salesperson_data)
        total_invoices = sum(item['total_invoices'] for item in salesperson_data)
        
        return {
            'period': period,
            'date_range': (start_date, end_date),
            'product_metrics': {
                'total_revenue': total_revenue,
                'total_profit': total_profit,
                'total_items_sold': total_items_sold,
                'profit_margin': (total_profit / total_revenue * 100) if total_revenue > 0 else 0,
                'top_products': product_data[:5],
                'total_products': len(product_data),
            },
            'salesperson_metrics': {
                'total_sales_amount': total_sales_by_people,
                'total_invoices': total_invoices,
                'average_sale_value': total_sales_by_people / total_invoices if total_invoices > 0 else 0,
                'top_performers': salesperson_data[:5],
                'total_salespeople': len(salesperson_data),
            }
        }
    
    @staticmethod
    def get_product_performance(period='this_month'):
        """Get product performance data for a given period"""
        date_ranges = AnalyticsEngine.get_date_ranges()
        start_date, end_date = date_ranges.get(period, date_ranges['this_month'])
        return AnalyticsEngine.calculate_product_performance(start_date, end_date)
    
    @staticmethod
    def get_salesperson_performance(period='this_month'):
        """Get salesperson performance data for a given period"""
        date_ranges = AnalyticsEngine.get_date_ranges()
        start_date, end_date = date_ranges.get(period, date_ranges['this_month'])
        return AnalyticsEngine.calculate_salesperson_performance(start_date, end_date)
