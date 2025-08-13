-- Complete RLS Security Fix
-- This addresses all remaining security issues

-- ==========================================
-- STEP 1: Enable RLS on Missing Tables
-- ==========================================

-- Enable RLS on tables that still don't have it
ALTER TABLE public.accounting_app_financialforecast ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.auth_user ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.django_admin_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sales_app_adminlog ENABLE ROW LEVEL SECURITY;

-- ==========================================
-- STEP 2: Add Missing Policies for System Tables
-- ==========================================

-- Auth User Policy (Admin only, or users can see their own record)
CREATE POLICY auth_user_policy ON public.auth_user
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND ag.name = 'Admin'
        )
        OR auth.uid()::text::integer = id
    );

-- Django Admin Log Policy (Admin only)
CREATE POLICY django_admin_log_policy ON public.django_admin_log
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND ag.name = 'Admin'
        )
    );

-- Sales App Admin Log Policy (Managers and Admin)
CREATE POLICY sales_app_adminlog_policy ON public.sales_app_adminlog
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND (ag.name = 'Admin' OR ag.name = 'Managers')
        )
    );

-- Auth Groups Policy (Admin only)
CREATE POLICY auth_group_policy ON public.auth_group
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND ag.name = 'Admin'
        )
    );

-- Auth Permissions Policy (Admin only)
CREATE POLICY auth_permission_policy ON public.auth_permission
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND ag.name = 'Admin'
        )
    );

-- Auth Group Permissions Policy (Admin only)
CREATE POLICY auth_group_permissions_policy ON public.auth_group_permissions
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND ag.name = 'Admin'
        )
    );

-- Auth User Groups Policy (Admin only)
CREATE POLICY auth_user_groups_policy ON public.auth_user_groups
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND ag.name = 'Admin'
        )
    );

-- Auth User Permissions Policy (Admin only)
CREATE POLICY auth_user_user_permissions_policy ON public.auth_user_user_permissions
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND ag.name = 'Admin'
        )
    );

-- Django Content Types Policy (Read-only for authenticated)
CREATE POLICY django_content_type_policy ON public.django_content_type
    FOR SELECT
    TO authenticated
    USING (auth.uid() IS NOT NULL);

-- Django Migrations Policy (Admin only)
CREATE POLICY django_migrations_policy ON public.django_migrations
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND ag.name = 'Admin'
        )
    );

-- Django Sessions Policy (Users can access their own sessions)
CREATE POLICY django_session_policy ON public.django_session
    FOR ALL
    TO authenticated
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
-- STEP 3: Add Missing Policies for Business Tables
-- ==========================================

-- Financial Forecast Policy (Managers and Admin)
CREATE POLICY accounting_app_financialforecast_policy ON public.accounting_app_financialforecast
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND (ag.name = 'Admin' OR ag.name = 'Managers')
        )
    );

-- Tax Settings Policy (Admin only)
CREATE POLICY accounting_app_taxsettings_policy ON public.accounting_app_taxsettings
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND ag.name = 'Admin'
        )
    );

-- Accounting Audit Log Policy (Managers and Admin)
CREATE POLICY accounting_app_accountingauditlog_policy ON public.accounting_app_accountingauditlog
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND (ag.name = 'Admin' OR ag.name = 'Managers')
        )
    );

-- Expense Policy (Managers and Admin)
CREATE POLICY accounting_app_expense_policy ON public.accounting_app_expense
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND (ag.name = 'Admin' OR ag.name = 'Managers')
        )
    );

-- Product Performance Policy (Managers and Admin)
CREATE POLICY accounting_app_productperformance_policy ON public.accounting_app_productperformance
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND (ag.name = 'Admin' OR ag.name = 'Managers')
        )
    );

-- Salesperson Performance Policy (Managers and Admin)
CREATE POLICY accounting_app_salespersonperformance_policy ON public.accounting_app_salespersonperformance
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND (ag.name = 'Admin' OR ag.name = 'Managers')
        )
    );
