-- DEBUG: Check current RLS policy definitions
-- This will show us exactly what's in the policies to understand why warnings persist

SELECT 
    schemaname,
    tablename, 
    policyname,
    qual as policy_definition
FROM pg_policies 
WHERE schemaname = 'public' 
    AND tablename IN ('auth_group', 'auth_user', 'sales_app_product', 'sales_app_sale')
ORDER BY tablename, policyname;

-- Check specific policy that should have been optimized
SELECT 
    'auth_group_policy' as policy_name,
    qual as current_definition
FROM pg_policies 
WHERE schemaname = 'public' 
    AND tablename = 'auth_group' 
    AND policyname = 'auth_group_policy';
