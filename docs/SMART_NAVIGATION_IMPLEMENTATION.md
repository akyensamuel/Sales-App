# Smart Navigation Implementation Guide

## Overview

The navigation system has been completely redesigned to provide intelligent forward/back navigation that:
- Tracks only **main routes** (not detail or print pages)
- Respects **user group permissions** (Admin, Managers, Cashiers)
- Provides sensible **fallback routes** when back button is used
- Maintains **navigation history** per session

## How It Works

### Main Routes Tracked

The system tracks these primary routes only:

| Route Name | Path | Access Level |
|------------|------|--------------|
| `sales_entry` | `/sales/sales_entry/` | All authenticated users |
| `cash_sales_entry` | `/sales/cash/sales_entry/` | All authenticated users |
| `cash_products` | `/sales/cash/products/` | All authenticated users |
| `products` | `/sales/products/` | All authenticated users |
| `manager_dashboard` | `/sales/manager_dashboard/` | Admin, Managers |
| `accounting_dashboard` | `/accounting/` | Admin only |
| `home` | `/sales/` | All authenticated users |

### Routes NOT Tracked (Detail/Print Pages)

These are skipped and not included in navigation history:
- Invoice detail pages (`/sales/invoice/<id>/`)
- Print pages (`/sales/receipt_print/<id>/`)
- Edit pages (`/sales/edit_invoice/<id>/`)
- Product detail pages
- Any URL with `/<id>/` pattern (detail routes)

## Navigation Flow

### Back Button Behavior

**Scenario**: User makes a sale on `/sales/sales_entry/` and clicks save/print. Receipt prints from `/sales/receipt_print/123/`, then user clicks back arrow.

**What happens:**
1. Current URL: `/sales/receipt_print/123/` (detail page - not tracked)
2. Navigation stack: `[sales_entry, ...]`
3. Back button triggered → pops current route
4. Returns to: `/sales/sales_entry/` (main route)

**Without detail page navigation**:
If user navigates: Sales Entry → Manager Dashboard → Cash Sales Entry

**What happens**:
1. Current URL: `/sales/cash/sales_entry/` (main route)
2. Navigation stack: `[sales_entry, manager_dashboard, cash_sales_entry]`
3. Back button triggered → pops `cash_sales_entry`
4. Returns to: `/sales/manager_dashboard/` (previous main route)

### Forward Button Behavior

The forward button uses browser history via `window.history.forward()`, which:
- Works only within your browser session
- Maintains browser back/forward button functionality
- Is compatible with back button smart navigation

## User Group Access Control

Each route has group requirements:

```javascript
// Example route configuration
const MAIN_ROUTES = {
    'manager_dashboard': { 
        path: '/sales/manager_dashboard/', 
        group_required: ['Admin', 'Managers']  // Only these groups can access
    },
    'accounting_dashboard': { 
        path: '/accounting/', 
        group_required: ['Admin']  // Admin only
    }
};
```

### Fallback Behavior

If user tries to go back to a route they don't have access to:

1. Admin/Managers → `/sales/manager_dashboard/`
2. Cashiers → `/sales/sales_entry/`
3. Unauthenticated → `/` (home page)

## Technical Implementation

### Files Modified

1. **`core/templates/core/navigation_handler.html`** (NEW)
   - JavaScript functions for route tracking
   - `handleBackNavigation()` - Smart back button
   - `handleForwardNavigation()` - Browser forward
   - `initializeNavigationStack()` - Initialize history
   - `getCurrentMainRoute()` - Detect current route
   - `canAccessRoute()` - Check permissions

2. **`core/templates/core/navbar.html`** (UPDATED)
   - Back button calls `handleBackNavigation()` instead of `window.history.back()`
   - Forward button calls `handleForwardNavigation()`
   - Navbar element now has `data-user-groups` and `data-is-authenticated` attributes
   - Passes user group data to navigation handler

3. **`core/context_processors.py`** (NEW)
   - Provides `user_groups` and `user_groups_json` to all templates
   - Converts user groups to JSON for JavaScript access

4. **`sales_management_project/settings.py`** (UPDATED)
   - Added `core.context_processors.user_groups_context` to context processors

5. **`core/templates/core/base.html`** (UPDATED)
   - Includes navigation handler script
   - Loads group_filters template tag
   - Passes user_groups_json to navbar via context

### JavaScript Functions

#### `initializeNavigation()`
- Reads user groups and authentication status from navbar element
- Initializes navigation stack from sessionStorage

#### `initializeNavigationStack()`
- Retrieves current navigation stack
- Adds current route if it's a main route
- Prevents duplicates
- Limits history to last 10 routes (prevents memory issues)

#### `handleBackNavigation()`
- Gets current navigation stack
- Pops current route
- Finds previous accessible route
- Navigates to it, or falls back to default dashboard

#### `handleForwardNavigation()`
- Uses browser's native `window.history.forward()`
- Compatible with smart back navigation

