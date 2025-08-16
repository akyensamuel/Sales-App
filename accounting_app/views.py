from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Q, Count
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import datetime, timedelta
from decimal import Decimal
import json
from calendar import monthrange

from .models import (
    FinancialForecast, Expense, ExpenseCategory, ProfitLossSnapshot,
    TaxSettings, AccountingAuditLog, ProductPerformance, SalesPersonPerformance,
    CashDepartmentPerformance, DepartmentFinancialSnapshot, CashServicePerformance
)
from sales_app.models import Invoice, Sale, CashInvoice, CashSale
from .analytics import AnalyticsEngine

def is_admin(user):
    return user.is_authenticated and user.groups.filter(name='Admin').exists()

def log_audit_action(user, action, model_name, object_id="", details="", ip_address=None):
    """Log accounting actions for audit trail"""
    AccountingAuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=str(object_id),
        details=details,
        ip_address=ip_address
    )

def accounting_login(request):
    if request.user.is_authenticated:
        if is_admin(request.user):
            return redirect('accounting_dashboard')
        return render(request, 'accounting_app/login.html', {'error': 'You do not have permission to access the accounting app.'})

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None and is_admin(user):
            login(request, user)
            log_audit_action(user, 'view', 'AccountingDashboard', details='User logged into accounting system')
            return redirect('accounting_dashboard')
        else:
            return render(request, 'accounting_app/login.html', {'error': 'Invalid credentials or insufficient permissions.'})
    return render(request, 'accounting_app/login.html')

