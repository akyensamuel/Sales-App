import csv
import io
from datetime import datetime
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Q
from django.utils import timezone
from django import forms
from django.db import transaction
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory

from .models import Product, Invoice, Sale, AdminLog
from .forms import InvoiceForm, SaleForm, ProductForm, SalesCSVImportForm
from .cache_utils import SalesCache, get_dashboard_stats, cache_expensive_query


# === UTILITY FUNCTIONS ===

def is_manager(user):
    """Check if user is a manager"""
    return user.is_authenticated and user.groups.filter(name='Managers').exists()


def validate_stock_availability(formset_data):
    """
    Validate that all items in the formset have sufficient stock.
    Returns a list of error messages if validation fails.
    """
    errors = []
    stock_requirements = {}  # {product_name: total_quantity_needed}
    
    for form_data in formset_data:
        if form_data and not form_data.get('DELETE', False):
            item_name = form_data.get('item')
            quantity = form_data.get('quantity', 0)
            
            if item_name and quantity > 0:
                stock_requirements[item_name] = stock_requirements.get(item_name, 0) + quantity
    
    # Check stock availability for each product
    for item_name, total_needed in stock_requirements.items():
        try:
            product = Product.objects.get(name=item_name)
            available = product.stock or 0
            if available < total_needed:
                errors.append(
                    f"Insufficient stock for '{item_name}'. "
                    f"Needed: {total_needed}, Available: {available}"
                )
        except Product.DoesNotExist:
            errors.append(f"Product '{item_name}' not found in inventory.")
    
    return errors


def deduct_stock_for_sale_items(formset_data, invoice_no):
    """
    Deduct stock quantities for all items in the sale.
    This function should be called within a database transaction.
    """
    stock_deductions = {}  # {product_name: total_quantity_to_deduct}
    
    # Calculate total deductions needed per product
    for form_data in formset_data:
        if form_data and not form_data.get('DELETE', False):
            item_name = form_data.get('item')
            quantity = form_data.get('quantity', 0)
            
            if item_name and quantity > 0:
                stock_deductions[item_name] = stock_deductions.get(item_name, 0) + quantity
    
    # Apply deductions
    for item_name, total_deduction in stock_deductions.items():
        try:
            product = Product.objects.select_for_update().get(name=item_name)
            product.stock = (product.stock or 0) - total_deduction
            product.save()
            print(f"Stock deducted: {item_name} - {total_deduction} units. New stock: {product.stock}")
        except Product.DoesNotExist:
            print(f"WARNING: Product '{item_name}' not found during stock deduction")


def restore_stock_for_sale_items(sale_items, invoice_no):
    """
    Restore stock quantities for sale items (used when deleting/editing invoices).
    """
    for sale_item in sale_items:
        if sale_item.item and sale_item.quantity:
            try:
                product = Product.objects.select_for_update().get(name=sale_item.item)
                product.stock = (product.stock or 0) + sale_item.quantity
                product.save()
                print(f"Stock restored: {sale_item.item} + {sale_item.quantity} units. New stock: {product.stock}")
            except Product.DoesNotExist:
                print(f"WARNING: Product '{sale_item.item}' not found during stock restoration")


def process_csv_import(csv_file):
    """Process CSV file import and return results"""
    decoded_file = csv_file.read().decode('utf-8')
    io_string = io.StringIO(decoded_file)
    reader = csv.DictReader(io_string)
    imported, errors = 0, []
    
    for idx, row in enumerate(reader, start=2):
        try:
            # Handle different CSV column name variations
            date_of_sale = row.get('Date of Sale') or row.get('DATE_TODAY')
            invoice_no = row.get('Invoice No') or row.get('INV NO')
            teller = row.get('User') or row.get('TELLER')
            customer_name = row.get('Customer Name') or row.get('CUSTOMER NA')
            customer_number = row.get('CUSTOMER NO')
            item = row.get('Item') or row.get('TYPE OF JOB')
            quantity = int(float(row.get('Quantity') or row.get('QTY') or 1))
            unit_price = float(row.get('Unit Price') or row.get('UP') or 0)
            total_amount = float(row.get('total_amount') or row.get('T AMT') or 0)
            amount_paid = float(row.get('AMT PAID') or 0)
            balance = float(row.get('BAL TO BE PAID') or 0)

            invoice, created = Invoice.objects.get_or_create(
                invoice_no=invoice_no,
                defaults={
                    'customer_name': customer_name,
                    'date_of_sale': date_of_sale,
                    'amount_paid': amount_paid,
                    'total': total_amount,
                }
            )
            
            Sale.objects.create(
                invoice=invoice,
                item=item,
                unit_price=unit_price,
                quantity=quantity,
                total_price=total_amount,
            )
            imported += 1
            
        except Exception as e:
            errors.append(f"Row {idx}: {e}")
    
    return imported, errors


