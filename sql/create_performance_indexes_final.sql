-- STRATEGIC PERFORMANCE INDEXES (Correct Column Names)
-- Based on actual Django model field names
-- Optimizes the slow queries identified in performance testing

-- Invoice table optimizations (addresses 237ms slow queries)
CREATE INDEX IF NOT EXISTS idx_invoice_date_payment_optimized 
ON sales_app_invoice (date_of_sale DESC, payment_status);

CREATE INDEX IF NOT EXISTS idx_invoice_customer_date_optimized 
ON sales_app_invoice (customer_name, date_of_sale DESC);

CREATE INDEX IF NOT EXISTS idx_invoice_user_date_optimized 
ON sales_app_invoice (user_id, date_of_sale DESC);

-- Sale table optimizations (addresses 261ms slow queries)
CREATE INDEX IF NOT EXISTS idx_sale_invoice_item_optimized 
ON sales_app_sale (invoice_id, item);

CREATE INDEX IF NOT EXISTS idx_sale_item_quantity_optimized 
ON sales_app_sale (item, quantity DESC);

-- Product table optimizations (addresses 281ms slow queries)
CREATE INDEX IF NOT EXISTS idx_product_stock_name_optimized 
ON sales_app_product (stock DESC, name);

CREATE INDEX IF NOT EXISTS idx_product_name_stock_optimized 
ON sales_app_product (name, stock);

-- Cash Invoice table optimizations
CREATE INDEX IF NOT EXISTS idx_cashinvoice_date_payment_optimized 
ON sales_app_cashinvoice (date_of_sale DESC, payment_status);

CREATE INDEX IF NOT EXISTS idx_cashinvoice_user_date_optimized 
ON sales_app_cashinvoice (user_id, date_of_sale DESC);

-- Cash Sale table optimizations
CREATE INDEX IF NOT EXISTS idx_cashsale_invoice_item_optimized 
ON sales_app_cashsale (invoice_id, item);

-- Stock Movement optimizations
CREATE INDEX IF NOT EXISTS idx_stockmovement_product_date_optimized 
ON sales_app_stockmovement (product_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_stockmovement_type_date_optimized 
ON sales_app_stockmovement (movement_type, created_at DESC);

-- Admin Log optimizations
CREATE INDEX IF NOT EXISTS idx_adminlog_user_timestamp_optimized 
ON sales_app_adminlog (user_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_adminlog_action_timestamp_optimized 
ON sales_app_adminlog (action, timestamp DESC);

-- Update table statistics for query planner
ANALYZE sales_app_invoice;
ANALYZE sales_app_sale; 
ANALYZE sales_app_product;
ANALYZE sales_app_cashinvoice;
ANALYZE sales_app_cashsale;
ANALYZE sales_app_stockmovement;
ANALYZE sales_app_adminlog;

-- Performance summary
SELECT 'OPTIMIZED_INDEXES_CREATED' as status, COUNT(*) as new_indexes 
FROM pg_indexes 
WHERE schemaname = 'public' AND indexname LIKE '%_optimized';
