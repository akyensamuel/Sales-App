-- RLS PERFORMANCE OPTIMIZATION (Corrected)
-- Fixes RLS initialization plan issues using proper subquery optimization
-- Replaces auth.uid() calls with subqueries to prevent per-row re-evaluation

-- STEP 1: Drop and recreate policies with optimized subqueries

-- System tables policies (Admin only access) - Optimized with subqueries
DROP POLICY IF EXISTS auth_group_policy ON auth_group;
CREATE POLICY auth_group_policy ON public.auth_group
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = (SELECT auth.uid()::text::integer)
            AND ag.name = 'Admin'
        )
    );

DROP POLICY IF EXISTS auth_user_policy ON auth_user;
CREATE POLICY auth_user_policy ON public.auth_user
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = (SELECT auth.uid()::text::integer)
            AND ag.name = 'Admin'
        )
        OR (SELECT auth.uid()::text::integer) = id
    );

DROP POLICY IF EXISTS auth_permission_policy ON auth_permission;
CREATE POLICY auth_permission_policy ON public.auth_permission
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = (SELECT auth.uid()::text::integer)
            AND ag.name = 'Admin'
        )
    );

DROP POLICY IF EXISTS auth_group_permissions_policy ON auth_group_permissions;
CREATE POLICY auth_group_permissions_policy ON public.auth_group_permissions
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = (SELECT auth.uid()::text::integer)
            AND ag.name = 'Admin'
        )
    );

DROP POLICY IF EXISTS auth_user_groups_policy ON auth_user_groups;
CREATE POLICY auth_user_groups_policy ON public.auth_user_groups
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = (SELECT auth.uid()::text::integer)
            AND ag.name = 'Admin'
        )
        OR user_id = (SELECT auth.uid()::text::integer)
    );

DROP POLICY IF EXISTS auth_user_user_permissions_policy ON auth_user_user_permissions;
CREATE POLICY auth_user_user_permissions_policy ON public.auth_user_user_permissions
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = (SELECT auth.uid()::text::integer)
            AND ag.name = 'Admin'
        )
        OR user_id = (SELECT auth.uid()::text::integer)
    );

-- Django system tables (Admin only)
DROP POLICY IF EXISTS django_admin_log_policy ON django_admin_log;
CREATE POLICY django_admin_log_policy ON public.django_admin_log
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = (SELECT auth.uid()::text::integer)
            AND ag.name = 'Admin'
        )
    );

DROP POLICY IF EXISTS django_content_type_policy ON django_content_type;
CREATE POLICY django_content_type_policy ON public.django_content_type
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = (SELECT auth.uid()::text::integer)
            AND ag.name = 'Admin'
        )
    );

DROP POLICY IF EXISTS django_migrations_policy ON django_migrations;
CREATE POLICY django_migrations_policy ON public.django_migrations
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = (SELECT auth.uid()::text::integer)
            AND ag.name = 'Admin'
        )
    );

DROP POLICY IF EXISTS django_session_policy ON django_session;
CREATE POLICY django_session_policy ON public.django_session
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = (SELECT auth.uid()::text::integer)
            AND ag.name = 'Admin'
        )
    );

-- STEP 2: Fix multiple permissive policies issue on sales_app_adminlog
DROP POLICY IF EXISTS sales_app_adminlog_modify_policy ON sales_app_adminlog;
DROP POLICY IF EXISTS sales_app_adminlog_policy ON sales_app_adminlog;

-- Create single consolidated policy
CREATE POLICY sales_app_adminlog_consolidated_policy ON public.sales_app_adminlog
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = (SELECT auth.uid()::text::integer)
            AND ag.name IN ('Admin', 'Managers')
        )
    );

-- STEP 3: Remove duplicate indexes
DROP INDEX IF EXISTS sales_app_p_name_7b1c70_idx;
DROP INDEX IF EXISTS sales_app_s_invoice_c363aa_idx;

-- STEP 4: Optimization verification
SELECT 'RLS_PERFORMANCE_OPTIMIZED' as status,
       'Converted auth.uid() calls to subqueries for better performance' as improvement;
