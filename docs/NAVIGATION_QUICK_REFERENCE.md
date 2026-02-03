# Smart Navigation - Quick Reference

## ⚡ TL;DR - What Changed

**Before**: Back/Forward buttons used browser history
```javascript
<button onclick="window.history.back()">Back</button>
<button onclick="window.history.forward()">Forward</button>
```

**After**: Back button uses intelligent main route navigation
```javascript
<button onclick="handleBackNavigation()">Back</button>  // Smart!
<button onclick="handleForwardNavigation()">Forward</button>  // Still standard
```

## 🎯 What This Solves

### Problem 1: Going back after printing receipt
**Before**: Back button took you to the detail page with same order
**After**: Back button takes you to sales entry page (previous main route)

### Problem 2: Respecting user permissions
**Before**: Could navigate to restricted pages if in history
**After**: Only allows navigation to routes user has access to

### Problem 3: Complex history chains
**Before**: Long chain of detail pages in back button
**After**: Clean history of only main routes

## 📍 Main Routes Tracked

```
/sales/sales_entry/                    → 'sales_entry'
/sales/manager_dashboard/             → 'manager_dashboard'
/sales/cash/sales_entry/              → 'cash_sales_entry'
/sales/cash/products/                 → 'cash_products'
/sales/products/                      → 'products'
/accounting/                          → 'accounting_dashboard'
/sales/                               → 'home'
```

## ❌ Routes NOT Tracked (Skipped)

```
/sales/sales_entry/123/               → Detail page (SKIPPED)
/sales/receipt_print/123/             → Print page (SKIPPED)
/sales/edit_invoice/456/              → Edit page (SKIPPED)
/accounting/expenses/789/             → Detail page (SKIPPED)
(Any URL with /<id>/ pattern)
```

## 🔑 Key Configuration

Edit `core/templates/core/navigation_handler.html` to:

### Add new route:
```javascript
const MAIN_ROUTES = {
    'new_route': { 
        path: '/path/to/new_route/', 
        group_required: ['Admin', 'Managers']  // or null for all
    },
};
```

### Change access level:
```javascript
// Before: Managers only
'manager_dashboard': { path: '/sales/manager_dashboard/', group_required: ['Admin', 'Managers'] }

// After: Managers and Cashiers
'manager_dashboard': { path: '/sales/manager_dashboard/', group_required: ['Admin', 'Managers', 'Cashiers'] }
```

## 🧪 Quick Test

**In browser console (F12)**:

```javascript
// 1. Check current route
getCurrentMainRoute()  // Should return route name or null

// 2. Check user groups
JSON.parse(document.querySelector('[data-user-groups]').dataset.userGroups)  // ['Managers']

// 3. Check navigation history
JSON.parse(sessionStorage.getItem('mainRouteStack'))  // ['sales_entry', 'manager_dashboard']

// 4. Test access check
canAccessRoute('accounting_dashboard')  // true or false

// 5. Simulate back navigation
handleBackNavigation()  // Will navigate to previous route
```

## 📊 User Group Access

| Route | Admin | Managers | Cashiers |
|-------|:-----:|:--------:|:--------:|
| sales_entry | ✓ | ✓ | ✓ |
| cash_sales_entry | ✓ | ✓ | ✓ |
| products | ✓ | ✓ | ✓ |
| manager_dashboard | ✓ | ✓ | ✗ |
| accounting | ✓ | ✗ | ✗ |

## 🐛 If Something Goes Wrong

### Back button not responding?
```javascript
// Clear and reinitialize
sessionStorage.clear()
location.reload()
```

### User can access restricted route?
1. Go to Django Admin
2. Verify user groups: exactly "Admin", "Managers", or "Cashiers"
3. Clear cache: Ctrl+Shift+Delete (or Cmd+Shift+Delete on Mac)

### Navigation jumping to wrong page?
1. Check: `canAccessRoute(routeName)` function
2. Verify user groups are loaded correctly
3. Check for typos in group names

## 📁 Files You Need to Know

- `core/templates/core/navigation_handler.html` - Main JavaScript logic
- `core/templates/core/navbar.html` - Back/Forward buttons
- `core/context_processors.py` - User groups for templates
- `sales_management_project/settings.py` - Context processor registration

## 🔄 How It Works (Simple Version)

1. User navigates to page
2. System checks if it's a main route → Adds to history
3. User clicks back button
4. System checks history for previous accessible route
5. Navigates to that route (not detail page)
6. If no accessible route found → Goes to dashboard

## ⚙️ Configuration Options

Currently tracked routes + their access requirements:

```javascript
const MAIN_ROUTES = {
    'sales_entry': { path: '/sales/sales_entry/', group_required: null },
    'cash_sales_entry': { path: '/sales/cash/sales_entry/', group_required: null },
    'manager_dashboard': { path: '/sales/manager_dashboard/', group_required: ['Admin', 'Managers'] },
    'cash_products': { path: '/sales/cash/products/', group_required: null },
    'products': { path: '/sales/products/', group_required: null },
    'accounting_dashboard': { path: '/accounting/', group_required: ['Admin'] },
    'home': { path: '/sales/', group_required: null },
};
```

## 💡 Pro Tips

1. **Check history anytime**: `JSON.parse(sessionStorage.getItem('mainRouteStack'))`
2. **Debug navigation**: Open console and click back button, watch logs
3. **Test as different user**: Try with Admin, Managers, Cashiers accounts
4. **Mobile test**: Use browser DevTools device emulation

## ✨ Result

✅ Smart back button that understands your app
✅ User permissions respected in navigation
✅ Clean history of main routes only
✅ Sensible fallback destinations
✅ Works on all devices and browsers

---

**For detailed documentation**, see `docs/SMART_NAVIGATION_IMPLEMENTATION.md`
