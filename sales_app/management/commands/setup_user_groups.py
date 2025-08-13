# sales_app/management/commands/setup_user_groups.py

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

class Command(BaseCommand):
    help = 'Create user groups (Admin, Manager, Sales) required for RLS security policies'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.HTTP_INFO("🔧 Setting up user groups for RLS security...")
        )
        
        # Define groups and their permissions
        groups_config = {
            'Admin': {
                'description': 'Full system access - can manage all data and users',
                'permissions': 'all'  # Will get all permissions
            },
            'Managers': {
                'description': 'Business operations - sales, accounting, reports',
                'permissions': [
                    # Sales app permissions
                    'sales_app.view_invoice', 'sales_app.add_invoice', 'sales_app.change_invoice',
                    'sales_app.view_cashinvoice', 'sales_app.add_cashinvoice', 'sales_app.change_cashinvoice',
                    'sales_app.view_product', 'sales_app.add_product', 'sales_app.change_product',
                    'sales_app.view_cashproduct', 'sales_app.add_cashproduct', 'sales_app.change_cashproduct',
                    'sales_app.view_sale', 'sales_app.view_cashsale',
                    'sales_app.view_stockmovement', 'sales_app.add_stockmovement', 'sales_app.change_stockmovement',
                    'sales_app.view_adminlog',
                    # Accounting app permissions
                    'accounting_app.view_expense', 'accounting_app.add_expense', 'accounting_app.change_expense',
                    'accounting_app.view_expensecategory',
                    'accounting_app.view_financialforecast', 'accounting_app.add_financialforecast', 'accounting_app.change_financialforecast',
                    'accounting_app.view_profitlosssnapshot', 'accounting_app.view_productperformance',
                    'accounting_app.view_salespersonperformance', 'accounting_app.view_accountingauditlog',
                ]
            },
            'Cashiers': {
                'description': 'Cash operations - create invoices, handle cash transactions',
                'permissions': [
                    # Cash and sales permissions
                    'sales_app.view_invoice', 'sales_app.add_invoice', 'sales_app.change_invoice',
                    'sales_app.view_cashinvoice', 'sales_app.add_cashinvoice', 'sales_app.change_cashinvoice',
                    'sales_app.view_product', 'sales_app.view_cashproduct',
                    'sales_app.view_sale', 'sales_app.add_sale', 'sales_app.change_sale',
                    'sales_app.view_cashsale', 'sales_app.add_cashsale', 'sales_app.change_cashsale',
                    'sales_app.view_stockmovement',
                ]
            }
        }
        
        created_groups = []
        
        for group_name, config in groups_config.items():
            group, created = Group.objects.get_or_create(name=group_name)
            
            if created:
                created_groups.append(group_name)
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Created group: {group_name}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"⚠️  Group already exists: {group_name}")
                )
            
            # Set permissions
            if config['permissions'] == 'all':
                # Give all permissions to Admin
                all_permissions = Permission.objects.all()
                group.permissions.set(all_permissions)
                self.stdout.write(f"   📋 Assigned ALL permissions to {group_name}")
            else:
                # Set specific permissions
                permissions = []
                for perm_code in config['permissions']:
                    try:
                        if '.' in perm_code:
                            app_label, codename = perm_code.split('.', 1)
                            permission = Permission.objects.get(
                                content_type__app_label=app_label,
                                codename=codename
                            )
                            permissions.append(permission)
                    except Permission.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f"   ⚠️  Permission not found: {perm_code}")
                        )
                
                group.permissions.set(permissions)
                self.stdout.write(f"   📋 Assigned {len(permissions)} permissions to {group_name}")
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(f"\n✅ User Groups Setup Complete!")
        )
        
        if created_groups:
            self.stdout.write(
                self.style.HTTP_INFO(f"📊 Created {len(created_groups)} new groups: {', '.join(created_groups)}")
            )
        
        self.stdout.write(
            self.style.HTTP_INFO("\n📝 Next Steps:")
        )
        self.stdout.write("   1. Go to Django Admin (/admin/)")
        self.stdout.write("   2. Navigate to 'Authentication and Authorization' → 'Users'")
        self.stdout.write("   3. Assign users to appropriate groups:")
        self.stdout.write("      • Admin: System administrators")
        self.stdout.write("      • Managers: Business managers") 
        self.stdout.write("      • Cashiers: Cash transaction staff")
        self.stdout.write("   4. Run: python manage.py enable_rls_security")
        
        self.stdout.write(
            self.style.WARNING(
                "\n⚠️  IMPORTANT: Assign at least one user to the 'Admin' group before enabling RLS!"
            )
        )
