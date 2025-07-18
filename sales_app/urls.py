from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='sales_root'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('sales_entry/', views.sales_entry, name='sales_entry'),
    path('manager_dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('edit_sale/<int:sale_id>/', views.edit_sale, name='edit_sale'),
    path('invoice/<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),
    path('edit_invoice/<int:invoice_id>/', views.edit_invoice, name='edit_invoice'),
    path('receipt_print/<int:invoice_id>/', views.invoice_detail, {'print_mode': True}, name='receipt_print'),
]