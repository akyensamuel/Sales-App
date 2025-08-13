-- FIX RLS POLICIES WITH CORRECT COLUMN NAMES
-- Corrects the policies that failed due to incorrect column references

-- Fix sales_app_sale policy (no user_id field - access through invoice.user)
DROP POLICY IF EXISTS sales_app_sale_modify_policy ON sales_app_sale;
CREATE POLICY sales_app_sale_modify_policy ON public.sales_app_sale
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = (SELECT auth.uid()::text::integer)
            AND ag.name IN ('Admin', 'Managers')
        )
        OR EXISTS (
            SELECT 1 FROM public.sales_app_invoice si
            WHERE si.id = sales_app_sale.invoice_id 
            AND si.user_id = (SELECT auth.uid()::text::integer)
        )
    );

-- Fix sales_app_stockmovement policy (uses created_by, not user_id)
DROP POLICY IF EXISTS sales_app_stockmovement_modify_policy ON sales_app_stockmovement;
CREATE POLICY sales_app_stockmovement_modify_policy ON public.sales_app_stockmovement
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = (SELECT auth.uid()::text::integer)
            AND ag.name IN ('Admin', 'Managers')
        )
        OR created_by_id = (SELECT auth.uid()::text::integer)
    );

-- Fix sales_app_cashsale policy (no user_id field - access through invoice.user)
DROP POLICY IF EXISTS sales_app_cashsale_modify_policy ON sales_app_cashsale;
CREATE POLICY sales_app_cashsale_modify_policy ON public.sales_app_cashsale
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = (SELECT auth.uid()::text::integer)
            AND ag.name IN ('Admin', 'Managers', 'Cashiers')
        )
        OR EXISTS (
            SELECT 1 FROM public.sales_app_cashinvoice sci
            WHERE sci.id = sales_app_cashsale.invoice_id 
            AND sci.user_id = (SELECT auth.uid()::text::integer)
        )
    );

-- Verification query
SELECT 
    'RLS_COLUMN_FIXES_APPLIED' as status,
    'Fixed policies with correct column references' as improvement;
