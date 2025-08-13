# Data Directory

This directory contains CSV files and data imports for the Sales Management System.

## 📁 Contents

- **`SALES TABLE - SALES_TABLE.csv`** - Main sales data import file

## 🔧 Usage

### CSV Import Process
1. Place your CSV files in this directory
2. Use the import scripts from `../scripts/data_import/`
3. Monitor the import process through Django admin

### Import Scripts
```bash
# Debug CSV format issues
python scripts/data_import/debug_csv.py

# Run optimized import (recommended)
python scripts/data_import/optimized_csv_import.py

# Quick import for testing
python scripts/data_import/quick_csv_import.py
```

## 📋 CSV Format Requirements

### Sales Data CSV
Expected columns:
- Customer Name
- Phone Number  
- Date (DD/M/YYYY format)
- Product/Service details
- Amounts and pricing

## ⚠️ Important Notes

1. **Backup first**: Always backup your database before importing
2. **Date format**: Use DD/M/YYYY format (e.g., 15/3/2024)
3. **File size**: Large files should use the optimized import script
4. **Encoding**: UTF-8 encoding recommended for special characters

## 🔄 Data Processing

The system includes:
- **Date correction**: Fixes imported date issues
- **Batch processing**: Handles large datasets efficiently  
- **Data validation**: Checks for required fields
- **Error logging**: Tracks import issues for debugging

## 📚 Related Documentation

- **Import Guide**: `../docs/features/CSV_IMPORT_GUIDE.md`
- **Data Fixes**: `../docs/PRODUCTION_FIX_LOG.md`
- **Testing**: `../scripts/testing/`
