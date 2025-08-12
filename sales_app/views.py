import csv
import io
from datetime import datetime
import logging

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

from .models import Product, Invoice, Sale, AdminLog, CashInvoice, CashSale, CashProduct
from .forms import InvoiceForm, SaleForm, ProductForm, SalesCSVImportForm, CashProductForm, CashInvoiceForm, CashSaleForm
from .cache_utils import SalesCache, get_dashboard_stats, cache_expensive_query



# === UTILITY FUNCTIONS ===
logger = logging.getLogger(__name__)

def is_manager(user):
    """Check if user is a manager"""
    return user.is_authenticated and user.groups.filter(name='Managers').exists()


def validate_stock_availability(formset_data):
    """
    Validate that all items exist in the product catalog.
    Note: Stock levels are now handled during deduction with minimum zero enforcement.
    Returns a list of error messages if validation fails.
    """
    errors = []
    stock_requirements = {}  # {product_name: total_quantity_needed}
    
    try:
        logger.debug(f"Validating items for {len(formset_data)} entries")
        for i, form_data in enumerate(formset_data):
            if form_data and not form_data.get('DELETE', False):
                item_name = form_data.get('item')
                quantity = form_data.get('quantity', 0)
                logger.debug(f"Item {i}: {item_name}, Quantity: {quantity}")
                if item_name and quantity > 0:
                    stock_requirements[item_name] = stock_requirements.get(item_name, 0) + quantity
        logger.debug(f"Stock requirements: {stock_requirements}")
        # Only check that products exist - no longer blocking on stock levels
        for item_name, total_needed in stock_requirements.items():
            try:
                product = Product.objects.get(name=item_name)
                available = product.stock or 0
                logger.debug(f"Product {item_name}: needed {total_needed}, available {available}")
                # Log low stock warning but don't block the sale
                if available < total_needed:
                    logger.warning(f"STOCK WARNING: Low stock for '{item_name}'. Needed: {total_needed}, Available: {available} (Sale will proceed, stock will be capped at zero)")
            except Product.DoesNotExist:
                error_msg = f"Product '{item_name}' not found in inventory."
                errors.append(error_msg)
                logger.error(f"PRODUCT ERROR: {error_msg}")
    except Exception as validation_error:
        error_msg = f"Stock validation error: {str(validation_error)}"
        errors.append(error_msg)
        logger.error(f"VALIDATION ERROR: {error_msg}")
        import traceback
        logger.error(traceback.format_exc())
    logger.debug(f"Item validation completed. Found {len(errors)} errors")
    return errors



    