#### `canAccessRoute(routeName)`
- Checks authentication status
- Verifies user group permissions
- Returns true if user can access route

#### `navigateToDefaultDashboard()`
- Routes users to appropriate dashboard:
  - Admin/Managers → Manager Dashboard
  - Cashiers → Sales Entry
  - Unauthenticated → Home

## Usage Examples

### Example 1: Sales Entry → Save → Back

```
1. User navigates to: /sales/sales_entry/ 
   → Stack: [sales_entry]
   
2. User clicks "Save and Print"
   → Page redirects to: /sales/receipt_print/123/ 
   → Stack: [sales_entry] (detail page not added)
   
3. User clicks Back arrow
   → Navigation calls handleBackNavigation()
   → Stack pops, finds sales_entry in history
   → User returns to: /sales/sales_entry/
```

### Example 2: Multi-Route Navigation → Back

```
1. Cashier navigates: 
   → Sales Entry (/sales/sales_entry/)
   → Stack: [sales_entry]
   
2. Then views Manager Dashboard (has access):
   → Manager Dashboard (/sales/manager_dashboard/)
   → Stack: [sales_entry, manager_dashboard]
   
3. Then goes to Cash Sales:
   → Cash Sales Entry (/sales/cash/sales_entry/)
   → Stack: [sales_entry, manager_dashboard, cash_sales_entry]
   
4. Clicks Back arrow:
   → Stack pops cash_sales_entry
   → User returns to: /sales/manager_dashboard/
   
5. Clicks Back arrow again:
   → Stack pops manager_dashboard
   → User returns to: /sales/sales_entry/
```

### Example 3: Access Control

```
1. Cashier at: /sales/cash/sales_entry/
   → Stack: [cash_sales_entry]
   
2. Types URL directly: /accounting/ (Admin-only)
   → canAccessRoute() returns false
   → Navigation system ignores this route
   → Click Back → Still on /sales/cash/sales_entry/
```

## Session Storage

Navigation history is stored in `sessionStorage`:

```javascript
// Automatically managed by the system
sessionStorage.getItem('mainRouteStack')  // Current stack
// Example: ["sales_entry", "manager_dashboard", "cash_sales_entry"]
```

- Stored as JSON array of route names
- Cleared when browser tab/window closes
- Separate for each tab/window
- Limited to last 10 routes

## Configuration

### Adding New Routes

To add a new main route, edit `navigation_handler.html`:

```javascript
const MAIN_ROUTES = {
    'new_route': { 
        path: '/path/to/route/', 
        group_required: ['GroupName'] // or null for all
    },
};
```

### Modifying Access Levels

Change `group_required` in MAIN_ROUTES:

```javascript
// Before: Admin only
'accounting_dashboard': { path: '/accounting/', group_required: ['Admin'] }

// After: Admin and Managers
'accounting_dashboard': { path: '/accounting/', group_required: ['Admin', 'Managers'] }
```

## Browser Compatibility

- ✅ Chrome/Chromium 51+
- ✅ Firefox 55+
- ✅ Safari 11+
- ✅ Edge 15+
- ✅ Mobile browsers (iOS Safari, Chrome Mobile)

**Dependencies:**
- Requires `sessionStorage` support
- Requires JSON support
- No external libraries needed

## Troubleshooting

### Back button not working?

1. Check console (F12) for JavaScript errors
2. Verify user groups are loaded: Open browser DevTools → Storage → Session Storage → Look for `mainRouteStack`
3. Check that user is authenticated
4. Verify route names match `MAIN_ROUTES` configuration

### User can access restricted route?

1. Verify user group assignments in Django Admin
2. Check `data-user-groups` attribute in navbar (DevTools)
3. Confirm group names match exactly (case-sensitive): "Admin", "Managers", "Cashiers"

### Navigation stack keeps growing?

The system automatically limits to 10 routes. If you see more:
1. Clear sessionStorage: `sessionStorage.clear()` in console
2. Refresh page

### Navigation jumps to unexpected page?

1. Check that the previous route is accessible to user
2. Verify user group permissions
3. Look for permission changes mid-session (unlikely but possible)

## Session Persistence Note

Navigation history is **PER SESSION**:
- Cleared when user logs out
- Cleared when browser tab closes
- Cleared when user closes browser (not persistent storage)
- Separate for each tab/window

This is intentional for security and simplicity.

## Future Enhancements

Possible improvements:
- Persistent navigation history (localStorage) for multi-session tracking
- Visual breadcrumb of navigation path
- Keyboard shortcuts (Alt+Left/Right for back/forward)
- Navigation state recovery after page refresh
- Analytics on navigation patterns

---

## Quick Start Checklist

- ✅ Navigation handler JavaScript created
- ✅ Navbar buttons updated to use smart navigation
- ✅ Context processor created for user groups
- ✅ Settings configured with context processor
- ✅ Base template includes navigation handler
- ✅ User groups available in JavaScript

**Ready to test!** Try the back button after making a sale and saving.
