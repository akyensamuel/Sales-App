-- Database Performance Optimization Script
-- Removes unused indexes identified by Supabase database linter
-- This will improve INSERT/UPDATE performance and reduce storage overhead

-- CAUTION: Always backup your database before running this script
-- Run this during low-traffic periods

-- Authentication System Indexes
DROP INDEX IF EXISTS auth_group_name_a6ea08ec_like;
DROP INDEX IF EXISTS auth_group_permissions_group_id_b120cbf9;
DROP INDEX IF EXISTS auth_group_permissions_permission_id_84c5c92e;
DROP INDEX IF EXISTS auth_user_groups_group_id_97559544;
DROP INDEX IF EXISTS auth_user_groups_user_id_6a12ed8b;
DROP INDEX IF EXISTS auth_user_user_permissions_permission_id_1fbb5f2c;
DROP INDEX IF EXISTS auth_user_username_6821ab7c_like;

-- Django System Indexes
DROP INDEX IF EXISTS django_admin_log_content_type_id_c4bce8eb;
DROP INDEX IF EXISTS django_admin_log_user_id_c564eba6;
DROP INDEX IF EXISTS django_session_expire_date_a5c62663;
DROP INDEX IF EXISTS django_session_session_key_c0390e0f_like;

-- Sales App Admin Log Indexes
DROP INDEX IF EXISTS sales_app_adminlog_user_id_11468d49;
DROP INDEX IF EXISTS sales_app_adminlog_action_ddbd08f3;
DROP INDEX IF EXISTS sales_app_adminlog_action_ddbd08f3_like;
DROP INDEX IF EXISTS sales_app_adminlog_timestamp_90fa9492;
DROP INDEX IF EXISTS sales_app_a_user_id_01c75d_idx;

-- Accounting App Indexes
DROP INDEX IF EXISTS accounting_app_expensecategory_name_4b14535a_like;
DROP INDEX IF EXISTS accounting_app_expense_category_id_0ece805c;

-- Product Performance Indexes
DROP INDEX IF EXISTS accounting__total_r_47fa19_idx;
DROP INDEX IF EXISTS accounting__total_q_4ee0f8_idx;
DROP INDEX IF EXISTS accounting_app_productperformance_product_name_0cdbb826;
DROP INDEX IF EXISTS accounting_app_productperformance_product_name_0cdbb826_like;
DROP INDEX IF EXISTS accounting_app_productperformance_period_start_c78b6144;
DROP INDEX IF EXISTS accounting_app_productperformance_period_end_397661ad;

-- Salesperson Performance Indexes
DROP INDEX IF EXISTS accounting_app_salespersonperformance_period_start_c52b7cd5;
DROP INDEX IF EXISTS accounting_app_salespersonperformance_period_end_b137cc8a;
DROP INDEX IF EXISTS accounting_app_salespersonperformance_user_id_c9efbc48;
DROP INDEX IF EXISTS accounting__total_s_382557_idx;
DROP INDEX IF EXISTS accounting__perform_0fb530_idx;

-- Sales App Invoice Indexes
DROP INDEX IF EXISTS sales_app_invoice_customer_name_fb371111;
DROP INDEX IF EXISTS sales_app_invoice_customer_name_fb371111_like;
DROP INDEX IF EXISTS sales_app_invoice_payment_status_a28fd793_like;
DROP INDEX IF EXISTS sales_app_invoice_total_079827e5;
DROP INDEX IF EXISTS sales_app_i_custome_b7182e_idx;

-- Sales App Product Indexes
DROP INDEX IF EXISTS sales_app_product_name_705a6662;
DROP INDEX IF EXISTS sales_app_product_name_705a6662_like;
DROP INDEX IF EXISTS sales_app_product_stock_1b53325a;
DROP INDEX IF EXISTS sales_app_p_stock_14ffaa_idx;

-- Sales App Sale Indexes
DROP INDEX IF EXISTS sales_app_sale_item_3ab20919;
DROP INDEX IF EXISTS sales_app_sale_item_3ab20919_like;

-- Cash Department Indexes
DROP INDEX IF EXISTS sales_app_c_date_of_b311f0_idx;
DROP INDEX IF EXISTS sales_app_c_custome_7238b6_idx;
DROP INDEX IF EXISTS sales_app_c_user_id_081392_idx;
DROP INDEX IF EXISTS sales_app_c_invoice_2153ea_idx;
DROP INDEX IF EXISTS sales_app_cashinvoice_customer_name_2c087bc6;
DROP INDEX IF EXISTS sales_app_cashinvoice_customer_name_2c087bc6_like;
DROP INDEX IF EXISTS sales_app_cashinvoice_total_54ad83ab;
DROP INDEX IF EXISTS sales_app_cashinvoice_payment_status_fb798e06;
DROP INDEX IF EXISTS sales_app_cashinvoice_payment_status_fb798e06_like;
DROP INDEX IF EXISTS sales_app_cashinvoice_user_id_2ecfd08b;
DROP INDEX IF EXISTS sales_app_cashsale_item_30e2d039;
DROP INDEX IF EXISTS sales_app_cashsale_item_30e2d039_like;

-- Create Optimized Indexes for Commonly Used Queries
-- These indexes should actually be used by your application

-- Optimize invoice queries by date and status
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_invoice_date_status 
ON sales_app_invoice (date_of_sale, payment_status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cashinvoice_date_status 
ON sales_app_cashinvoice (date_of_sale, payment_status);

-- Optimize product searches by stock levels
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_product_stock_low 
ON sales_app_product (stock) WHERE stock <= 10;

-- Optimize sales queries by date
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sale_date 
ON sales_app_sale (date_of_sale);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cashsale_date 
ON sales_app_cashsale (date_of_sale);

-- Optimize admin log queries by timestamp
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_adminlog_timestamp_desc 
ON sales_app_adminlog (timestamp DESC);

-- Optimize expense queries by date and category
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_expense_date_category 
ON accounting_app_expense (date, category_id);

-- Performance monitoring query
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats 
WHERE schemaname = 'public' 
  AND tablename IN (
    'sales_app_invoice', 'sales_app_cashinvoice', 
    'sales_app_product', 'sales_app_sale', 'sales_app_cashsale'
  )
ORDER BY tablename, attname;