# === AUTHENTICATION VIEWS ===

def login_view(request):
    """Handle user login with role-based redirection"""
    if request.user.is_authenticated:
        return redirect('manager_dashboard' if is_manager(request.user) else 'sales_entry')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('manager_dashboard' if is_manager(user) else 'sales_entry')
        else:
            return render(request, 'sales_app/login.html', {'error': 'Invalid credentials'})
    
    return render(request, 'sales_app/login.html')


def logout_view(request):
    """Handle user logout"""
    logout(request)
    return redirect('login')


# === PRODUCT MANAGEMENT VIEWS ===

@login_required
@user_passes_test(is_manager)
def products_list(request):
    """Display list of all products with pagination and filtering"""
    products_query = Product.objects.all()
    
    # Add search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        products_query = products_query.filter(
            Q(name__icontains=search_query) | Q(stock__lt=50)
        )
    
    # Add filtering for low stock
    show_low_stock = request.GET.get('low_stock', '') == 'true'
    if show_low_stock:
        products_query = products_query.filter(stock__lt=50)
    
    products_query = products_query.order_by('name')
    
    # Add pagination
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    paginator = Paginator(products_query, 50)  # Show 50 products per page
    page = request.GET.get('page')
    
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)
    
    context = {
        'products': products,
        'search_query': search_query,
        'show_low_stock': show_low_stock,
    }
    
    return render(request, 'sales_app/products.html', context)


@login_required
@user_passes_test(is_manager)
def add_product(request):
    """Add a new product"""
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product added successfully!')
            return redirect('products_list')
    else:
        form = ProductForm()
    
    return render(request, 'sales_app/product_form.html', {'form': form, 'action': 'Add'})


@login_required
@user_passes_test(is_manager)
def edit_product(request, product_id):
    """Edit an existing product"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully!')
            return redirect('products_list')
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'sales_app/product_form.html', {'form': form, 'action': 'Edit'})


@login_required
@user_passes_test(is_manager)
def delete_product(request, product_id):
    """Delete a product"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted successfully!')
        return redirect('products_list')
    
    return render(request, 'sales_app/product_confirm_delete.html', {'product': product})


# === PRODUCT SEARCH API ===

def product_autocomplete(request):
    """Legacy product autocomplete API"""
    query = request.GET.get('q', '')
    products = Product.objects.filter(name__icontains=query)[:10]
    data = [
        {
            'id': p.id, 
            'name': p.name, 
            'unit_price': str(p.price),
            'stock': p.stock or 0
        }
        for p in products
    ]
    return JsonResponse(data, safe=False)


def product_search_api(request):
    """
    API endpoint for Select2 product search.
    Returns JSON list of matching products with id, name, price, and stock.
    """
    if request.method == 'GET':
        query = request.GET.get('q', '').strip()
        products = Product.objects.filter(name__icontains=query)[:20] if query else Product.objects.none()
        
        data = [
            {
                'id': product.id,
                'text': product.name,
                'price': str(product.price),
                'unit_price': str(product.price),
                'stock': product.stock or 0
            }
            for product in products
        ]
        return JsonResponse(data, safe=False)
    
    return JsonResponse([], safe=False)


# === SALES ENTRY VIEW ===

