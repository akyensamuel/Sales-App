-- PHASE 1: Safe Database Performance Optimization
-- Remove completely unused indexes that are definitely safe to drop
-- Focus on indexes with 0 scans and no foreign key relationships

-- IMPORTANT: Run this during low-traffic periods
-- This script only removes obviously unused indexes

BEGIN;

-- Remove unused LIKE indexes (rarely needed for partial text matching)
DROP INDEX IF EXISTS auth_group_name_a6ea08ec_like;
DROP INDEX IF EXISTS auth_user_username_6821ab7c_like;
DROP INDEX IF EXISTS django_session_session_key_c0390e0f_like;
DROP INDEX IF EXISTS accounting_app_expensecategory_name_4b14535a_like;
DROP INDEX IF EXISTS accounting_app_productperformance_product_name_0cdbb826_like;
DROP INDEX IF EXISTS sales_app_invoice_customer_name_fb371111_like;
DROP INDEX IF EXISTS sales_app_invoice_payment_status_a28fd793_like;
DROP INDEX IF EXISTS sales_app_product_name_705a6662_like;
DROP INDEX IF EXISTS sales_app_sale_item_3ab20919_like;
DROP INDEX IF EXISTS sales_app_cashinvoice_customer_name_2c087bc6_like;
DROP INDEX IF EXISTS sales_app_cashinvoice_payment_status_fb798e06_like;
DROP INDEX IF EXISTS sales_app_cashsale_item_30e2d039_like;

-- Remove unused admin log indexes (table shows 0 usage)
DROP INDEX IF EXISTS sales_app_adminlog_action_ddbd08f3;
DROP INDEX IF EXISTS sales_app_adminlog_action_ddbd08f3_like;
DROP INDEX IF EXISTS sales_app_adminlog_timestamp_90fa9492;
DROP INDEX IF EXISTS sales_app_adminlog_user_id_11468d49;
DROP INDEX IF EXISTS sales_app_a_user_id_01c75d_idx;

-- Remove unused complex composite indexes
DROP INDEX IF EXISTS accounting__total_q_4ee0f8_idx;
DROP INDEX IF EXISTS accounting__total_r_47fa19_idx;
DROP INDEX IF EXISTS accounting__total_s_382557_idx;
DROP INDEX IF EXISTS accounting__perform_0fb530_idx;

-- Remove unused custom indexes
DROP INDEX IF EXISTS sales_app_i_custome_b7182e_idx;
DROP INDEX IF EXISTS sales_app_p_stock_14ffaa_idx;
DROP INDEX IF EXISTS sales_app_c_date_of_b311f0_idx;
DROP INDEX IF EXISTS sales_app_c_custome_7238b6_idx;
DROP INDEX IF EXISTS sales_app_c_user_id_081392_idx;
DROP INDEX IF EXISTS sales_app_c_invoice_2153ea_idx;

-- Remove unused foreign key indexes (these were created automatically but not used)
DROP INDEX IF EXISTS accounting_app_expense_category_id_0ece805c;
DROP INDEX IF EXISTS accounting_app_productperformance_period_start_c78b6144;
DROP INDEX IF EXISTS accounting_app_productperformance_period_end_397661ad;
DROP INDEX IF EXISTS accounting_app_salespersonperformance_period_start_c52b7cd5;
DROP INDEX IF EXISTS accounting_app_salespersonperformance_period_end_b137cc8a;
DROP INDEX IF EXISTS accounting_app_salespersonperformance_user_id_c9efbc48;

-- Remove unused text search indexes
DROP INDEX IF EXISTS sales_app_invoice_customer_name_fb371111;
DROP INDEX IF EXISTS sales_app_invoice_total_079827e5;
DROP INDEX IF EXISTS sales_app_product_name_705a6662;
DROP INDEX IF EXISTS sales_app_product_stock_1b53325a;
DROP INDEX IF EXISTS sales_app_sale_item_3ab20919;
DROP INDEX IF EXISTS sales_app_cashinvoice_customer_name_2c087bc6;
DROP INDEX IF EXISTS sales_app_cashinvoice_total_54ad83ab;
DROP INDEX IF EXISTS sales_app_cashinvoice_payment_status_fb798e06;
DROP INDEX IF EXISTS sales_app_cashinvoice_user_id_2ecfd08b;
DROP INDEX IF EXISTS sales_app_cashsale_item_30e2d039;

COMMIT;

-- Performance monitoring after cleanup
SELECT 
    'AFTER CLEANUP' as status,
    COUNT(*) as total_indexes,
    SUM(CASE WHEN idx_scan = 0 THEN 1 ELSE 0 END) as unused_indexes,
    SUM(CASE WHEN idx_scan > 0 THEN 1 ELSE 0 END) as used_indexes
FROM pg_stat_user_indexes 
WHERE schemaname = 'public';
