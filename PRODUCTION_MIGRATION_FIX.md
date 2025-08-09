# Production Migration Fix Guide

## Issue
The production database is missing the `customer_phone` column in the `sales_app_invoice` table, causing a ProgrammingError.

## Root Cause
The production database schema is out of sync with the current model definitions. The migration `0012_invoice_customer_phone.py` and `0013_cashproduct_cashinvoice_cashsale_and_more.py` haven't been applied in production.

## Solution

### Method 1: Via Render Dashboard (Recommended)
1. Go to your Render service dashboard
2. Navigate to the "Shell" tab
3. Run the following commands:

```bash
cd /opt/render/project/src
python manage.py migrate sales_app
```

### Method 2: Via Render CLI
If you have Render CLI installed:

```bash
render shell <your-service-name>
cd /opt/render/project/src
python manage.py migrate sales_app
```

### Method 3: Add Migration Command to Deployment
Add this to your deployment script or render.yaml:

```bash
python manage.py migrate --noinput
```

## Verification
After running the migration, you can verify by checking the applied migrations:

```bash
python manage.py showmigrations sales_app
```

## Expected Output
You should see checkmarks next to these migrations:
- [X] 0012_invoice_customer_phone
- [X] 0013_cashproduct_cashinvoice_cashsale_and_more

## Production Safety
These migrations are safe to run in production as they:
1. Add new columns with NULL=True (non-breaking)
2. Create new tables (additive changes)
3. Don't modify existing data

## Files Affected
- `sales_app_invoice` table: gains `customer_phone` column
- New tables: `sales_app_cashproduct`, `sales_app_cashinvoice`, `sales_app_cashsale`

## Emergency Fix
If migrations fail, you can temporarily comment out the customer_phone usage in the manager_dashboard view, but this is not recommended for long-term use.