@login_required
def sales_entry(request):
    """Handle sales entry form with stock management"""
    SaleFormSet = inlineformset_factory(Invoice, Sale, form=SaleForm, extra=1, can_delete=True)
    
    if request.method == 'POST':
        invoice_form = InvoiceForm(request.POST)
        formset = SaleFormSet(request.POST)
        
        if invoice_form.is_valid() and formset.is_valid():
            # Validate stock availability before proceeding
            formset_data = [form.cleaned_data for form in formset if form.cleaned_data]
            stock_errors = validate_stock_availability(formset_data)
            
            if stock_errors:
                for error in stock_errors:
                    messages.error(request, error)
            else:
                try:
                    with transaction.atomic():
                        invoice = invoice_form.save(commit=False)
                        invoice.user = request.user
                        invoice.save()
                        
                        # Deduct stock before saving formset
                        deduct_stock_for_sale_items(formset_data, invoice.invoice_no)
                        
                        # Save the formset
                        formset.instance = invoice
                        formset.save()
                        
                        # Recalculate total from saved items
                        invoice.total = sum(item.total_price for item in invoice.items.all())
                        invoice.save()
                        
                        messages.success(request, f'Invoice {invoice.invoice_no} saved successfully!')
                        
                        if 'save_print' in request.POST:
                            return render(request, 'sales_app/receipt_print.html', {
                                'invoice': invoice,
                                'items': invoice.items.all(),
                            })
                        
                        return redirect('sales_entry')
                        
                except Exception as e:
                    messages.error(request, f'Error saving invoice: {str(e)}')
    else:
        invoice_form = InvoiceForm()
        formset = SaleFormSet()
    
    return render(request, 'sales_app/sales_entry.html', {
        'invoice_form': invoice_form,
        'formset': formset
    })


# === MANAGER DASHBOARD & INVOICE VIEWS ===

def process_csv_import(csv_file):
    """
    Process CSV file import and return results
    """
    import_errors = []
    imported_count = 0
    
    try:
        # Validate file
        if not csv_file.name.endswith('.csv'):
            return 0, ['Please upload a valid CSV file.']
        
        if csv_file.size > 10 * 1024 * 1024:  # 10MB limit
            return 0, ['File size too large. Please upload a file smaller than 10MB.']
        
        # Process CSV
        decoded_file = csv_file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string)
        
        with transaction.atomic():
            for row_num, row in enumerate(reader, start=2):
                try:
                    # Clean and validate data
                    date_str = (row.get('Date of Sale') or '').strip()
                    invoice_no = (row.get('Invoice No') or '').strip()
                    customer_name = (row.get('Customer Name') or '').strip()
                    item = (row.get('Item') or '').strip()
                    
                    # Skip empty rows
                    if not any([date_str, invoice_no, customer_name, item]):
                        continue
                    
                    # Parse numeric fields
                    quantity = int(float(row.get('Quantity', 0) or 0))
                    unit_price = float(row.get('Unit Price', 0) or 0)
                    total_amount = float(row.get('total_amount', 0) or 0)
                    amount_paid = float(row.get('AMT PAID', 0) or 0)
                    
                    # Parse date
                    from datetime import datetime
                    if '/' in date_str:
                        date_obj = datetime.strptime(date_str, '%d/%m/%Y').date()
                    else:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                    
                    # Get or create invoice
                    invoice, created = Invoice.objects.get_or_create(
                        invoice_no=invoice_no,
                        defaults={
                            'customer_name': customer_name,
                            'date_of_sale': date_obj,
                            'amount_paid': amount_paid,
                            'total': total_amount,
                        }
                    )
                    
                    # Create sale item
                    Sale.objects.create(
                        invoice=invoice,
                        item=item,
                        unit_price=unit_price,
                        quantity=quantity,
                        total_price=total_amount,
                    )
                    
                    imported_count += 1
                    
                except Exception as e:
                    import_errors.append(f"Row {row_num}: {str(e)}")
                    continue
        
        return imported_count, import_errors
        
    except Exception as e:
        return 0, [f'Error processing CSV file: {str(e)}']