def deduct_stock_for_sale_items(formset_data, invoice_no):
    """
    Deduct stock quantities for all items in the sale.
    Stock levels are capped at zero (never goes negative).
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
    
    # Apply deductions with zero-floor enforcement
    for item_name, total_deduction in stock_deductions.items():
        try:
            product = Product.objects.select_for_update().get(name=item_name)
            current_stock = product.stock or 0
            
            # Calculate actual deduction (never let stock go negative)
            actual_deduction = min(total_deduction, current_stock)
            new_stock = max(0, current_stock - total_deduction)
            
            product.stock = new_stock
            product.save()
            
            if actual_deduction < total_deduction:
                shortage = total_deduction - actual_deduction
                logger.warning(f"STOCK CAPPED: {item_name} - attempted {total_deduction}, deducted {actual_deduction}, shortage {shortage}. New stock: {new_stock}")
            else:
                logger.info(f"Stock deducted: {item_name} - {total_deduction} units. New stock: {new_stock}")
            
        except Product.DoesNotExist:
            logger.warning(f"Product '{item_name}' not found during stock deduction")
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
                logger.info(f"Stock restored: {sale_item.item} + {sale_item.quantity} units. New stock: {product.stock}")
            except Product.DoesNotExist:
                logger.warning(f"Product '{sale_item.item}' not found during stock restoration")


def process_csv_import(csv_file):
    """Process CSV file import and return results"""
    from datetime import datetime
    
    def parse_csv_date(date_string):
        """Parse DD/M/YYYY format to proper date object"""
        if not date_string or date_string.strip() == '' or date_string.strip() == ';':
            return timezone.now().date()
        
        try:
            # Try DD/M/YYYY format first (from your CSV)
            return datetime.strptime(date_string.strip(), '%d/%m/%Y').date()
        except ValueError:
            try:
                # Try DD-M-YYYY format
                return datetime.strptime(date_string.strip(), '%d-%m-%Y').date()
            except ValueError:
                try:
                    # Try YYYY-MM-DD format (standard Django format)
                    return datetime.strptime(date_string.strip(), '%Y-%m-%d').date()
                except ValueError:
                    logger.warning(f"Could not parse date: {date_string}, using current date")
                    return timezone.now().date()
    
    decoded_file = csv_file.read().decode('utf-8')
    io_string = io.StringIO(decoded_file)
    reader = csv.DictReader(io_string)
    imported, errors = 0, []
    
    for idx, row in enumerate(reader, start=2):
        try:
            # Handle different CSV column name variations
            date_string = row.get('Date of Sale') or row.get('DATE_TODAY')
            date_of_sale = parse_csv_date(date_string)
            invoice_no = row.get('Invoice No') or row.get('INV NO')
            teller = row.get('User') or row.get('TELLER')
            customer_name = row.get('Customer Name') or row.get('CUSTOMER NA')
            customer_phone = row.get('Customer Phone') or row.get('CUSTOMER_PHONE') or row.get('Phone')
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
                    'customer_phone': customer_phone,
                    'date_of_sale': date_of_sale,  # Now using properly parsed date
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
        try:
            invoice_form = InvoiceForm(request.POST)
            formset = SaleFormSet(request.POST)
            
            # Debug logging for production
            logger.debug(f"Processing sales entry for user {request.user}")
            logger.debug(f"Formset total forms: {request.POST.get('form-TOTAL_FORMS', 'NOT_FOUND')}")
            logger.debug(f"POST data keys: {list(request.POST.keys())}")
            
            if invoice_form.is_valid() and formset.is_valid():
                # Validate stock availability before proceeding
                formset_data = [form.cleaned_data for form in formset if form.cleaned_data and not form.cleaned_data.get('DELETE', False)]
                logger.debug(f"Processing {len(formset_data)} sale items")
                
                # Double-check we have items to process
                if not formset_data:
                    messages.error(request, 'No valid items found. Please add at least one item to the invoice.')
                    logger.debug("No valid items found in formset")
                else:
                    validation_errors = validate_stock_availability(formset_data)
                    
                    if validation_errors:
                        for error in validation_errors:
                            messages.error(request, error)
                        logger.debug(f"Item validation failed: {validation_errors}")
                    else:
                        try:
                            with transaction.atomic():
                                invoice = invoice_form.save(commit=False)
                                invoice.user = request.user
                                invoice.save()
                                logger.debug(f"Invoice created with ID {invoice.id}")
                                
                                # Deduct stock (capped at zero) before saving formset
                                deduct_stock_for_sale_items(formset_data, invoice.invoice_no)
                                
                                # Save the formset
                                formset.instance = invoice
                                saved_items = formset.save()
                                logger.debug(f"Saved {len(saved_items)} sale items")
                                
                                # Recalculate total from saved items
                                total_amount = sum(item.total_price for item in invoice.items.all())
                                invoice.total = total_amount
                                invoice.save()
                                logger.debug(f"Invoice total calculated: {total_amount}")
                                
                                messages.success(request, f'Invoice {invoice.invoice_no} saved successfully!')
                                
                                if 'save_print' in request.POST:
                                    logger.debug(f"Rendering receipt for invoice {invoice.invoice_no}")
                                    return render(request, 'sales_app/receipt_print.html', {
                                        'invoice': invoice,
                                        'items': invoice.items.all(),
                                    })
                                
                                logger.debug("Redirecting to sales entry after successful save")
                                return redirect('sales_entry')
                                
                        except Exception as save_error:
                            logger.error(f"Database transaction failed: {str(save_error)}")
                            messages.error(request, f'Error saving invoice: {str(save_error)}')
                            # Optionally add more detailed error for debugging
                            if hasattr(save_error, '__dict__'):
                                logger.error(f"Error details: {save_error.__dict__}")
                            
            else:
                # Form validation failed
                logger.debug("Form validation failed")
                if not invoice_form.is_valid():
                    logger.debug(f"Invoice form errors: {invoice_form.errors}")
                    for field, errors in invoice_form.errors.items():
                        for error in errors:
                            messages.error(request, f"Invoice {field}: {error}")
                            
                if not formset.is_valid():
                    logger.debug(f"Formset errors: {formset.errors}")
                    logger.debug(f"Formset non-form errors: {formset.non_form_errors()}")
                    
                    for i, form in enumerate(formset.forms):
                        if form.errors:
                            logger.debug(f"Form {i} errors: {form.errors}")
                            for field, errors in form.errors.items():
                                for error in errors:
                                    messages.error(request, f"Item {i+1} - {field}: {error}")
                    
                    for error in formset.non_form_errors():
                        messages.error(request, f"Form error: {error}")
                        
        except Exception as general_error:
            logger.error(f"CRITICAL ERROR in sales_entry: {str(general_error)}")
            import traceback
            traceback.print_exc()
            messages.error(request, f'Unexpected error occurred. Please try again. Error: {str(general_error)}')
            
    else:
        invoice_form = InvoiceForm()
        formset = SaleFormSet()
    
    return render(request, 'sales_app/sales_entry.html', {
        'invoice_form': invoice_form,
        'formset': formset
    })


# === MANAGER DASHBOARD & INVOICE VIEWS ===


@login_required
@user_passes_test(is_manager)
def manager_dashboard(request):
    """Manager dashboard with search functionality and CSV import for both regular and cash departments"""
    # Handle CSV import
    import_result = None
    import_errors = None
    csv_form = SalesCSVImportForm()
    
    # Get department filter
    department = request.GET.get('department', 'regular')  # 'regular' or 'cash'
    
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
            # Handle regular invoice deletion with stock restoration
            invoice_id = request.POST.get('delete_invoice_id')
            logger.debug(f"Delete request received for invoice ID: {invoice_id}")
            logger.debug(f"POST data: {dict(request.POST)}")
            
            try:
                with transaction.atomic():
                    invoice = Invoice.objects.select_related('user').prefetch_related('items').get(id=invoice_id)
                    logger.debug(f"Found invoice {invoice.invoice_no} for deletion")
                    
                    # Store invoice data for success message and logging (since object will be deleted)
                    invoice_no = invoice.invoice_no
                    customer_name = invoice.customer_name
                    invoice_items = list(invoice.items.all())  # Convert to list to avoid queryset issues
                    
                    logger.debug(f"Invoice has {len(invoice_items)} items")
                    
                    # Restore stock for all items in the invoice
                    restore_stock_for_sale_items(invoice_items, invoice_no)
                    logger.debug(f"Stock restored for invoice {invoice_no}")
                    
                    # Log the deletion before deleting
                    AdminLog.objects.create(
                        user=request.user,
                        action='Deleted Invoice (Stock Restored)',
                        details=f'Invoice ID: {invoice_id}, Customer: {customer_name}'
                    )
                    logger.debug(f"Admin log created for deletion")
                    
                    # Refresh invoice object from database before delete
                    invoice.refresh_from_db()
                    logger.debug(f"Invoice refreshed from database")
                    
                    # Delete the invoice using direct database query
                    try:
                        # First, let's check if the invoice still exists
                        invoice_exists = Invoice.objects.filter(id=invoice_id).exists()
                        logger.debug(f"Invoice exists before delete: {invoice_exists}")
                        
                        if invoice_exists:
                            # Try deleting using queryset delete (bypasses model delete method)
                            deleted_count = Invoice.objects.filter(id=invoice_id).delete()
                            logger.debug(f"Deleted count: {deleted_count}")
                            logger.debug(f"Invoice {invoice_no} deleted successfully via queryset")
                            messages.success(request, f'Invoice {invoice_no} deleted and stock quantities restored.')
                        else:
                            logger.debug(f"Invoice {invoice_id} no longer exists in database")
                            messages.error(request, 'Invoice was already deleted or does not exist.')
                            
                    except Exception as delete_error:
                        logger.debug(f"Error during queryset delete: {str(delete_error)}")
                        logger.debug(f"Delete error type: {type(delete_error)}")
                        import traceback
                        traceback.print_exc()
                        raise delete_error
                    
            except Invoice.DoesNotExist:
                logger.debug(f"Invoice with ID {invoice_id} not found")
                messages.error(request, 'Invoice not found.')
            except Exception as e:
                logger.debug(f"Error during deletion process: {str(e)}")
                logger.debug(f"Error type: {type(e)}")
                import traceback
                traceback.print_exc()
                messages.error(request, f'Error deleting invoice: {str(e)}')
            
            return redirect('manager_dashboard')
            
        elif 'delete_cash_invoice_id' in request.POST:
            # Handle cash invoice deletion (no stock restoration needed)
            cash_invoice_id = request.POST.get('delete_cash_invoice_id')
            logger.debug(f"Delete request received for cash invoice ID: {cash_invoice_id}")
            
            try:
                cash_invoice = CashInvoice.objects.get(id=cash_invoice_id)
                invoice_no = cash_invoice.invoice_no
                customer_name = cash_invoice.customer_name
                
                # Log the deletion
                AdminLog.objects.create(
                    user=request.user,
                    action='Deleted Cash Invoice',
                    details=f'Cash Invoice ID: {cash_invoice_id}, Customer: {customer_name}'
                )
                
                cash_invoice.delete()
                messages.success(request, f'Cash Invoice {invoice_no} deleted successfully.')
                
            except CashInvoice.DoesNotExist:
                messages.error(request, 'Cash Invoice not found.')
            except Exception as e:
                messages.error(request, f'Error deleting cash invoice: {str(e)}')
            
            from django.http import HttpResponseRedirect
            from django.urls import reverse
            return HttpResponseRedirect(reverse('manager_dashboard') + '?department=cash')
    
    # Handle search and filtering parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    customer_name = request.GET.get('customer_name', '').strip()
    customer_phone = request.GET.get('customer_phone', '').strip()
    invoice_no = request.GET.get('invoice_no', '').strip()
    
    has_search_params = any([start_date, end_date, customer_name, customer_phone, invoice_no])
    
    # Handle different departments
    if department == 'cash':
        # Cash department - query CashInvoice model
        invoices_query = CashInvoice.objects.prefetch_related('items')
        
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
            
            # Customer phone search
            if customer_phone:
                search_conditions |= Q(customer_phone__icontains=customer_phone)
            
            # Invoice number search
            if invoice_no:
                search_conditions |= Q(invoice_no__icontains=invoice_no)
            
            if search_conditions:
                invoices = invoices_query.filter(search_conditions).order_by('-date_of_sale')
        else:
            # Default: show today's cash invoices
            today = timezone.now().date()
            invoices = invoices_query.filter(date_of_sale=today).order_by('-date_of_sale')
    
    else:
        # Regular department - query Invoice model
        invoices_query = Invoice.objects.select_related('user').prefetch_related('items')
        
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
            
            # Customer phone search
            if customer_phone:
                search_conditions |= Q(customer_phone__icontains=customer_phone)
            
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
        'department': department,
        'search_params': {
            'start_date': start_date,
            'end_date': end_date,
            'customer_name': customer_name,
            'customer_phone': customer_phone,
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
    """Print all invoices for a specific date (supports both regular and cash departments)"""
    date_str = request.GET.get('date')
    department = request.GET.get('department', 'regular')
    
    if date_str:
        try:
            print_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            print_date = timezone.now().date()
    else:
        print_date = timezone.now().date()
    
    if department == 'cash':
        invoices = CashInvoice.objects.filter(date_of_sale=print_date).prefetch_related('items').order_by('invoice_no')
        template_name = 'sales_app/cash_invoices_print.html'
    else:
        invoices = Invoice.objects.filter(date_of_sale=print_date).prefetch_related('items').order_by('invoice_no')
        template_name = 'sales_app/invoices_print.html'
    
    total_sales = invoices.aggregate(Sum('total'))['total__sum'] or 0
    
    context = {
        'invoices': invoices,
        'total_sales': total_sales,
        'print_date': print_date,
        'print_type': 'daily',
        'department': department
    }
    return render(request, template_name, context)


@login_required
@user_passes_test(is_manager)
def print_search_results(request):
    """Print search results from manager dashboard (supports both regular and cash departments)"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    customer_name = request.GET.get('customer_name', '').strip()
    customer_phone = request.GET.get('customer_phone', '').strip()
    invoice_no = request.GET.get('invoice_no', '').strip()
    department = request.GET.get('department', 'regular')
    
    # Select appropriate model based on department
    if department == 'cash':
        invoices = CashInvoice.objects.all().prefetch_related('items').order_by('-date_of_sale')
        template_name = 'sales_app/cash_invoices_print.html'
    else:
        invoices = Invoice.objects.all().prefetch_related('items').order_by('-date_of_sale')
        template_name = 'sales_app/invoices_print.html'
    
    has_search_params = any([start_date, end_date, customer_name, customer_phone, invoice_no])
    
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
        
        if customer_phone:
            search_conditions |= Q(customer_phone__icontains=customer_phone)
        
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
            'customer_phone': customer_phone,
            'invoice_no': invoice_no,
        },
        'print_type': 'search',
        'department': department
    }
    return render(request, template_name, context)


