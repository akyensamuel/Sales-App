-- Fix RLS policies with correct syntax
-- This addresses the SQL syntax errors from the previous run

-- Sales modify policy (fixed syntax)
DROP POLICY IF EXISTS sales_app_sale_modify_policy ON public.sales_app_sale;
CREATE POLICY sales_app_sale_modify_policy ON public.sales_app_sale
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND (ag.name = 'Admin' OR ag.name = 'Managers' OR ag.name = 'Cashiers')
        )
    );

-- Products modify policy (fixed syntax)  
DROP POLICY IF EXISTS sales_app_product_modify_policy ON public.sales_app_product;
CREATE POLICY sales_app_product_modify_policy ON public.sales_app_product
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

-- Invoices modify policy (fixed syntax)
DROP POLICY IF EXISTS sales_app_invoice_modify_policy ON public.sales_app_invoice;
CREATE POLICY sales_app_invoice_modify_policy ON public.sales_app_invoice
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND (ag.name = 'Admin' OR ag.name = 'Managers' OR ag.name = 'Cashiers')
        )
    );

-- Stock Movement modify policy (fixed syntax)
DROP POLICY IF EXISTS sales_app_stockmovement_modify_policy ON public.sales_app_stockmovement;
CREATE POLICY sales_app_stockmovement_modify_policy ON public.sales_app_stockmovement
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

-- Cash Products modify policy (fixed syntax)
DROP POLICY IF EXISTS sales_app_cashproduct_modify_policy ON public.sales_app_cashproduct;
CREATE POLICY sales_app_cashproduct_modify_policy ON public.sales_app_cashproduct
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

-- Cash Sales modify policy (fixed syntax)
DROP POLICY IF EXISTS sales_app_cashsale_modify_policy ON public.sales_app_cashsale;
CREATE POLICY sales_app_cashsale_modify_policy ON public.sales_app_cashsale
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND (ag.name = 'Admin' OR ag.name = 'Managers' OR ag.name = 'Cashiers')
        )
    );

-- Cash Invoices modify policy (fixed syntax)
DROP POLICY IF EXISTS sales_app_cashinvoice_modify_policy ON public.sales_app_cashinvoice;
CREATE POLICY sales_app_cashinvoice_modify_policy ON public.sales_app_cashinvoice
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.auth_user_groups aug
            JOIN public.auth_group ag ON aug.group_id = ag.id
            WHERE aug.user_id = auth.uid()::text::integer
            AND (ag.name = 'Admin' OR ag.name = 'Managers' OR ag.name = 'Cashiers')
        )
    );

-- Accounting: Profit Loss Snapshot modify policy (fixed syntax)
DROP POLICY IF EXISTS accounting_app_profitlosssnapshot_modify_policy ON public.accounting_app_profitlosssnapshot;
CREATE POLICY accounting_app_profitlosssnapshot_modify_policy ON public.accounting_app_profitlosssnapshot
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

-- Expense Categories modify policy (fixed syntax)
DROP POLICY IF EXISTS accounting_app_expensecategory_modify_policy ON public.accounting_app_expensecategory;
CREATE POLICY accounting_app_expensecategory_modify_policy ON public.accounting_app_expensecategory
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
