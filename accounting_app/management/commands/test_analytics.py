from django.core.management.base import BaseCommand
from accounting_app.analytics import AnalyticsEngine
from accounting_app.models import ProductPerformance, SalesPersonPerformance
from sales_app.models import Sale, Product
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Test analytics functionality'

    def handle(self, *args, **options):
        self.stdout.write("🔍 Testing Analytics System...")
        
        # Test AnalyticsEngine initialization
        engine = AnalyticsEngine()
        self.stdout.write(self.style.SUCCESS("✅ AnalyticsEngine initialized successfully"))
        
        # Test getting product performance
        try:
            product_data = engine.get_product_performance()
            self.stdout.write(self.style.SUCCESS(f"✅ Product performance data retrieved: {len(product_data)} products"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Product performance error: {e}"))
            
        # Test getting salesperson performance
        try:
            sales_data = engine.get_salesperson_performance()
            self.stdout.write(self.style.SUCCESS(f"✅ Salesperson performance data retrieved: {len(sales_data)} staff members"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Salesperson performance error: {e}"))
        
        # Test model creation
        try:
            # Check database content
            products = Product.objects.all()
            self.stdout.write(f"📦 Found {products.count()} products in database")
            
            # Check users with required roles
            managers = User.objects.filter(groups__name='Managers')
            cashiers = User.objects.filter(groups__name='Cashiers')
            self.stdout.write(f"👥 Found {managers.count()} managers, {cashiers.count()} cashiers")
            
            # Test model access
            performance_count = ProductPerformance.objects.count()
            staff_count = SalesPersonPerformance.objects.count()
            self.stdout.write(f"📊 ProductPerformance records: {performance_count}")
            self.stdout.write(f"👨‍💼 SalesPersonPerformance records: {staff_count}")
            
            self.stdout.write(self.style.SUCCESS("✅ All analytics models accessible"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Model test error: {e}"))
            
        self.stdout.write(self.style.SUCCESS("\n🎉 Analytics system test completed!"))
