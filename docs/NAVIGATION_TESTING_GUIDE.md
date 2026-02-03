"""
Test file to verify smart navigation logic
This is a JavaScript logic test that can be copied to browser console for testing
"""

# JAVASCRIPT TEST CODE (copy and paste into browser console F12)
"""
// Test 1: Initialize navigation with sample user groups
userGroups = ['Managers'];
isAuthenticated = true;

// Test 2: Check route access
console.log('Admin can access manager_dashboard?', canAccessRoute('manager_dashboard')); // true
console.log('Manager can access accounting_dashboard?', canAccessRoute('accounting_dashboard')); // false

// Test 3: Simulate navigation history
sessionStorage.setItem('mainRouteStack', JSON.stringify(['sales_entry', 'manager_dashboard']));

// Test 4: Go back from detail page
window.location.pathname = '/sales/receipt_print/123/';
console.log('Current route (from detail page):', getCurrentMainRoute()); // should be null (detail page)

// Test 5: Initialize stack
initializeNavigationStack();
console.log('Stack after init:', JSON.parse(sessionStorage.getItem('mainRouteStack')));

// Test 6: Test route matching with different URLs
const testUrls = [
    '/sales/sales_entry/',
    '/sales/sales_entry/edit/',
    '/sales/receipt_print/123/',
    '/sales/manager_dashboard/',
    '/sales/cash/sales_entry/',
    '/accounting/',
];

testUrls.forEach(url => {
    window.location.pathname = url;
    console.log(`URL: ${url} -> Route: ${getCurrentMainRoute()}`);
});
"""

# PYTHON TEST CODE (can be run with manage.py shell)
"""
from django.contrib.auth.models import User, Group
from django.contrib.auth import get_user_model

# Create test groups if they don't exist
admin_group, _ = Group.objects.get_or_create(name='Admin')
managers_group, _ = Group.objects.get_or_create(name='Managers')
cashiers_group, _ = Group.objects.get_or_create(name='Cashiers')

# Create test user
User = get_user_model()
test_user, created = User.objects.get_or_create(username='testuser')

# Add to Managers group
test_user.groups.add(managers_group)

# Verify
print(f"User: {test_user.username}")
print(f"Groups: {list(test_user.groups.values_list('name', flat=True))}")

# This should output:
# User: testuser
# Groups: ['Managers']
"""
