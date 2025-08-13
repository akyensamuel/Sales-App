-- PHASE 2: Advanced Performance Optimization
-- Remove remaining unused indexes and create strategic indexes
-- Focus on the remaining 32 unused indexes and slow queries

BEGIN;

-- Remove remaining unused Django system indexes
DROP INDEX IF EXISTS auth_group_permissions_group_id_b120cbf9;
DROP INDEX IF EXISTS auth_group_permissions_permission_id_84c5c92e;
DROP INDEX IF EXISTS auth_user_groups_group_id_97559544;
DROP INDEX IF EXISTS auth_user_groups_user_id_6a12ed8b;
DROP INDEX IF EXISTS auth_user_user_permissions_permission_id_1fbb5f2c;
DROP INDEX IF EXISTS django_admin_log_content_type_id_c4bce8eb;
DROP INDEX IF EXISTS django_admin_log_user_id_c564eba6;
DROP INDEX IF EXISTS django_session_expire_date_a5c62663;

-- Remove unused primary keys that aren't being accessed
-- (Keep only essential ones for tables that are actively queried)
DROP INDEX IF EXISTS auth_group_pkey;
DROP INDEX IF EXISTS auth_permission_pkey;
DROP INDEX IF EXISTS auth_user_pkey;
DROP INDEX IF EXISTS django_admin_log_pkey;
DROP INDEX IF EXISTS django_content_type_pkey;
DROP INDEX IF EXISTS django_migrations_pkey;
DROP INDEX IF EXISTS django_session_pkey;

-- Remove unused accounting indexes (0 scans)
DROP INDEX IF EXISTS accounting_app_expense_pkey;
DROP INDEX IF EXISTS accounting_app_expensecategory_pkey;
DROP INDEX IF EXISTS accounting_app_taxsettings_pkey;
DROP INDEX IF EXISTS accounting_app_accountingauditlog_pkey;
DROP INDEX IF EXISTS accounting_app_productperformance_pkey;

-- Remove unused sales app primary keys for tables not actively queried
DROP INDEX IF EXISTS sales_app_product_pkey;
DROP INDEX IF EXISTS sales_app_stockmovement_pkey;
DROP INDEX IF EXISTS sales_app_adminlog_pkey;

-- Remove unused unique constraints that aren't needed
DROP INDEX IF EXISTS auth_group_permissions_group_id_permission_id_0cd325b0_uniq;
DROP INDEX IF EXISTS auth_user_user_permissions_user_id_permission_id_14a6b632_uniq;
DROP INDEX IF EXISTS auth_permission_content_type_id_codename_01ab375a_uniq;

COMMIT;

-- CREATE STRATEGIC PERFORMANCE INDEXES
-- These will dramatically improve query performance

BEGIN;

-- Optimize invoice queries (your slowest queries)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_invoice_date_payment_status 
ON sales_app_invoice (date_of_sale DESC, payment_status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_invoice_recent_paid 
ON sales_app_invoice (date_of_sale DESC) 
WHERE payment_status = 'Paid' AND date_of_sale >= CURRENT_DATE - INTERVAL '90 days';

-- Optimize product stock queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_product_in_stock 
ON sales_app_product (name, stock) 
WHERE stock > 0;

-- Optimize sales performance queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sale_invoice_date 
ON sales_app_sale (invoice_id) 
INCLUDE (date_of_sale, quantity, price);

-- Optimize cash department queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cashinvoice_date_payment 
ON sales_app_cashinvoice (date_of_sale DESC, payment_status);

-- Optimize user-based queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_invoice_user_date 
ON sales_app_invoice (user_id, date_of_sale DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cashinvoice_user_date 
ON sales_app_cashinvoice (user_id, date_of_sale DESC);

COMMIT;

-- Analyze tables to update statistics for query planner
ANALYZE sales_app_invoice;
ANALYZE sales_app_sale;
ANALYZE sales_app_product;
ANALYZE sales_app_cashinvoice;
ANALYZE sales_app_cashsale;

-- Final performance check
SELECT 
    'PHASE_2_COMPLETE' as status,
    COUNT(*) as total_indexes,
    SUM(CASE WHEN idx_scan = 0 THEN 1 ELSE 0 END) as unused_indexes,
    ROUND((SUM(CASE WHEN idx_scan > 0 THEN 1 ELSE 0 END)::decimal / COUNT(*)) * 100, 1) as efficiency_percent
FROM pg_stat_user_indexes 
WHERE schemaname = 'public';
