-- Enable RLS (Row Level Security) for all public tables
-- This addresses the security vulnerability where RLS is disabled
-- Updated for user groups: Admin, Managers, Cashiers

-- ==========================================
-- Django System Tables (Limited Access)
-- ==========================================

-- Django Auth Tables
ALTER TABLE public.auth_user ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.auth_group ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.auth_permission ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.auth_group_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.auth_user_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.auth_user_user_permissions ENABLE ROW LEVEL SECURITY;

-- Django System Tables
ALTER TABLE public.django_admin_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.django_content_type ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.django_migrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.django_session ENABLE ROW LEVEL SECURITY;

-- ==========================================
-- Sales App Tables (Business Logic Access)
-- ==========================================

ALTER TABLE public.sales_app_adminlog ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sales_app_sale ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sales_app_product ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sales_app_invoice ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sales_app_stockmovement ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sales_app_cashproduct ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sales_app_cashsale ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sales_app_cashinvoice ENABLE ROW LEVEL SECURITY;

-- ==========================================
-- Accounting App Tables (Business Logic Access)
-- ==========================================

ALTER TABLE public.accounting_app_financialforecast ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.accounting_app_taxsettings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.accounting_app_profitlosssnapshot ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.accounting_app_accountingauditlog ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.accounting_app_expense ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.accounting_app_expensecategory ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.accounting_app_productperformance ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.accounting_app_salespersonperformance ENABLE ROW LEVEL SECURITY;

-- ==========================================
-- RLS POLICIES - Django System Tables
-- ==========================================

-- Auth User: Only admins can access user data
CREATE POLICY auth_user_policy ON public.auth_user
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND ag.name = 'Admin'
        )
        OR auth.uid()::text::integer = id
    );

-- Auth Groups: Only admins can manage groups
CREATE POLICY auth_group_policy ON public.auth_group
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND ag.name = 'Admin'
        )
    );

-- Permissions: Only admins can access
CREATE POLICY auth_permission_policy ON public.auth_permission
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND ag.name = 'Admin'
        )
    );

-- Group Permissions: Only admins can manage
CREATE POLICY auth_group_permissions_policy ON public.auth_group_permissions
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND ag.name = 'Admin'
        )
    );

-- User Groups: Only admins can manage
CREATE POLICY auth_user_groups_policy ON public.auth_user_groups
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND ag.name = 'Admin'
        )
    );

-- User Permissions: Only admins can manage
CREATE POLICY auth_user_user_permissions_policy ON public.auth_user_user_permissions
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND ag.name = 'Admin'
        )
    );

-- Django Admin Log: Only admins can access
CREATE POLICY django_admin_log_policy ON public.django_admin_log
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND ag.name = 'Admin'
        )
    );

-- Content Types: Read-only for authenticated users
CREATE POLICY django_content_type_policy ON public.django_content_type
    FOR SELECT
    USING (auth.uid() IS NOT NULL);

-- Migrations: Admin only
CREATE POLICY django_migrations_policy ON public.django_migrations
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND ag.name = 'Admin'
        )
    );

-- Sessions: Users can only access their own sessions
CREATE POLICY django_session_policy ON public.django_session
    FOR ALL
    USING (
        session_data LIKE '%"_auth_user_id":' || auth.uid()::text || '%'
        OR EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND ag.name = 'Admin'
        )
    );

-- ==========================================
-- RLS POLICIES - Sales App Tables
-- ==========================================

-- Admin Log: All authenticated users can read, admin can modify
CREATE POLICY sales_app_adminlog_policy ON public.sales_app_adminlog
    FOR SELECT
    USING (auth.uid() IS NOT NULL);

CREATE POLICY sales_app_adminlog_modify_policy ON public.sales_app_adminlog
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND (ag.name = 'Admin' OR ag.name = 'Managers')
        )
    );

-- Sales: Users can see all sales (business requirement), managers can modify
CREATE POLICY sales_app_sale_select_policy ON public.sales_app_sale
    FOR SELECT
    USING (auth.uid() IS NOT NULL);

CREATE POLICY sales_app_sale_modify_policy ON public.sales_app_sale
    FOR INSERT, UPDATE, DELETE
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND (ag.name = 'Admin' OR ag.name = 'Managers' OR ag.name = 'Cashiers')
        )
    );

-- Products: All authenticated users can read, admin/manager can modify
CREATE POLICY sales_app_product_select_policy ON public.sales_app_product
    FOR SELECT
    USING (auth.uid() IS NOT NULL);

CREATE POLICY sales_app_product_modify_policy ON public.sales_app_product
    FOR INSERT, UPDATE, DELETE
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND (ag.name = 'Admin' OR ag.name = 'Managers')
        )
    );

-- Invoices: Users can see all invoices, cashiers/manager/admin can create/modify
CREATE POLICY sales_app_invoice_select_policy ON public.sales_app_invoice
    FOR SELECT
    USING (auth.uid() IS NOT NULL);

