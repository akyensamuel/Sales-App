from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from decimal import Decimal

class Invoice(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('unpaid', 'Unpaid'),
        ('partial', 'Partially Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    
    invoice_no = models.CharField(max_length=20, unique=True, editable=False, null=True, blank=True, db_index=True)
    customer_name = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    customer_phone = models.CharField(max_length=20, null=True, blank=True, help_text="Customer's phone number")
    date_of_sale = models.DateField(default=timezone.now, null=True, blank=True, db_index=True)
    due_date = models.DateField(null=True, blank=True, db_index=True)
    notes = models.TextField(blank=True, null=True)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True, db_index=True)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='unpaid', db_index=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    
    class Meta:
        ordering = ['-date_of_sale', '-id']
        indexes = [
            models.Index(fields=['date_of_sale', 'payment_status']),
            models.Index(fields=['customer_name', 'date_of_sale']),
            models.Index(fields=['user', 'date_of_sale']),
        ]

    @property
    def balance(self):
        """Calculate the remaining balance (total - amount_paid)"""
        return (self.total or 0) - (self.amount_paid or 0)
    
    def update_payment_status(self):
        """Automatically update payment status based on amount paid"""
        if self.amount_paid == 0:
            self.payment_status = 'unpaid'
        elif self.amount_paid >= self.total:
            self.payment_status = 'paid'
        else:
            self.payment_status = 'partial'
        
        # Check for overdue status
        if self.due_date and timezone.now().date() > self.due_date and self.payment_status != 'paid':
            self.payment_status = 'overdue'

    def save(self, *args, **kwargs):
        if not self.invoice_no:
            today = timezone.now().strftime('%Y%m%d')
            prefix = f"INV-{today}-"
            last_invoice = Invoice.objects.filter(invoice_no__startswith=prefix).order_by('-invoice_no').first()
            if last_invoice:
                last_number = int(last_invoice.invoice_no[-3:])
                next_number = f"{last_number+1:03d}"
            else:
                next_number = "001"
            self.invoice_no = f"{prefix}{next_number}"
        
        # Automatically update payment status when saving
        self.update_payment_status()
        
        super().save(*args, **kwargs)

    def __str__(self):
        return self.invoice_no


class AdminLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    action = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, null=True, blank=True, db_index=True)
    details = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.action} at {self.timestamp}"

class Product(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.IntegerField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name', 'stock']),
            models.Index(fields=['stock']),  # For low stock queries
        ]

    def __str__(self):
        return self.name


class Sale(models.Model):
    invoice = models.ForeignKey('Invoice', on_delete=models.CASCADE, related_name='items', null=True, blank=True)
    item = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    quantity = models.IntegerField(default=1, null=True, blank=True)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)

    class Meta:
        ordering = ['-id']
        indexes = [
            models.Index(fields=['invoice', 'item']),
        ]

    def __str__(self):
        return f"{self.item} - {self.quantity} units"

class StockMovement(models.Model):
    """
    Track all stock movements for audit trail
    """
    MOVEMENT_TYPES = [
        ('SALE', 'Sale'),
        ('PURCHASE', 'Purchase'),
        ('ADJUSTMENT', 'Stock Adjustment'),
        ('RETURN', 'Return'),
        ('RESTOCK', 'Restock'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_movements')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity_change = models.IntegerField()  # Positive for additions, negative for reductions
    stock_before = models.IntegerField()  # Stock level before this movement
    stock_after = models.IntegerField()   # Stock level after this movement
    reference = models.CharField(max_length=100, blank=True, null=True)  # Invoice number, etc.
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.product.name} - {self.movement_type}: {self.quantity_change}"


class CashProduct(models.Model):
    """
    Products for cash department with rate-based pricing
    """
    name = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    rate = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, 
                               help_text="Rate to be applied to amount for pricing calculation")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        ordering = ['name']
        
    def calculate_price(self, amount):
        """
        Calculate price based on rate and amount
        Special handling for SUBSCRIBER WITHDRAWAL: only applies rate when amount >= 6000, otherwise 0
        """
        if self.name == "SUBSCRIBER WITHDRAWAL":
            if amount >= 6000:
                return Decimal('0.001') * Decimal(str(amount))
            else:
                return Decimal('0')
        return (self.rate or Decimal('0')) * Decimal(str(amount))

    def __str__(self):
        return self.name


class CashInvoice(models.Model):
    """
    Cash department invoices - no balance field needed as these are cash transactions
    """
    PAYMENT_STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    
    invoice_no = models.CharField(max_length=20, unique=True, editable=False, null=True, blank=True, db_index=True)
    customer_name = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    customer_phone = models.CharField(max_length=20, null=True, blank=True, help_text="Customer's phone number")
    date_of_sale = models.DateField(default=timezone.now, null=True, blank=True, db_index=True)
    notes = models.TextField(blank=True, null=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True, db_index=True)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='paid', db_index=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cash_invoices')
    
    class Meta:
        ordering = ['-date_of_sale', '-id']
        indexes = [
            models.Index(fields=['date_of_sale', 'payment_status']),
            models.Index(fields=['customer_name', 'date_of_sale']),
            models.Index(fields=['user', 'date_of_sale']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.invoice_no:
            today = timezone.now().strftime('%Y%m%d')
            prefix = f"CASH-{today}-"
            last_invoice = CashInvoice.objects.filter(invoice_no__startswith=prefix).order_by('-invoice_no').first()
            if last_invoice:
                last_number = int(last_invoice.invoice_no[-3:])
                next_number = f"{last_number+1:03d}"
            else:
                next_number = "001"
            self.invoice_no = f"{prefix}{next_number}"
        
        super().save(*args, **kwargs)

    def __str__(self):
        return self.invoice_no


class CashSale(models.Model):
    """
    Cash sale items with amount-based pricing
    """
    invoice = models.ForeignKey('CashInvoice', on_delete=models.CASCADE, related_name='items', null=True, blank=True)
    item = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True, 
                                help_text="Base amount for rate calculation")
    rate = models.DecimalField(max_digits=10, decimal_places=4, default=0, null=True, blank=True,
                              help_text="Rate applied to amount")
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)

    class Meta:
        ordering = ['-id']
        indexes = [
            models.Index(fields=['invoice', 'item']),
        ]
    
    def save(self, *args, **kwargs):
        # Calculate total price based on rate and amount with special SUBSCRIBER WITHDRAWAL logic
        if self.item == "SUBSCRIBER WITHDRAWAL":
            if (self.amount or 0) >= 6000:
                self.rate = Decimal('0.001')
                self.total_price = (self.amount or Decimal('0')) * Decimal('0.001')
            else:
                self.rate = Decimal('0')
                self.total_price = Decimal('0')
        else:
            self.total_price = (self.rate or Decimal('0')) * (self.amount or Decimal('0'))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item} - Amount: {self.amount}"