# === DEBUG VIEW ===

def test_debug(request):
    """Test debug view for development"""
    logger.info("TEST DEBUG VIEW CALLED")
    logger.info("This should appear in terminal")
    return HttpResponse("Debug test")


# === CASH DEPARTMENT VIEWS ===



@login_required
@user_passes_test(is_manager)
def cash_products(request):
    """Manage cash department products with rate-based pricing"""
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        
        if product_id:
            # Edit existing product
            product = get_object_or_404(CashProduct, id=product_id)
            form = CashProductForm(request.POST, instance=product)
        else:
            # Add new product
            form = CashProductForm(request.POST)
        
        if form.is_valid():
            product = form.save()
            action = 'updated' if product_id else 'added'
            messages.success(request, f'Product "{product.name}" {action} successfully!')
            
            # Log the action
            AdminLog.objects.create(
                user=request.user,
                action=f'Cash Product {action.title()}',
                details=f'Product: {product.name}, Rate: {product.rate}'
            )
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
        
        return redirect('cash_products')
    
    # GET request - display products
    products = CashProduct.objects.all().order_by('name')
    
    context = {
        'products': products,
    }
    
    return render(request, 'sales_app/cash_products.html', context)


@login_required
@user_passes_test(is_manager)
def delete_cash_product(request, product_id):
    """Delete a cash product"""
    if request.method == 'POST':
        try:
            product = get_object_or_404(CashProduct, id=product_id)
            product_name = product.name
            product.delete()
            
            messages.success(request, f'Product "{product_name}" deleted successfully!')
            
            # Log the deletion
            AdminLog.objects.create(
                user=request.user,
                action='Cash Product Deleted',
                details=f'Product: {product_name}'
            )
        except Exception as e:
            messages.error(request, f'Error deleting product: {str(e)}')
    
    return redirect('cash_products')