CREATE POLICY sales_app_invoice_modify_policy ON public.sales_app_invoice
    FOR INSERT, UPDATE, DELETE
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND (ag.name = 'Admin' OR ag.name = 'Managers' OR ag.name = 'Cashiers')
        )
    );

-- Stock Movement: Read-only for most users, admin/manager can modify
CREATE POLICY sales_app_stockmovement_select_policy ON public.sales_app_stockmovement
    FOR SELECT
    USING (auth.uid() IS NOT NULL);

CREATE POLICY sales_app_stockmovement_modify_policy ON public.sales_app_stockmovement
    FOR INSERT, UPDATE, DELETE
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND (ag.name = 'Admin' OR ag.name = 'Managers')
        )
    );

-- Cash Products: All authenticated users can read, admin/manager can modify
CREATE POLICY sales_app_cashproduct_select_policy ON public.sales_app_cashproduct
    FOR SELECT
    USING (auth.uid() IS NOT NULL);

CREATE POLICY sales_app_cashproduct_modify_policy ON public.sales_app_cashproduct
    FOR INSERT, UPDATE, DELETE
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND (ag.name = 'Admin' OR ag.name = 'Managers')
        )
    );

-- Cash Sales: Users can see all, cashiers/manager/admin can create/modify
CREATE POLICY sales_app_cashsale_select_policy ON public.sales_app_cashsale
    FOR SELECT
    USING (auth.uid() IS NOT NULL);

CREATE POLICY sales_app_cashsale_modify_policy ON public.sales_app_cashsale
    FOR INSERT, UPDATE, DELETE
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND (ag.name = 'Admin' OR ag.name = 'Managers' OR ag.name = 'Cashiers')
        )
    );

-- Cash Invoices: Users can see all, cashiers/manager/admin can create/modify
CREATE POLICY sales_app_cashinvoice_select_policy ON public.sales_app_cashinvoice
    FOR SELECT
    USING (auth.uid() IS NOT NULL);

CREATE POLICY sales_app_cashinvoice_modify_policy ON public.sales_app_cashinvoice
    FOR INSERT, UPDATE, DELETE
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND (ag.name = 'Admin' OR ag.name = 'Managers' OR ag.name = 'Cashiers')
        )
    );

-- ==========================================
-- RLS POLICIES - Accounting App Tables
-- ==========================================

-- Financial Forecast: Manager and Admin access only
CREATE POLICY accounting_app_financialforecast_policy ON public.accounting_app_financialforecast
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND (ag.name = 'Admin' OR ag.name = 'Managers')
        )
    );

-- Tax Settings: Admin only
CREATE POLICY accounting_app_taxsettings_policy ON public.accounting_app_taxsettings
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND ag.name = 'Admin'
        )
    );

-- Profit Loss Snapshot: Manager and Admin can read, Admin can modify
CREATE POLICY accounting_app_profitlosssnapshot_select_policy ON public.accounting_app_profitlosssnapshot
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND (ag.name = 'Admin' OR ag.name = 'Managers')
        )
    );

CREATE POLICY accounting_app_profitlosssnapshot_modify_policy ON public.accounting_app_profitlosssnapshot
    FOR INSERT, UPDATE, DELETE
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND ag.name = 'Admin'
        )
    );

-- Accounting Audit Log: Manager and Admin can read
CREATE POLICY accounting_app_accountingauditlog_policy ON public.accounting_app_accountingauditlog
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND (ag.name = 'Admin' OR ag.name = 'Managers')
        )
    );

-- Expenses: Manager and Admin can access
CREATE POLICY accounting_app_expense_policy ON public.accounting_app_expense
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND (ag.name = 'Admin' OR ag.name = 'Managers')
        )
    );

-- Expense Categories: All authenticated users can read, Admin can modify
CREATE POLICY accounting_app_expensecategory_select_policy ON public.accounting_app_expensecategory
    FOR SELECT
    USING (auth.uid() IS NOT NULL);

CREATE POLICY accounting_app_expensecategory_modify_policy ON public.accounting_app_expensecategory
    FOR INSERT, UPDATE, DELETE
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND ag.name = 'Admin'
        )
    );

-- Product Performance: Manager and Admin can read
CREATE POLICY accounting_app_productperformance_policy ON public.accounting_app_productperformance
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND (ag.name = 'Admin' OR ag.name = 'Managers')
        )
    );

-- Salesperson Performance: Manager and Admin can read
CREATE POLICY accounting_app_salespersonperformance_policy ON public.accounting_app_salespersonperformance
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND (ag.name = 'Admin' OR ag.name = 'Managers')
        )
    );

-- ==========================================
-- IMPORTANT NOTES
-- ==========================================

-- 1. These policies assume you have user groups: 'Admin', 'Managers', 'Cashiers'
-- 2. The auth.uid() function returns the authenticated user's ID from Supabase Auth
-- 3. You may need to adjust these policies based on your specific business requirements
-- 4. Test these policies thoroughly in a development environment first
-- 5. Consider creating specific service roles for your Django application

-- To apply this file:
-- 1. Save this as a .sql file
-- 2. Run it in your Supabase SQL editor or
-- 3. Use the Django management command we'll create next
