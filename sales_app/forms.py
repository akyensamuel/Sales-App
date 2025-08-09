from django import forms
from .models import Invoice, Sale, Product


# Form for uploading a CSV file
class SalesCSVImportForm(forms.Form):
    csv_file = forms.FileField(
        label="Select CSV file",
        help_text="CSV file with sales data. Headers: Date of Sale,Invoice No,User,Customer Name,CUSTOMER NO,Item,Quantity,Unit Price,total_amount,AMT PAID,BAL TO BE PAID"
    )

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'price', 'stock']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500'}),
            'price': forms.NumberInput(attrs={'class': 'w-full rounded border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500', 'step': '0.01'}),
            'stock': forms.NumberInput(attrs={'class': 'w-full rounded border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500'}),
        }


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        # Remove 'discount' from fields
        fields = ['customer_name', 'date_of_sale', 'notes', 'amount_paid']
        widgets = {
            'customer_name': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_sale': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'amount_paid': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


class SaleForm(forms.ModelForm):
    # --- Override the 'item' field here ---
    # Define it as a ModelChoiceField directly in the form class, not in Meta.widgets
    item = forms.ModelChoiceField(
        queryset=Product.objects.all().order_by('name'),
        empty_label="enter item...",
        required=False,
        # You can optionally specify the widget and its attributes here if needed,
        # although widget_tweaks in the template usually handles styling.
        # widget=forms.Select(attrs={'class': 'form-control'}) 
    )
    # --- End of field override ---

    class Meta:
        model = Sale
        fields = ['item', 'unit_price', 'quantity', 'discount', 'total_price']
        # --- Remove 'item' from widgets dictionary ---
        widgets = {
            # 'item': forms.ModelChoiceField(...), # <-- Remove this line
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'discount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'total_price': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
        }

    # --- Add the clean_item method ---
    def clean_item(self):
        """
        Convert the selected Product instance back to its name string
        for saving into the Sale.item CharField.
        """
        data = self.cleaned_data['item']
        # data is either a Product instance or None
        if data:
            return data.name # Return the name of the product
        return data # Return None if no product was selected

    # --- Add the __init__ method ---
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If this form is for editing an existing Sale instance
        if self.instance and self.instance.pk and self.instance.item:
            try:
                # Try to find the Product object whose name matches the Sale.item string
                product = Product.objects.get(name=self.instance.item)
                # Set the initial value of the 'item' field to this Product instance
                self.initial['item'] = product
            except Product.DoesNotExist:
                # If the name in Sale.item doesn't match any current Product,
                # the field will just be blank/empty_label, which is fine.
                pass
        # Ensure the 'item' field has the correct classes applied via widget_tweaks
        # The widget_tweaks filter in the template handles the 'form-control' class.
        # If you needed to set it here, you could do:
        # if 'item' in self.fields:
        #     self.fields['item'].widget.attrs.update({'class': 'form-control'})