@login_required
@user_passes_test(is_manager)
def manager_dashboard(request):
    """Manager dashboard with search functionality and CSV import"""
    # Handle CSV import
    import_result = None
    import_errors = None
    csv_form = SalesCSVImportForm()
    
    if request.method == 'POST':
        if 'csv_file' in request.FILES:
            csv_form = SalesCSVImportForm(request.POST, request.FILES)
            if csv_form.is_valid():
                csv_file = csv_form.cleaned_data['csv_file']
                import_result, import_errors = process_csv_import(csv_file)
                
                if import_result > 0:
                    messages.success(request, f'Successfully imported {import_result} sales records.')
                if import_errors:
                    for error in import_errors[:5]:  # Show first 5 errors
                        messages.error(request, error)
                    if len(import_errors) > 5:
                        messages.warning(request, f'And {len(import_errors) - 5} more errors...')
        
        elif 'delete_invoice_id' in request.POST:
            # Handle invoice deletion with stock restoration
            invoice_id = request.POST.get('delete_invoice_id')
            try:
                with transaction.atomic():
                    invoice = Invoice.objects.select_related('user').prefetch_related('items').get(id=invoice_id)
                    
                    # Restore stock for all items in the invoice
                    restore_stock_for_sale_items(invoice.items.all(), invoice.invoice_no)
                    
                    # Log the deletion
                    AdminLog.objects.create(
                        user=request.user,
                        action='Deleted Invoice (Stock Restored)',
                        details=f'Invoice ID: {invoice_id}, Customer: {invoice.customer_name}'
                    )
                    
                    invoice.delete()
                    messages.success(request, 'Invoice deleted and stock quantities restored.')
                    
            except Invoice.DoesNotExist:
                messages.error(request, 'Invoice not found.')
            except Exception as e:
                messages.error(request, f'Error deleting invoice: {str(e)}')
            
            return redirect('manager_dashboard')
    
    # Handle search and filtering with optimized queries
    invoices_query = Invoice.objects.select_related('user').prefetch_related('items')
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    customer_name = request.GET.get('customer_name', '').strip()
    invoice_no = request.GET.get('invoice_no', '').strip()
    
    has_search_params = any([start_date, end_date, customer_name, invoice_no])
    
    if has_search_params:
        search_conditions = Q()
        
        # Date range search
        if start_date and end_date:
            search_conditions |= Q(date_of_sale__gte=start_date, date_of_sale__lte=end_date)
        elif start_date:
            search_conditions |= Q(date_of_sale__gte=start_date)
        elif end_date:
            search_conditions |= Q(date_of_sale__lte=end_date)
        
        # Customer name search
        if customer_name:
            search_conditions |= Q(customer_name__icontains=customer_name)
        
        # Invoice number search
        if invoice_no:
            search_conditions |= Q(invoice_no__icontains=invoice_no)
        
        if search_conditions:
            invoices = invoices_query.filter(search_conditions).order_by('-date_of_sale')
    else:
        # Default: show today's invoices
        today = timezone.now().date()
        invoices = invoices_query.filter(date_of_sale=today).order_by('-date_of_sale')

    # Use pagination for large datasets
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    paginator = Paginator(invoices, 25)  # Show 25 invoices per page
    page = request.GET.get('page')
    
    try:
        invoices_page = paginator.page(page)
    except PageNotAnInteger:
        invoices_page = paginator.page(1)
    except EmptyPage:
        invoices_page = paginator.page(paginator.num_pages)
    
    # Calculate total sales efficiently
    total_sales = invoices.aggregate(Sum('total'))['total__sum'] or 0
    
    context = {
        'invoices': invoices_page,
        'total_sales': total_sales,
        'search_params': {
            'start_date': start_date,
            'end_date': end_date,
            'customer_name': customer_name,
            'invoice_no': invoice_no,
        },
        'form': csv_form,
        'import_result': import_result,
        'import_errors': import_errors,
        'has_search_params': has_search_params,
    }
    
    return render(request, 'sales_app/manager_dashboard.html', context)


@login_required
@user_passes_test(is_manager)
def invoice_detail(request, invoice_id, print_mode=False):
    """Display invoice details or receipt for printing"""
    invoice = get_object_or_404(Invoice, id=invoice_id)
    items = invoice.items.exclude(item__isnull=True).exclude(item__exact="")
    
    template = 'sales_app/receipt_print.html' if (print_mode or request.resolver_match.url_name == 'receipt_print') else 'sales_app/invoice_detail.html'
    
    return render(request, template, {
        'invoice': invoice,
        'items': items
    })


