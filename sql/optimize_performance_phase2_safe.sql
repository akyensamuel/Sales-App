-- PHASE 2 SAFE: Advanced Performance Optimization
-- Remove remaining unused indexes safely (avoid primary keys)
-- Focus on non-essential unused indexes and create strategic performance indexes

BEGIN;

-- Remove remaining unused foreign key indexes (safe to drop)
DROP INDEX IF EXISTS auth_group_permissions_group_id_b120cbf9;
DROP INDEX IF EXISTS auth_group_permissions_permission_id_84c5c92e;
DROP INDEX IF EXISTS auth_user_groups_group_id_97559544;
DROP INDEX IF EXISTS auth_user_groups_user_id_6a12ed8b;
DROP INDEX IF EXISTS auth_user_user_permissions_permission_id_1fbb5f2c;

-- Remove unused Django admin indexes (safe to drop)
DROP INDEX IF EXISTS django_admin_log_content_type_id_c4bce8eb;
DROP INDEX IF EXISTS django_admin_log_user_id_c564eba6;
DROP INDEX IF EXISTS django_session_expire_date_a5c62663;

-- Remove unused unique constraint indexes (not primary keys)
DROP INDEX IF EXISTS auth_group_permissions_group_id_permission_id_0cd325b0_uniq;
DROP INDEX IF EXISTS auth_user_user_permissions_user_id_permission_id_14a6b632_uniq;
DROP INDEX IF EXISTS auth_permission_content_type_id_codename_01ab375a_uniq;

-- Remove unused composite indexes for accounting
DROP INDEX IF EXISTS accounting_app_productpe_product_name_period_star_0d382705_uniq;
DROP INDEX IF EXISTS accounting_app_salespers_user_id_period_start_per_f688f901_uniq;

COMMIT;

-- CREATE STRATEGIC PERFORMANCE INDEXES
-- These will dramatically improve query performance

BEGIN;

-- Optimize invoice queries (addresses slow 237ms queries)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_invoice_date_payment_optimized 
ON sales_app_invoice (date_of_sale DESC, payment_status)
WHERE date_of_sale >= CURRENT_DATE - INTERVAL '1 year';

-- Optimize recent invoice lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_invoice_recent_activity 
ON sales_app_invoice (date_of_sale DESC) 
WHERE payment_status IN ('Paid', 'Pending', 'Overdue');

-- Optimize product stock queries (addresses slow 281ms queries)  
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_product_active_stock 
ON sales_app_product (stock DESC, name) 
WHERE stock > 0;

-- Optimize sales-invoice joins (addresses slow 261ms queries)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sale_invoice_performance 
ON sales_app_sale (invoice_id, date_of_sale DESC)
INCLUDE (quantity, price, item);

-- Optimize cash department performance
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cashinvoice_performance 
ON sales_app_cashinvoice (date_of_sale DESC, payment_status)
WHERE date_of_sale >= CURRENT_DATE - INTERVAL '6 months';

-- Optimize user activity tracking
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_invoice_user_recent 
ON sales_app_invoice (user_id, date_of_sale DESC)
WHERE date_of_sale >= CURRENT_DATE - INTERVAL '3 months';

-- Optimize accounting queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_expense_date_category_active 
ON accounting_app_expense (date DESC, category_id)
WHERE date >= CURRENT_DATE - INTERVAL '1 year';

COMMIT;

-- Update table statistics for query planner optimization
ANALYZE sales_app_invoice;
ANALYZE sales_app_sale; 
ANALYZE sales_app_product;
ANALYZE sales_app_cashinvoice;
ANALYZE sales_app_cashsale;
ANALYZE accounting_app_expense;

-- Performance verification query
SELECT 
    'PHASE_2_SAFE_COMPLETE' as status,
    COUNT(*) as total_indexes,
    SUM(CASE WHEN idx_scan = 0 THEN 1 ELSE 0 END) as unused_indexes,
    ROUND((SUM(CASE WHEN idx_scan > 0 THEN 1 ELSE 0 END)::decimal / COUNT(*)) * 100, 1) as efficiency_percent
FROM pg_stat_user_indexes 
WHERE schemaname = 'public';
