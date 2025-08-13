# Scripts Directory Index

This directory contains organized utility scripts for the Sales Management System.

## 📁 Directory Structure

### `production/` - Production Deployment Scripts
- **`apply_production_migrations.py`** - Apply database migrations in production
- **`fix_production_cache.py`** - Fix cache issues in production environment
- **`production_csv_import.py`** - Import CSV data in production safely
- **`render_restart_helper.py`** - Helper script for Render.com deployments
- **`reset_db_connection.py`** - Reset database connections for production issues

### `data_import/` - CSV Import & Data Processing
- **`debug_csv.py`** - Debug CSV import issues
- **`optimized_csv_import.py`** - Optimized CSV import with batch processing
- **`quick_csv_import.py`** - Quick CSV import for development

### `testing/` - Testing & Debugging Scripts
- **`test_accounting_filters.py`** - Test accounting template filters
- **`test_analytics.py`** - Test analytics functionality
- **`test_db_connection.py`** - Test database connectivity
- **`test_delete.py`** - Test delete functionality
- **`test_delete_access.py`** - Test delete access permissions
- **`test_manual_delete.py`** - Manual delete testing
- **`test_optimizations.py`** - Test performance optimizations
- **`quick_delete_test.py`** - Quick delete operation testing
- **`fix_data_integrity.py`** - Fix data integrity issues
- **`fix_print_statements.py`** - Fix print statement issues

## 🚀 Usage

### Production Scripts
```bash
# Apply migrations safely in production
python scripts/production/apply_production_migrations.py

# Import CSV data in production
python scripts/production/production_csv_import.py
```

### Data Import Scripts
```bash
# Debug CSV import issues
python scripts/data_import/debug_csv.py

# Run optimized import
python scripts/data_import/optimized_csv_import.py
```

### Testing Scripts
```bash
# Test database connections
python scripts/testing/test_db_connection.py

# Test specific functionality
python scripts/testing/test_[functionality].py
```

## ⚠️ Important Notes

1. **Production scripts** should only be run in production environment
2. **Testing scripts** are safe to run in development
3. **Data import scripts** should be used with caution on live data
4. Always backup your database before running production scripts
5. Check script documentation within each file for specific usage instructions

## 📚 Related Documentation

- **Security Setup**: `../docs/SECURITY_FIX_WALKTHROUGH.md`
- **Testing Guide**: `../docs/TESTING_GUIDE.md`
- **Production Deployment**: `../docs/PRODUCTION_FIX_LOG.md`