@login_required
@user_passes_test(is_manager)
def edit_invoice(request, invoice_id):
    """Edit an existing invoice with stock management"""
    invoice = get_object_or_404(Invoice, id=invoice_id)
    SaleFormSet = inlineformset_factory(Invoice, Sale, form=SaleForm, extra=0, can_delete=True)
    
    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=invoice)
        formset = SaleFormSet(request.POST, instance=invoice)
        
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    # Restore stock for original invoice items
                    original_items = list(invoice.items.all())
                    restore_stock_for_sale_items(original_items, invoice.invoice_no)
                    
                    # Validate stock for new/updated items
                    formset_data = [form.cleaned_data for form in formset if form.cleaned_data]
                    stock_errors = validate_stock_availability(formset_data)
                    
                    if stock_errors:
                        # Restore original stock deductions if validation fails
                        for sale_item in original_items:
                            if sale_item.item and sale_item.quantity:
                                try:
                                    product = Product.objects.select_for_update().get(name=sale_item.item)
                                    product.stock = (product.stock or 0) - sale_item.quantity
                                    product.save()
                                except Product.DoesNotExist:
                                    pass
                        
                        for error in stock_errors:
                            messages.error(request, error)
                        raise ValidationError("Stock validation failed")
                    
                    # Save updated invoice and formset
                    invoice = form.save(commit=False)
                    invoice.user = request.user
                    invoice.save()
                    formset.save()
                    
                    # Deduct stock for new/updated items
                    deduct_stock_for_sale_items(formset_data, invoice.invoice_no)
                    
                    # Recalculate total
                    items_total = sum(item.total_price or 0 for item in invoice.items.all())
                    invoice_discount = invoice.discount or 0
                    invoice.total = items_total - invoice_discount
                    invoice.save()
                    
                    messages.success(request, 'Invoice updated successfully!')
                    return redirect('manager_dashboard')
                    
            except ValidationError:
                pass  # Error messages already added
            except Exception as e:
                messages.error(request, f'Error updating invoice: {str(e)}')
    else:
        form = InvoiceForm(instance=invoice)
        formset = SaleFormSet(instance=invoice)
        
    return render(request, 'sales_app/edit_invoice.html', {
        'form': form,
        'formset': formset,
        'invoice': invoice
    })


@login_required
@user_passes_test(is_manager)
def edit_sale(request, sale_id):
    """Edit a single sale item"""
    sale = get_object_or_404(Sale, id=sale_id)
    
    if request.method == 'POST':
        form = SaleForm(request.POST, instance=sale)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sale updated successfully!')
            return redirect('manager_dashboard')
    else:
        form = SaleForm(instance=sale)
    
    return render(request, 'sales_app/edit_sale.html', {'form': form})


# === PRINT VIEWS ===

@login_required
@user_passes_test(is_manager)
def print_daily_invoices(request):
    """Print all invoices for a specific date"""
    date_str = request.GET.get('date')
    
    if date_str:
        try:
            print_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            print_date = timezone.now().date()
    else:
        print_date = timezone.now().date()
    
    invoices = Invoice.objects.filter(date_of_sale=print_date).prefetch_related('items').order_by('invoice_no')
    total_sales = invoices.aggregate(Sum('total'))['total__sum'] or 0
    
    context = {
        'invoices': invoices,
        'total_sales': total_sales,
        'print_date': print_date,
        'print_type': 'daily'
    }
    return render(request, 'sales_app/invoices_print.html', context)


@login_required
@user_passes_test(is_manager)
def print_search_results(request):
    """Print search results from manager dashboard"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    customer_name = request.GET.get('customer_name', '').strip()
    invoice_no = request.GET.get('invoice_no', '').strip()
    
    invoices = Invoice.objects.all().prefetch_related('items').order_by('-date_of_sale')
    has_search_params = any([start_date, end_date, customer_name, invoice_no])
    
    if has_search_params:
        search_conditions = Q()
        
        if start_date and end_date:
            search_conditions |= Q(date_of_sale__gte=start_date, date_of_sale__lte=end_date)
        elif start_date:
            search_conditions |= Q(date_of_sale__gte=start_date)
        elif end_date:
            search_conditions |= Q(date_of_sale__lte=end_date)
        
        if customer_name:
            search_conditions |= Q(customer_name__icontains=customer_name)
        
        if invoice_no:
            search_conditions |= Q(invoice_no__icontains=invoice_no)
        
        if search_conditions:
            invoices = invoices.filter(search_conditions)
    else:
        # Show today's invoices if no search params
        today = timezone.now().date()
        invoices = invoices.filter(date_of_sale=today)
    
    total_sales = invoices.aggregate(Sum('total'))['total__sum'] or 0
    
    context = {
        'invoices': invoices,
        'total_sales': total_sales,
        'search_params': {
            'start_date': start_date,
            'end_date': end_date,
            'customer_name': customer_name,
            'invoice_no': invoice_no,
        },
        'print_type': 'search'
    }
    return render(request, 'sales_app/invoices_print.html', context)


# === DEBUG VIEW ===

def test_debug(request):
    """Test debug view for development"""
    print("=== TEST DEBUG VIEW CALLED ===")
    print("This should appear in terminal")
    return HttpResponse("Debug test")