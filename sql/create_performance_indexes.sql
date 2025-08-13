-- STRATEGIC PERFORMANCE INDEXES
-- Creates optimized indexes to improve query performance
-- No transaction blocks needed for CONCURRENTLY operations

-- Optimize invoice queries (addresses slow 237ms queries)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_invoice_date_payment_fast 
ON sales_app_invoice (date_of_sale DESC, payment_status)
WHERE date_of_sale >= CURRENT_DATE - INTERVAL '1 year';

-- Optimize recent invoice lookups with covering index
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_invoice_recent_fast 
ON sales_app_invoice (date_of_sale DESC) 
INCLUDE (invoice_no, customer_name, total, payment_status)
WHERE date_of_sale >= CURRENT_DATE - INTERVAL '90 days';

-- Optimize product stock queries (addresses slow 281ms queries)  
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_product_stock_fast 
ON sales_app_product (stock DESC, name) 
WHERE stock > 0;

-- Optimize sales-invoice joins (addresses slow 261ms queries)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sale_join_fast 
ON sales_app_sale (invoice_id, date_of_sale DESC)
INCLUDE (quantity, price, item);

-- Optimize paid sales lookup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_invoice_paid_fast 
ON sales_app_invoice (payment_status, date_of_sale DESC)
WHERE payment_status = 'Paid';

-- Optimize cash department performance
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cashinvoice_fast 
ON sales_app_cashinvoice (date_of_sale DESC, payment_status)
WHERE date_of_sale >= CURRENT_DATE - INTERVAL '6 months';

-- Optimize user-specific queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_invoice_user_fast 
ON sales_app_invoice (user_id, date_of_sale DESC)
WHERE date_of_sale >= CURRENT_DATE - INTERVAL '3 months';

-- Optimize accounting queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_expense_fast 
ON accounting_app_expense (date DESC, category_id)
WHERE date >= CURRENT_DATE - INTERVAL '1 year';

-- Optimize stock movement tracking
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stockmovement_fast 
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

-- Performance verification
SELECT 
    'STRATEGIC_INDEXES_CREATED' as status,
    COUNT(*) as total_indexes,
    SUM(CASE WHEN idx_scan = 0 THEN 1 ELSE 0 END) as unused_indexes,
    ROUND((SUM(CASE WHEN idx_scan > 0 THEN 1 ELSE 0 END)::decimal / COUNT(*)) * 100, 1) as efficiency_percent
FROM pg_stat_user_indexes 
WHERE schemaname = 'public';

-- Show newly created performance indexes
SELECT 
    indexname,
    tablename,
    indexdef
FROM pg_indexes 
WHERE schemaname = 'public' 
  AND indexname LIKE '%_fast'
ORDER BY tablename, indexname;