def cash_product_search_api(request):
    """
    API endpoint for Select2 cash product search.
    Returns JSON list of matching cash products with id, name, and rate.
    """
    if request.method == 'GET':
        query = request.GET.get('q', '').strip()
        products = CashProduct.objects.filter(name__icontains=query)[:20] if query else CashProduct.objects.none()
        
        data = [
            {
                'id': product.id,
                'text': product.name,
                'name': product.name,
                'rate': str(product.rate)
            }
            for product in products
        ]
        return JsonResponse(data, safe=False)
    
    return JsonResponse([], safe=False)


@login_required
def cash_sales_entry(request):
    """Handle cash department sales entry with rate-based pricing"""
    from django.forms import inlineformset_factory
    
    CashSaleFormSet = inlineformset_factory(CashInvoice, CashSale, form=CashSaleForm, extra=1, can_delete=True)
    
    if request.method == 'POST':
        try:
            invoice_form = CashInvoiceForm(request.POST)
            formset = CashSaleFormSet(request.POST)
            
            logger.debug(f"Processing cash sales entry for user {request.user}")
            logger.debug(f"Formset total forms: {request.POST.get('form-TOTAL_FORMS', 'NOT_FOUND')}")
            
            if invoice_form.is_valid() and formset.is_valid():
                formset_data = [form.cleaned_data for form in formset if form.cleaned_data and not form.cleaned_data.get('DELETE', False)]
                logger.debug(f"Processing {len(formset_data)} cash sale items")
                
                if not formset_data:
                    messages.error(request, 'No valid items found. Please add at least one item to the transaction.')
                    logger.debug("No valid items found in formset")
                else:
                    try:
                        with transaction.atomic():
                            # Create cash invoice
                            invoice = invoice_form.save(commit=False)
                            invoice.user = request.user
                            invoice.payment_status = 'paid'  # Cash transactions are always paid
                            invoice.save()
                            logger.debug(f"Cash invoice created with ID {invoice.id}")
                            
                            # Save the formset
                            formset.instance = invoice
                            saved_items = formset.save()
                            logger.debug(f"Saved {len(saved_items)} cash sale items")
                            
                            # Calculate total from saved items
                            total_amount = sum(item.total_price for item in invoice.items.all())
                            invoice.total = total_amount
                            invoice.save()
                            logger.debug(f"Cash invoice total calculated: {total_amount}")
                            
                            messages.success(request, f'Cash Transaction {invoice.invoice_no} saved successfully!')
                            
                            if 'save_print' in request.POST:
                                logger.debug(f"Rendering cash receipt for invoice {invoice.invoice_no}")
                                return render(request, 'sales_app/cash_receipt_print.html', {
                                    'invoice': invoice,
                                    'items': invoice.items.all(),
                                })
                            
                            logger.debug(f"Redirecting to cash sales entry after successful save")
                            return redirect('cash_sales_entry')
                            
                    except Exception as save_error:
                        logger.error(f"Cash transaction save failed: {str(save_error)}")
                        messages.error(request, f'Error saving cash transaction: {str(save_error)}')
                        import traceback
                        traceback.print_exc()
            else:
                # Form validation failed
                logger.debug("Cash form validation failed")
                if not invoice_form.is_valid():
                    logger.debug(f"Cash invoice form errors: {invoice_form.errors}")
                    for field, errors in invoice_form.errors.items():
                        for error in errors:
                            messages.error(request, f"Invoice {field}: {error}")
                            
                if not formset.is_valid():
                    logger.debug(f"Cash formset errors: {formset.errors}")
                    for i, form in enumerate(formset.forms):
                        if form.errors:
                            logger.debug(f"Cash form {i} errors: {form.errors}")
                            for field, errors in form.errors.items():
                                for error in errors:
                                    messages.error(request, f"Item {i+1} - {field}: {error}")
                        
        except Exception as general_error:
            logger.error(f"CRITICAL ERROR in cash_sales_entry: {str(general_error)}")
            import traceback
            traceback.print_exc()
            messages.error(request, f'Unexpected error occurred. Please try again. Error: {str(general_error)}')
    else:
        invoice_form = CashInvoiceForm()
        formset = CashSaleFormSet()
    
    return render(request, 'sales_app/cash_sales_entry.html', {
        'invoice_form': invoice_form,
        'formset': formset
    })


