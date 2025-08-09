# Production Migration Commands
# ============================
# Use these commands to apply migrations to production database

# 1. FIRST - Check what migrations are pending (safe, read-only)
python manage.py showmigrations

# 2. SECOND - See the migration plan (safe, read-only) 
python manage.py migrate --plan

# 3. THIRD - Apply specific app migrations (if you only want sales_app)
python manage.py migrate sales_app

# 4. FOURTH - Apply all pending migrations
python manage.py migrate

# 5. VERIFY - Check that the customer_phone column exists
python manage.py dbshell
# Then in the database shell, run:
# \d sales_app_invoice
# (or for PostgreSQL: SELECT column_name FROM information_schema.columns WHERE table_name = 'sales_app_invoice';)

# ALTERNATIVE: Use the custom management command
python manage.py fix_production_schema --check-only  # Check only
python manage.py fix_production_schema               # Apply fixes

# EMERGENCY: If you need to rollback (BE VERY CAREFUL)
# python manage.py migrate sales_app 0011  # Rollback to before customer_phone
