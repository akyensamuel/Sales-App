-- STRATEGIC PERFORMANCE INDEXES (Simple Version)
-- Creates optimized indexes to improve query performance
-- No complex WHERE clauses to avoid immutable function issues

-- Optimize invoice queries (addresses slow 237ms queries)
CREATE INDEX IF NOT EXISTS idx_invoice_date_payment_simple 
ON sales_app_invoice (date_of_sale DESC, payment_status);

-- Optimize recent invoice lookups 
CREATE INDEX IF NOT EXISTS idx_invoice_date_desc_simple 
ON sales_app_invoice (date_of_sale DESC, invoice_no);

-- Optimize product stock queries (addresses slow 281ms queries)  
CREATE INDEX IF NOT EXISTS idx_product_stock_simple 
ON sales_app_product (stock DESC, name);

-- Optimize sales-invoice joins (addresses slow 261ms queries)
CREATE INDEX IF NOT EXISTS idx_sale_invoice_date_simple 
ON sales_app_sale (invoice_id, date_of_sale DESC);

-- Optimize paid sales lookup
CREATE INDEX IF NOT EXISTS idx_invoice_payment_date_simple 
ON sales_app_invoice (payment_status, date_of_sale DESC);

-- Optimize cash department performance
CREATE INDEX IF NOT EXISTS idx_cashinvoice_date_payment_simple 
ON sales_app_cashinvoice (date_of_sale DESC, payment_status);

-- Optimize user-specific queries
CREATE INDEX IF NOT EXISTS idx_invoice_user_date_simple 
ON sales_app_invoice (user_id, date_of_sale DESC);

-- Optimize accounting queries
CREATE INDEX IF NOT EXISTS idx_expense_date_category_simple 
ON accounting_app_expense (date DESC, category_id);

-- Optimize stock movement tracking
CREATE INDEX IF NOT EXISTS idx_stockmovement_product_date_simple 
ON sales_app_stockmovement (product_id, created_at DESC);

-- Create composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_invoice_customer_date_simple 
ON sales_app_invoice (customer_name, date_of_sale DESC);

CREATE INDEX IF NOT EXISTS idx_sale_item_quantity_simple 
ON sales_app_sale (item, quantity DESC);

-- Update table statistics for query planner optimization
ANALYZE sales_app_invoice;
ANALYZE sales_app_sale; 
ANALYZE sales_app_product;
ANALYZE sales_app_cashinvoice;
ANALYZE sales_app_cashsale;
ANALYZE accounting_app_expense;
ANALYZE sales_app_stockmovement;

-- Show performance summary
SELECT 'SIMPLE_PERFORMANCE_INDEXES_CREATED' as status, COUNT(*) as new_indexes 
FROM pg_indexes 
WHERE schemaname = 'public' AND indexname LIKE '%_simple';
