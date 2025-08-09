from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.accounting_login, name='accounting_login'),
    path('', views.accounting_dashboard, name='accounting_dashboard'),
    path('dashboard/', views.accounting_dashboard, name='dashboard_home'),
    
    # Expense Management
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/create/', views.expense_create, name='expense_create'),
    path('expenses/<int:expense_id>/edit/', views.expense_edit, name='expense_edit'),
    path('expenses/<int:expense_id>/delete/', views.expense_delete, name='expense_delete'),
    
    # Reports
    path('reports/profit-loss/', views.profit_loss_report, name='profit_loss_report'),
    path('reports/revenue/', views.revenue_tracking, name='revenue_tracking'),
    
    # Analytics
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    path('analytics/products/', views.product_performance, name='product_performance'),
    path('analytics/salespeople/', views.salesperson_performance, name='salesperson_performance'),
    path('analytics/products/<str:product_name>/trends/', views.product_trends, name='product_trends'),
    path('analytics/salespeople/<int:user_id>/trends/', views.salesperson_trends, name='salesperson_trends'),
    path('api/analytics/', views.analytics_api, name='analytics_api'),
    
    # Legacy routes for compatibility
    path('forecast_dashboard/', views.forecast_dashboard, name='forecast_dashboard'),
]