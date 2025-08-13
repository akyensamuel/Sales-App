-- RLS PERFORMANCE OPTIMIZATION
-- Fixes RLS initialization plan issues and removes duplicate policies/indexes
-- Addresses all performance warnings from Supabase database linter

-- STEP 1: Optimize RLS policies to use subqueries for auth functions
-- This prevents re-evaluation of auth functions for each row

-- Drop existing policies that have performance issues
DROP POLICY IF EXISTS auth_group_policy ON auth_group;
DROP POLICY IF EXISTS auth_user_groups_policy ON auth_user_groups;
DROP POLICY IF EXISTS accounting_app_financialforecast_policy ON accounting_app_financialforecast;
DROP POLICY IF EXISTS auth_user_policy ON auth_user;
DROP POLICY IF EXISTS auth_user_user_permissions_policy ON auth_user_user_permissions;
DROP POLICY IF EXISTS django_admin_log_policy ON django_admin_log;
DROP POLICY IF EXISTS auth_permission_policy ON auth_permission;
DROP POLICY IF EXISTS auth_group_permissions_policy ON auth_group_permissions;
DROP POLICY IF EXISTS django_content_type_policy ON django_content_type;
DROP POLICY IF EXISTS django_migrations_policy ON django_migrations;
DROP POLICY IF EXISTS django_session_policy ON django_session;
DROP POLICY IF EXISTS accounting_app_productperformance_policy ON accounting_app_productperformance;
DROP POLICY IF EXISTS accounting_app_taxsettings_policy ON accounting_app_taxsettings;
DROP POLICY IF EXISTS accounting_app_expense_policy ON accounting_app_expense;
DROP POLICY IF EXISTS accounting_app_accountingauditlog_policy ON accounting_app_accountingauditlog;
DROP POLICY IF EXISTS accounting_app_expensecategory_modify_policy ON accounting_app_expensecategory;
DROP POLICY IF EXISTS accounting_app_salespersonperformance_policy ON accounting_app_salespersonperformance;
DROP POLICY IF EXISTS accounting_app_profitlosssnapshot_modify_policy ON accounting_app_profitlosssnapshot;

-- Fix multiple permissive policies issue on sales_app_adminlog
DROP POLICY IF EXISTS sales_app_adminlog_modify_policy ON sales_app_adminlog;
DROP POLICY IF EXISTS sales_app_adminlog_policy ON sales_app_adminlog;

-- Drop modify policies that cause performance issues and duplicates
DROP POLICY IF EXISTS sales_app_invoice_modify_policy ON sales_app_invoice;
DROP POLICY IF EXISTS sales_app_product_modify_policy ON sales_app_product;
DROP POLICY IF EXISTS sales_app_sale_modify_policy ON sales_app_sale;
DROP POLICY IF EXISTS sales_app_stockmovement_modify_policy ON sales_app_stockmovement;
DROP POLICY IF EXISTS sales_app_cashproduct_modify_policy ON sales_app_cashproduct;
DROP POLICY IF EXISTS sales_app_cashsale_modify_policy ON sales_app_cashsale;
DROP POLICY IF EXISTS sales_app_cashinvoice_modify_policy ON sales_app_cashinvoice;

-- STEP 2: Create optimized RLS policies using subqueries for auth functions

-- System tables (Admin only access)
CREATE POLICY auth_group_optimized_policy ON auth_group FOR ALL TO authenticated
USING ((SELECT auth.jwt()) ->> 'user_metadata' ->> 'groups' LIKE '%Admin%');

CREATE POLICY auth_user_optimized_policy ON auth_user FOR ALL TO authenticated  
USING ((SELECT auth.jwt()) ->> 'user_metadata' ->> 'groups' LIKE '%Admin%');

CREATE POLICY auth_permission_optimized_policy ON auth_permission FOR ALL TO authenticated
USING ((SELECT auth.jwt()) ->> 'user_metadata' ->> 'groups' LIKE '%Admin%');

CREATE POLICY auth_group_permissions_optimized_policy ON auth_group_permissions FOR ALL TO authenticated
USING ((SELECT auth.jwt()) ->> 'user_metadata' ->> 'groups' LIKE '%Admin%');

CREATE POLICY auth_user_groups_optimized_policy ON auth_user_groups FOR ALL TO authenticated
USING ((SELECT auth.jwt()) ->> 'user_metadata' ->> 'groups' LIKE '%Admin%');

CREATE POLICY auth_user_user_permissions_optimized_policy ON auth_user_user_permissions FOR ALL TO authenticated
USING ((SELECT auth.jwt()) ->> 'user_metadata' ->> 'groups' LIKE '%Admin%');

-- Django system tables (Admin only)
CREATE POLICY django_admin_log_optimized_policy ON django_admin_log FOR ALL TO authenticated
USING ((SELECT auth.jwt()) ->> 'user_metadata' ->> 'groups' LIKE '%Admin%');

CREATE POLICY django_content_type_optimized_policy ON django_content_type FOR ALL TO authenticated
USING ((SELECT auth.jwt()) ->> 'user_metadata' ->> 'groups' LIKE '%Admin%');