@login_required
@user_passes_test(is_manager)
def cash_receipt_detail(request, invoice_id):
    """Display cash invoice receipt for viewing/printing"""
    cash_invoice = get_object_or_404(CashInvoice, id=invoice_id)
    cash_items = cash_invoice.items.exclude(item__isnull=True).exclude(item__exact="")
    
    return render(request, 'sales_app/cash_receipt_print.html', {
        'invoice': cash_invoice,
        'items': cash_items
    })


@login_required
@user_passes_test(is_manager)
def edit_cash_invoice(request, invoice_id):
    """Edit an existing cash invoice"""
    from django.forms import inlineformset_factory
    
    cash_invoice = get_object_or_404(CashInvoice, id=invoice_id)
    CashSaleFormSet = inlineformset_factory(CashInvoice, CashSale, form=CashSaleForm, extra=0, can_delete=True)
    
    if request.method == 'POST':
        form = CashInvoiceForm(request.POST, instance=cash_invoice)
        formset = CashSaleFormSet(request.POST, instance=cash_invoice)
        
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    # Save updated cash invoice and formset
                    cash_invoice = form.save(commit=False)
                    cash_invoice.save()
                    formset.save()
                    
                    # Recalculate total from all items
                    items_total = sum(item.total_price or 0 for item in cash_invoice.items.all())
                    cash_invoice.total = items_total
                    cash_invoice.save()
                    
                    messages.success(request, f'Cash Invoice {cash_invoice.invoice_no} updated successfully!')
                    from django.http import HttpResponseRedirect
                    from django.urls import reverse
                    return HttpResponseRedirect(reverse('manager_dashboard') + '?department=cash')
                    
            except Exception as e:
                messages.error(request, f'Error updating cash invoice: {str(e)}')
        else:
            # Form validation failed
            if not form.is_valid():
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"Invoice {field}: {error}")
                        
            if not formset.is_valid():
                for i, form_errors in enumerate(formset.errors):
                    if form_errors:
                        for field, errors in form_errors.items():
                            for error in errors:
                                messages.error(request, f"Item {i+1} - {field}: {error}")
                
                for error in formset.non_form_errors():
                    messages.error(request, f"Form error: {error}")
    else:
        form = CashInvoiceForm(instance=cash_invoice)
        formset = CashSaleFormSet(instance=cash_invoice)
        
    return render(request, 'sales_app/edit_cash_invoice.html', {
        'form': form,
        'formset': formset,
        'cash_invoice': cash_invoice
    })