@login_required
@user_passes_test(is_admin)
def accounting_dashboard(request):
    """Main accounting dashboard with financial overview including cash department"""
    today = timezone.now().date()
    current_month = today.replace(day=1)
    
    # Regular Sales Revenue metrics
    regular_monthly_revenue = Invoice.objects.filter(
        date_of_sale__year=today.year,
        date_of_sale__month=today.month
    ).aggregate(total=Sum('total'))['total'] or 0
    
    # Cash Department Revenue metrics
    cash_monthly_revenue = CashInvoice.objects.filter(
        date_of_sale__year=today.year,
        date_of_sale__month=today.month
    ).aggregate(total=Sum('total'))['total'] or 0
    
    # Combined monthly revenue
    monthly_revenue = regular_monthly_revenue + cash_monthly_revenue
    
    # Expense metrics
    monthly_expenses = Expense.objects.filter(
        date__year=today.year,
        date__month=today.month
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Outstanding payments (only regular invoices, cash is always paid)
    outstanding_invoices = Invoice.objects.filter(
        payment_status__in=['unpaid', 'partial', 'overdue']
    ).aggregate(
        count=Count('id'),
        total=Sum('total'),
        paid=Sum('amount_paid')
    )
    
    # Calculate outstanding amount properly handling None values
    total_invoice_amount = outstanding_invoices['total'] or 0
    total_paid_amount = outstanding_invoices['paid'] or 0
    outstanding_amount = total_invoice_amount - total_paid_amount
    
    # Recent expenses
    recent_expenses = Expense.objects.select_related('category').order_by('-created_at')[:5]
    
    # P&L for current month
    net_profit = monthly_revenue - monthly_expenses
    profit_margin = (net_profit / monthly_revenue * 100) if monthly_revenue > 0 else 0
    
    # Department breakdown for current month
    cash_department_percentage = (cash_monthly_revenue / monthly_revenue * 100) if monthly_revenue > 0 else 0
    regular_department_percentage = (regular_monthly_revenue / monthly_revenue * 100) if monthly_revenue > 0 else 0
    
    # Cash department specific metrics
    cash_invoices_count = CashInvoice.objects.filter(
        date_of_sale__year=today.year,
        date_of_sale__month=today.month
    ).count()
    
    cash_transactions_count = CashSale.objects.filter(
        invoice__date_of_sale__year=today.year,
        invoice__date_of_sale__month=today.month
    ).count()
    
    # Get or create monthly snapshot with combined data
    snapshot, created = DepartmentFinancialSnapshot.objects.get_or_create(
        period_type='monthly',
        period_start=current_month,
        period_end=current_month.replace(day=monthrange(current_month.year, current_month.month)[1]),
        defaults={
            'regular_revenue': regular_monthly_revenue,
            'cash_revenue': cash_monthly_revenue,
            'total_revenue': monthly_revenue,
            'total_expenses': monthly_expenses,
            'net_profit': net_profit,
            'regular_outstanding_amount': outstanding_amount,
            'cash_invoices_count': cash_invoices_count,
            'cash_transactions_count': cash_transactions_count,
        }
    )
    
    if not created:
        # Update existing snapshot
        snapshot.regular_revenue = regular_monthly_revenue
        snapshot.cash_revenue = cash_monthly_revenue
        snapshot.total_revenue = monthly_revenue
        snapshot.total_expenses = monthly_expenses
        snapshot.net_profit = net_profit
        snapshot.regular_outstanding_amount = outstanding_amount
        snapshot.cash_invoices_count = cash_invoices_count
        snapshot.cash_transactions_count = cash_transactions_count
        snapshot.save()

    context = {
        'monthly_revenue': monthly_revenue,
        'regular_monthly_revenue': regular_monthly_revenue,
        'cash_monthly_revenue': cash_monthly_revenue,
        'monthly_expenses': monthly_expenses,
        'net_profit': net_profit,
        'profit_margin': profit_margin,
        'outstanding_amount': outstanding_amount,
        'outstanding_count': outstanding_invoices['count'] or 0,
        'recent_expenses': recent_expenses,
        'current_month': current_month.strftime('%B %Y'),
        'cash_department_percentage': cash_department_percentage,
        'regular_department_percentage': regular_department_percentage,
        'cash_invoices_count': cash_invoices_count,
        'cash_transactions_count': cash_transactions_count,
    }
    
    log_audit_action(request.user, 'view', 'AccountingDashboard', details='Accessed main dashboard with cash department data')
    return render(request, 'accounting_app/dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def expense_list(request):
    """List all expenses with filtering"""
    expenses = Expense.objects.select_related('category', 'created_by').order_by('-date')
    
    # Apply filters
    category_filter = request.GET.get('category')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    search = request.GET.get('search')
    
    if category_filter:
        expenses = expenses.filter(category_id=category_filter)
    
    if date_from:
        expenses = expenses.filter(date__gte=date_from)
    
    if date_to:
        expenses = expenses.filter(date__lte=date_to)
    
    if search:
        expenses = expenses.filter(
            Q(description__icontains=search) |
            Q(vendor__icontains=search) |
            Q(notes__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(expenses, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    categories = ExpenseCategory.objects.all()
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'current_filters': {
            'category': category_filter,
            'date_from': date_from,
            'date_to': date_to,
            'search': search,
        }
    }
    
    return render(request, 'accounting_app/expense_list.html', context)

@login_required
@user_passes_test(is_admin)
def expense_create(request):
    """Create new expense"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Get or create category
                category_name = request.POST.get('category_name', '').strip()
                category_id = request.POST.get('category')
                
                if category_name and not category_id:
                    category, created = ExpenseCategory.objects.get_or_create(
                        name=category_name,
                        defaults={'description': f'Auto-created category: {category_name}'}
                    )
                else:
                    category = get_object_or_404(ExpenseCategory, id=category_id)
                
                expense = Expense.objects.create(
                    amount=Decimal(request.POST['amount']),
                    date=request.POST['date'],
                    category=category,
                    description=request.POST['description'],
                    notes=request.POST.get('notes', ''),
                    payment_method=request.POST.get('payment_method', 'cash'),
                    vendor=request.POST.get('vendor', ''),
                    reference_number=request.POST.get('reference_number', ''),
                    is_recurring=request.POST.get('is_recurring') == 'on',
                    created_by=request.user
                )
                
                log_audit_action(
                    request.user, 'create', 'Expense', expense.id,
                    f'Created expense: {expense.description} - ₵{expense.amount}'
                )
                
                messages.success(request, 'Expense created successfully!')
                return redirect('expense_list')
                
        except Exception as e:
            messages.error(request, f'Error creating expense: {str(e)}')
    
    categories = ExpenseCategory.objects.all()
    return render(request, 'accounting_app/expense_form.html', {'categories': categories})

@login_required
@user_passes_test(is_admin)
def expense_edit(request, expense_id):
    """Edit existing expense"""
    expense = get_object_or_404(Expense, id=expense_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                old_amount = expense.amount
                
                expense.amount = Decimal(request.POST['amount'])
                expense.date = request.POST['date']
                expense.category_id = request.POST['category']
                expense.description = request.POST['description']
                expense.notes = request.POST.get('notes', '')
                expense.payment_method = request.POST.get('payment_method', 'cash')
                expense.vendor = request.POST.get('vendor', '')
                expense.reference_number = request.POST.get('reference_number', '')
                expense.is_recurring = request.POST.get('is_recurring') == 'on'
                expense.save()
                
                log_audit_action(
                    request.user, 'update', 'Expense', expense.id,
                    f'Updated expense: {expense.description} - Amount changed from ₵{old_amount} to ₵{expense.amount}'
                )
                
                messages.success(request, 'Expense updated successfully!')
                return redirect('expense_list')
                
        except Exception as e:
            messages.error(request, f'Error updating expense: {str(e)}')
    
    categories = ExpenseCategory.objects.all()
    return render(request, 'accounting_app/expense_form.html', {
        'expense': expense,
        'categories': categories,
        'is_edit': True
    })

@login_required
@user_passes_test(is_admin)
def expense_delete(request, expense_id):
    """Delete expense"""
    expense = get_object_or_404(Expense, id=expense_id)
    
    if request.method == 'POST':
        log_audit_action(
            request.user, 'delete', 'Expense', expense.id,
            f'Deleted expense: {expense.description} - ₵{expense.amount}'
        )
        
        expense.delete()
        messages.success(request, 'Expense deleted successfully!')
        return redirect('expense_list')
    
    return render(request, 'accounting_app/expense_confirm_delete.html', {'expense': expense})

@login_required
@user_passes_test(is_admin)
def profit_loss_report(request):
    """Generate profit & loss report"""
    year = int(request.GET.get('year', timezone.now().year))
    month = request.GET.get('month')
    
    if month:
        month = int(month)
        start_date = datetime(year, month, 1).date()
        end_date = datetime(year, month, monthrange(year, month)[1]).date()
        period_title = f"{start_date.strftime('%B %Y')}"
    else:
        start_date = datetime(year, 1, 1).date()
        end_date = datetime(year, 12, 31).date()
        period_title = f"Year {year}"
    
    # Calculate revenue
    revenue_data = Invoice.objects.filter(
        date_of_sale__range=[start_date, end_date]
    ).aggregate(
        total_revenue=Sum('total'),
        paid_revenue=Sum('amount_paid'),
        invoice_count=Count('id')
    )
    
    # Calculate expenses by category
    expense_data = Expense.objects.filter(
        date__range=[start_date, end_date]
    ).values('category__name').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    total_expenses = sum(item['total'] for item in expense_data)
    total_revenue = revenue_data['total_revenue'] or 0
    net_profit = total_revenue - total_expenses
    profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0
    
    # Add percentage calculation to expense data
    expense_data_with_percentage = []
    for expense in expense_data:
        percentage = (expense['total'] / total_expenses * 100) if total_expenses > 0 else 0
        expense_data_with_percentage.append({
            'category__name': expense['category__name'],
            'total': float(expense['total']),  # Convert to float for JavaScript
            'count': expense['count'],
            'percentage': percentage
        })
    
    context = {
        'period_title': period_title,
        'start_date': start_date,
        'end_date': end_date,
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
        'profit_margin': profit_margin,
        'expense_data': expense_data_with_percentage,
        'revenue_data': revenue_data,
        'selected_year': year,
        'selected_month': month,
        'years': range(2020, timezone.now().year + 2),
        'months': [
            (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
            (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
            (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
        ]
    }
    
    log_audit_action(request.user, 'view', 'ProfitLossReport', details=f'Generated P&L report for {period_title}')
    return render(request, 'accounting_app/profit_loss_report.html', context)

@login_required
@user_passes_test(is_admin)
def revenue_tracking(request):
    """Revenue tracking and analysis"""
    # Get monthly revenue for the last 12 months
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=365)
    
    monthly_data = []
    for i in range(12):
        month_start = (start_date.replace(day=1) + timedelta(days=32*i)).replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        if month_end > end_date:
            month_end = end_date
        
        revenue = Invoice.objects.filter(
            date_of_sale__range=[month_start, month_end]
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')
        
        monthly_data.append({
            'month': month_start.strftime('%B %Y'),
            'revenue': float(revenue),  # Convert to float for JavaScript
            'month_start': month_start,
            'month_end': month_end
        })
    
    # Outstanding invoices analysis
    outstanding_invoices = Invoice.objects.filter(
        payment_status__in=['unpaid', 'partial', 'overdue']
    ).select_related('user').order_by('-date_of_sale')
    
    # Payment status breakdown
    status_breakdown = Invoice.objects.values('payment_status').annotate(
        count=Count('id'),
        total=Sum('total')
    ).order_by('payment_status')
    
    # Calculate total revenue for 12 months
    total_12_month_revenue = sum(month['revenue'] for month in monthly_data)
    
    # Check if user can edit invoices (either Admin, Manager, or superuser)
    can_edit_invoices = (
        request.user.is_superuser or 
        request.user.groups.filter(name='Admin').exists() or 
        request.user.groups.filter(name='Managers').exists()
    )
    
    context = {
        'monthly_data': monthly_data,
        'total_12_month_revenue': total_12_month_revenue,
        'outstanding_invoices': outstanding_invoices,
        'status_breakdown': status_breakdown,
        'can_edit_invoices': can_edit_invoices,
    }
    
    return render(request, 'accounting_app/revenue_tracking.html', context)

# Legacy forecast dashboard for compatibility
def forecast_dashboard(request):
    return redirect('accounting_dashboard')


# === ANALYTICS VIEWS ===

@login_required
@user_passes_test(is_admin)
def analytics_dashboard(request):
    """Main analytics dashboard showing product and salesperson performance"""
    period = request.GET.get('period', 'this_month')
    
    # Generate analytics summary
    summary = AnalyticsEngine.generate_analytics_summary(period)
    
    # Get date ranges for the dropdown
    date_ranges = AnalyticsEngine.get_date_ranges()
    
    log_audit_action(
        request.user, 
        'view', 
        'AnalyticsDashboard', 
        details=f'Viewed analytics dashboard for period: {period}'
    )
    
    context = {
        'summary': summary,
        'period': period,
        'date_ranges': date_ranges,
        'page_title': 'Analytics Dashboard'
    }
    
    return render(request, 'accounting_app/analytics_dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def product_performance(request):
    """Detailed product performance analysis"""
    period = request.GET.get('period', 'this_month')
    product_filter = request.GET.get('product', '')
    
    date_ranges = AnalyticsEngine.get_date_ranges()
    start_date, end_date = date_ranges.get(period, date_ranges['this_month'])
    
    # Get product performance data
    product_data = AnalyticsEngine.calculate_product_performance(start_date, end_date, update_db=True)
    
    # Filter by product if specified
    if product_filter:
        product_data = [p for p in product_data if product_filter.lower() in p['product_name'].lower()]
    
    # Pagination
    paginator = Paginator(product_data, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get top products for quick stats
    top_products = product_data[:5] if product_data else []
    
    # Calculate totals
    total_revenue = sum(item['total_revenue'] for item in product_data)
    total_profit = sum(item['total_profit'] for item in product_data)
    total_items_sold = sum(item['total_quantity_sold'] for item in product_data)
    
    log_audit_action(
        request.user,
        'view',
        'ProductPerformance',
        details=f'Viewed product performance for period: {period}'
    )
    
    context = {
        'products': page_obj,
        'top_products': top_products,
        'period': period,
        'product_filter': product_filter,
        'date_ranges': date_ranges,
        'total_revenue': total_revenue,
        'total_profit': total_profit,
        'total_items_sold': total_items_sold,
        'profit_margin': (total_profit / total_revenue * 100) if total_revenue > 0 else 0,
        'page_title': 'Product Performance',
        # Template-expected variables
        'total_products': len(product_data),
        'total_units_sold': total_items_sold,
        'avg_margin': (total_profit / total_revenue * 100) if total_revenue > 0 else 0,
    }
    
    return render(request, 'accounting_app/product_performance.html', context)


@login_required
@user_passes_test(is_admin)
def salesperson_performance(request):
    """Detailed salesperson performance analysis"""
    period = request.GET.get('period', 'this_month')
    user_filter = request.GET.get('user', '')
    
    date_ranges = AnalyticsEngine.get_date_ranges()
    start_date, end_date = date_ranges.get(period, date_ranges['this_month'])
    
    # Get salesperson performance data
    performance_data = AnalyticsEngine.calculate_salesperson_performance(start_date, end_date, update_db=True)
    
    # Filter by user if specified
    if user_filter:
        performance_data = [p for p in performance_data if user_filter.lower() in (p['user'].get_full_name() or p['user'].username).lower()]
    
    # Pagination
    paginator = Paginator(performance_data, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get top performers for quick stats
    top_performers = performance_data[:5] if performance_data else []
    
    # Calculate totals
    total_sales = sum(item['total_sales_amount'] for item in performance_data)
    total_invoices = sum(item['total_invoices'] for item in performance_data)
    total_commission = sum(item['commission_earned'] for item in performance_data)
    
    log_audit_action(
        request.user,
        'view',
        'SalespersonPerformance',
        details=f'Viewed salesperson performance for period: {period}'
    )
    
    context = {
        'salespeople': page_obj,
        'top_performers': top_performers,
        'period': period,
        'user_filter': user_filter,
        'date_ranges': date_ranges,
        'total_sales': total_sales,
        'total_invoices': total_invoices,
        'total_commission': total_commission,
        'average_sale_value': total_sales / total_invoices if total_invoices > 0 else 0,
        'page_title': 'Salesperson Performance',
        # Template-expected variables
        'staff_performance': page_obj,
        'total_staff': len(performance_data),
    }
    
    return render(request, 'accounting_app/salesperson_performance.html', context)


@login_required
@user_passes_test(is_admin)
def product_trends(request, product_name):
    """Show product performance trends over time"""
    months = int(request.GET.get('months', 6))
    
    # Get trend data
    trends = AnalyticsEngine.get_product_trends(product_name, months)
    
    # Prepare chart data
    chart_data = {
        'labels': [trend.period_start.strftime('%b %Y') for trend in trends],
        'revenue': [float(trend.total_revenue) for trend in trends],
        'quantity': [trend.total_quantity_sold for trend in trends],
        'profit': [float(trend.total_profit) for trend in trends]
    }
    
    log_audit_action(
        request.user,
        'view',
        'ProductTrends',
        object_id=product_name,
        details=f'Viewed trends for product: {product_name}'
    )
    
    context = {
        'product_name': product_name,
        'trends': trends,
        'chart_data': json.dumps(chart_data),
        'months': months,
        'page_title': f'Trends - {product_name}'
    }
    
    return render(request, 'accounting_app/product_trends.html', context)


@login_required
@user_passes_test(is_admin)
def salesperson_trends(request, user_id):
    """Show salesperson performance trends over time"""
    months = int(request.GET.get('months', 6))
    
    # Get user and trend data
    from django.contrib.auth.models import User
    user = get_object_or_404(User, id=user_id)
    trends = AnalyticsEngine.get_salesperson_trends(user_id, months)
    
    # Prepare chart data
    chart_data = {
        'labels': [trend.period_start.strftime('%b %Y') for trend in trends],
        'sales': [float(trend.total_sales_amount) for trend in trends],
        'invoices': [trend.total_invoices for trend in trends],
        'conversion': [float(trend.conversion_rate) for trend in trends]
    }
    
    log_audit_action(
        request.user,
        'view',
        'SalespersonTrends',
        object_id=str(user_id),
        details=f'Viewed trends for user: {user.username}'
    )
    
    context = {
        'salesperson': user,
        'trends': trends,
        'chart_data': json.dumps(chart_data),
        'months': months,
        'page_title': f'Trends - {user.get_full_name() or user.username}'
    }
    
    return render(request, 'accounting_app/salesperson_trends.html', context)


@login_required
@user_passes_test(is_admin)
def analytics_api(request):
    """API endpoint for analytics data (for AJAX requests)"""
    period = request.GET.get('period', 'this_month')
    data_type = request.GET.get('type', 'summary')
    
    try:
        if data_type == 'summary':
            data = AnalyticsEngine.generate_analytics_summary(period)
        elif data_type == 'products':
            date_ranges = AnalyticsEngine.get_date_ranges()
            start_date, end_date = date_ranges.get(period, date_ranges['this_month'])
            data = AnalyticsEngine.calculate_product_performance(start_date, end_date, update_db=False)
        elif data_type == 'cash_services':
            date_ranges = AnalyticsEngine.get_date_ranges()
            start_date, end_date = date_ranges.get(period, date_ranges['this_month'])
            data = AnalyticsEngine.calculate_cash_service_performance(start_date, end_date, update_db=False)
        else:
            data = {'error': 'Invalid data type'}
        
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_admin)
def weekly_summary(request):
    """Weekly summary view across all departments"""
    try:
        weekly_data = AnalyticsEngine.get_weekly_summary()
        
        weekly_snapshot = weekly_data['weekly_snapshot']
        daily_summaries = weekly_data['daily_summaries']
        
        # Calculate week-over-week comparison
        previous_week_start = weekly_data['week_start'] - timedelta(days=7)
        previous_week_end = weekly_data['week_end'] - timedelta(days=7)
        
        try:
            previous_week_snapshot = DepartmentFinancialSnapshot.objects.get(
                period_type='weekly',
                period_start=previous_week_start,
                period_end=previous_week_end
            )
            
            # Calculate percentage changes
            revenue_change = 0
            if previous_week_snapshot.total_revenue > 0:
                revenue_change = ((weekly_snapshot.total_revenue - previous_week_snapshot.total_revenue) / 
                                previous_week_snapshot.total_revenue) * 100
            
            profit_change = 0
            if previous_week_snapshot.net_profit != 0:
                profit_change = ((weekly_snapshot.net_profit - previous_week_snapshot.net_profit) / 
                               abs(previous_week_snapshot.net_profit)) * 100
            
        except DepartmentFinancialSnapshot.DoesNotExist:
            previous_week_snapshot = None
            revenue_change = 0
            profit_change = 0
        
        # Get top performing products for the week
        top_products = AnalyticsEngine.calculate_product_performance(
            weekly_data['week_start'], 
            weekly_data['week_end'], 
            update_db=False
        )[:5]
        
        # Get top performing cash services for the week
        top_cash_services = AnalyticsEngine.calculate_cash_service_performance(
            weekly_data['week_start'], 
            weekly_data['week_end'], 
            update_db=False
        )[:5]
        
        # Staff performance for the week
        staff_performance = AnalyticsEngine.calculate_salesperson_performance(
            weekly_data['week_start'], 
            weekly_data['week_end'], 
            update_db=False
        )
        
        cash_staff_performance = AnalyticsEngine.calculate_cash_department_performance(
            weekly_data['week_start'], 
            weekly_data['week_end'], 
            update_db=False
        )
        
        context = {
            'weekly_snapshot': weekly_snapshot,
            'daily_summaries': daily_summaries,
            'previous_week_snapshot': previous_week_snapshot,
            'revenue_change': revenue_change,
            'profit_change': profit_change,
            'week_start': weekly_data['week_start'],
            'week_end': weekly_data['week_end'],
            'top_products': top_products,
            'top_cash_services': top_cash_services,
            'staff_performance': staff_performance,
            'cash_staff_performance': cash_staff_performance,
        }
        
        log_audit_action(
            request.user, 
            'view', 
            'WeeklySummary', 
            details=f'Viewed weekly summary for {weekly_data["week_start"]} to {weekly_data["week_end"]}'
        )
        
        return render(request, 'accounting_app/weekly_summary.html', context)
        
    except Exception as e:
        messages.error(request, f'Error generating weekly summary: {str(e)}')
        return redirect('accounting_dashboard')


@login_required
@user_passes_test(is_admin)
def cash_department_analytics(request):
    """Cash department specific analytics and reporting"""
    today = timezone.now().date()
    
    # Get current month cash department data
    current_month = today.replace(day=1)
    month_end = current_month.replace(day=monthrange(current_month.year, current_month.month)[1])
    
    # Cash department monthly metrics
    cash_monthly_data = AnalyticsEngine.create_department_financial_snapshot(
        'monthly', current_month, month_end
    )
    
    # Cash service performance for current month
    cash_services = AnalyticsEngine.calculate_cash_service_performance(
        current_month, month_end, update_db=False
    )
    
    # Cash staff performance for current month
    cash_staff = AnalyticsEngine.calculate_cash_department_performance(
        current_month, month_end, update_db=False
    )
    
    # Get last 6 months cash department trends
    monthly_trends = []
    for i in range(6):
        trend_month = (current_month.replace(day=1) - timedelta(days=32*i)).replace(day=1)
        trend_month_end = trend_month.replace(day=monthrange(trend_month.year, trend_month.month)[1])
        
        try:
            trend_snapshot = DepartmentFinancialSnapshot.objects.get(
                period_type='monthly',
                period_start=trend_month,
                period_end=trend_month_end
            )
        except DepartmentFinancialSnapshot.DoesNotExist:
            trend_snapshot = AnalyticsEngine.create_department_financial_snapshot(
                'monthly', trend_month, trend_month_end
            )
        
        monthly_trends.append({
            'month': trend_month,
            'snapshot': trend_snapshot
        })
    
    monthly_trends.reverse()  # Show oldest to newest
    
    # Calculate average transaction value
    average_transaction_value = 0
    if cash_monthly_data.cash_transactions_count > 0:
        average_transaction_value = cash_monthly_data.cash_revenue / cash_monthly_data.cash_transactions_count
    
    context = {
        'cash_monthly_data': cash_monthly_data,
        'cash_services': cash_services,
        'cash_staff': cash_staff,
        'monthly_trends': monthly_trends,
        'current_month': current_month.strftime('%B %Y'),
        'average_transaction_value': average_transaction_value,
    }
    
    log_audit_action(request.user, 'view', 'CashDepartmentAnalytics', details='Viewed cash department analytics')
    return render(request, 'accounting_app/cash_analytics.html', context)
