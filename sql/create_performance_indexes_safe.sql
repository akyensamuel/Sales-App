-- STRATEGIC PERFORMANCE INDEXES (Non-Concurrent)
-- Creates optimized indexes to improve query performance
-- Safe to run inside Django transactions

-- Optimize invoice queries (addresses slow 237ms queries)
CREATE INDEX IF NOT EXISTS idx_invoice_date_payment_fast 
ON sales_app_invoice (date_of_sale DESC, payment_status)
WHERE date_of_sale >= CURRENT_DATE - INTERVAL '1 year';

-- Optimize recent invoice lookups 
CREATE INDEX IF NOT EXISTS idx_invoice_recent_fast 
ON sales_app_invoice (date_of_sale DESC, invoice_no, customer_name)
WHERE date_of_sale >= CURRENT_DATE - INTERVAL '90 days';

-- Optimize product stock queries (addresses slow 281ms queries)  
CREATE INDEX IF NOT EXISTS idx_product_stock_fast 
ON sales_app_product (stock DESC, name) 
WHERE stock > 0;

-- Optimize sales-invoice joins (addresses slow 261ms queries)
CREATE INDEX IF NOT EXISTS idx_sale_join_fast 
ON sales_app_sale (invoice_id, date_of_sale DESC);

-- Optimize paid sales lookup
CREATE INDEX IF NOT EXISTS idx_invoice_paid_fast 
ON sales_app_invoice (payment_status, date_of_sale DESC)
WHERE payment_status = 'Paid';

-- Optimize cash department performance
CREATE INDEX IF NOT EXISTS idx_cashinvoice_fast 
ON sales_app_cashinvoice (date_of_sale DESC, payment_status)
WHERE date_of_sale >= CURRENT_DATE - INTERVAL '6 months';

-- Optimize user-specific queries
CREATE INDEX IF NOT EXISTS idx_invoice_user_fast 
ON sales_app_invoice (user_id, date_of_sale DESC)
WHERE date_of_sale >= CURRENT_DATE - INTERVAL '3 months';

-- Optimize accounting queries
CREATE INDEX IF NOT EXISTS idx_expense_fast 
ON accounting_app_expense (date DESC, category_id)
WHERE date >= CURRENT_DATE - INTERVAL '1 year';

-- Optimize stock movement tracking
CREATE INDEX IF NOT EXISTS idx_stockmovement_fast 
ON sales_app_stockmovement (product_id, created_at DESC)
WHERE created_at >= CURRENT_DATE - INTERVAL '6 months';

-- Update table statistics for query planner optimization
ANALYZE sales_app_invoice;
ANALYZE sales_app_sale; 
ANALYZE sales_app_product;
ANALYZE sales_app_cashinvoice;
ANALYZE sales_app_cashsale;
ANALYZE accounting_app_expense;
ANALYZE sales_app_stockmovement;

-- Show performance summary
SELECT 'PERFORMANCE_INDEXES_CREATED' as status, COUNT(*) as new_indexes 
FROM pg_indexes 
WHERE schemaname = 'public' AND indexname LIKE '%_fast';