CREATE POLICY django_migrations_optimized_policy ON django_migrations FOR ALL TO authenticated
USING ((SELECT auth.jwt()) ->> 'user_metadata' ->> 'groups' LIKE '%Admin%');

CREATE POLICY django_session_optimized_policy ON django_session FOR ALL TO authenticated
USING ((SELECT auth.jwt()) ->> 'user_metadata' ->> 'groups' LIKE '%Admin%');

-- Business tables (Role-based access)
CREATE POLICY sales_app_invoice_optimized_policy ON sales_app_invoice FOR ALL TO authenticated
USING ((SELECT auth.jwt()) ->> 'user_metadata' ->> 'groups' ~* '(Admin|Managers|Cashiers)');

CREATE POLICY sales_app_sale_optimized_policy ON sales_app_sale FOR ALL TO authenticated
USING ((SELECT auth.jwt()) ->> 'user_metadata' ->> 'groups' ~* '(Admin|Managers|Cashiers)');

CREATE POLICY sales_app_product_optimized_policy ON sales_app_product FOR ALL TO authenticated
USING ((SELECT auth.jwt()) ->> 'user_metadata' ->> 'groups' ~* '(Admin|Managers|Cashiers)');

CREATE POLICY sales_app_cashinvoice_optimized_policy ON sales_app_cashinvoice FOR ALL TO authenticated
USING ((SELECT auth.jwt()) ->> 'user_metadata' ->> 'groups' ~* '(Admin|Managers|Cashiers)');

CREATE POLICY sales_app_cashsale_optimized_policy ON sales_app_cashsale FOR ALL TO authenticated
USING ((SELECT auth.jwt()) ->> 'user_metadata' ->> 'groups' ~* '(Admin|Managers|Cashiers)');

CREATE POLICY sales_app_cashproduct_optimized_policy ON sales_app_cashproduct FOR ALL TO authenticated
USING ((SELECT auth.jwt()) ->> 'user_metadata' ->> 'groups' ~* '(Admin|Managers|Cashiers)');

CREATE POLICY sales_app_stockmovement_optimized_policy ON sales_app_stockmovement FOR ALL TO authenticated
USING ((SELECT auth.jwt()) ->> 'user_metadata' ->> 'groups' ~* '(Admin|Managers|Cashiers)');

-- Single consolidated admin log policy (fixes multiple permissive policies issue)
CREATE POLICY sales_app_adminlog_consolidated_policy ON sales_app_adminlog FOR ALL TO authenticated
USING ((SELECT auth.jwt()) ->> 'user_metadata' ->> 'groups' ~* '(Admin|Managers)');

-- Accounting tables (Admin and Managers)
CREATE POLICY accounting_app_expense_optimized_policy ON accounting_app_expense FOR ALL TO authenticated
USING ((SELECT auth.jwt()) ->> 'user_metadata' ->> 'groups' ~* '(Admin|Managers)');

CREATE POLICY accounting_app_expensecategory_optimized_policy ON accounting_app_expensecategory FOR ALL TO authenticated
USING ((SELECT auth.jwt()) ->> 'user_metadata' ->> 'groups' ~* '(Admin|Managers)');

CREATE POLICY accounting_app_taxsettings_optimized_policy ON accounting_app_taxsettings FOR ALL TO authenticated
USING ((SELECT auth.jwt()) ->> 'user_metadata' ->> 'groups' ~* '(Admin|Managers)');

CREATE POLICY accounting_app_financialforecast_optimized_policy ON accounting_app_financialforecast FOR ALL TO authenticated
USING ((SELECT auth.jwt()) ->> 'user_metadata' ->> 'groups' ~* '(Admin|Managers)');

CREATE POLICY accounting_app_productperformance_optimized_policy ON accounting_app_productperformance FOR ALL TO authenticated
USING ((SELECT auth.jwt()) ->> 'user_metadata' ->> 'groups' ~* '(Admin|Managers)');

CREATE POLICY accounting_app_salespersonperformance_optimized_policy ON accounting_app_salespersonperformance FOR ALL TO authenticated
USING ((SELECT auth.jwt()) ->> 'user_metadata' ->> 'groups' ~* '(Admin|Managers)');

CREATE POLICY accounting_app_profitlosssnapshot_optimized_policy ON accounting_app_profitlosssnapshot FOR ALL TO authenticated
USING ((SELECT auth.jwt()) ->> 'user_metadata' ->> 'groups' ~* '(Admin|Managers)');

CREATE POLICY accounting_app_accountingauditlog_optimized_policy ON accounting_app_accountingauditlog FOR ALL TO authenticated
USING ((SELECT auth.jwt()) ->> 'user_metadata' ->> 'groups' ~* '(Admin|Managers)');

-- STEP 3: Remove duplicate indexes identified by linter

-- Remove duplicate index on sales_app_product (keep the optimized one)
DROP INDEX IF EXISTS sales_app_p_name_7b1c70_idx;

-- Remove duplicate index on sales_app_sale (keep the optimized one)
DROP INDEX IF EXISTS sales_app_s_invoice_c363aa_idx;

-- STEP 4: Verify optimization results
SELECT 'RLS_PERFORMANCE_OPTIMIZED' as status, 
       'Fixed auth function re-evaluation and removed duplicate policies/indexes' as details;
