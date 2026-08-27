# Menu System Implementation Report

## Overview

The menu system is a **fully dynamic, database-driven sidebar navigation** with role-based access control (RBAC), product gating, multi-tenant organization scoping, and both system-level and custom menus. The backend (`crm_backend/menus/`) serves data via DRF endpoints; the frontend (`crm_frontend/`) consumes it via a React context provider and renders the sidebar 100% from API data (no hardcoded nav items).

---

## Current Access Model (as of latest changes)

The system is designed around **three active roles** — `Superadmin`, `Admin`, and `Staff` — with a clear two-path access model:

| Who | How they get menu access |
|-----|--------------------------|
| **Superadmin** | **Auto-granted** every active SYSTEM menu (hard-coded in the API — no `MenuRole` row required) |
| **Admin** | **Auto-granted** every active SYSTEM menu (same hard auto-grant) |
| **Staff** (and any other role) | **Explicit per-user assignment** by a Superadmin/Admin from **User Management** (via the "Assign Menu" modal → `MenuUser` rows) |

**Key behaviors:**

1. **Hard auto-grant for admins** — `_get_visible_menus()` always includes all active SYSTEM menus for `Superadmin`/`Admin`, regardless of `MenuRole` rows. This means any SYSTEM menu created later (e.g. from a separate platform-management app) is **immediately visible to admins** without any extra configuration *(product-gated menus excepted — see Security section #5)*.
2. **Staff access is opt-in** — staff see *nothing* by default. A Superadmin/Admin must explicitly assign menus to them from User Management.
3. **Role-based grants on SYSTEM menus are cleaned up** — the data migration `0006` removes any stale `MenuRole` rows for non-admin roles on SYSTEM menus, so staff can never inherit access through old bulk grants.
4. **`user-effective-menus` marks SYSTEM menus as `role_based` (🔒 locked)** for admin targets — the Assign-Menu modal shows them as auto-granted and unremovable.
5. **Platform Management moved to a separate app** — the old `/admin/menus*` frontend pages (`AdminMenus`, `AdminMenuRoles`, `AdminMenuForm`) have been **removed** from this repo. The backend menu API remains fully intact and is the contract the new app will consume.

---

## Backend Architecture (`crm_backend/menus/`)

### Models (`models.py` — 6 models, 231 lines)

| Model | Table | Purpose | Key Fields |
|-------|-------|---------|------------|
| `Organization` | `menus_organization` | Multi-tenant orgs | `name`, `owner` (FK User) |
| `Product` | `menus_product` | Purchasable modules | `name`, `code`, `is_active` |
| `OrgProductPurchase` | `menus_orgproductpurchase` | Product licensing per org | `organization`, `product`, `is_valid` (computed) |
| **`Menu`** | `menus_menu` | Core menu item | `type` (SYSTEM/CUSTOM), `code`, `name`, `href`, `icon`, `section`, `order`, `description`, `is_active`, `created_by`, `organization`, `required_product` |
| **`MenuRole`** | `menus_menurole` | Role-to-menu assignments | `menu`, `role`, `organization` |
| **`MenuUser`** | `menus_menuuser` | User-to-menu overrides | `menu`, `user` |

**Constraints:**
- `unique_together = (organization, code)` — menu code unique per org
- `UniqueConstraint(code)` where `organization__isnull=True` — SYSTEM menu codes globally unique
- `unique_together = (menu, role, organization)` — MenuRole per org context
- Indexes on `(organization, is_active)`, `(type, is_active)`, `(section, order)`
- UUID primary keys on all models

**Model permission methods:**
- `can_edit(user)` — SYSTEM: Superadmin only; CUSTOM: org Admin/Superadmin
- `can_assign_user(user)` — SYSTEM: Superadmin/Admin; CUSTOM: same as `can_edit`
- `can_delete(user)` — SYSTEM: Superadmin only; CUSTOM: creator or org Superadmin

### Serializers (`serializers.py` — 160 lines)

| Serializer | Purpose |
|------------|---------|
| `MenuListSerializer` | Minimal list output — includes `roles` as `SerializerMethodField` filtered by org context |
| `MenuDetailSerializer` | Full detail with nested `roles`, `user_assignments`, creator/org/product names |
| `MenuCreateUpdateSerializer` | Create/update — validates `code` (alphanumeric + underscores) and `href` (must start with `/`) |
| `MenuMyMenusResponseSerializer` | Response shape: `{ sections: {...}, all_menus: [...] }` |
| `MenuRoleSerializer` | MenuRole CRUD |
| `MenuUserSerializer` | MenuUser with `user_email`, `user_name` read-only fields |
| `AssignMenuToRoleSerializer` | Validates `role` is one of the valid roles (`Superadmin, Admin, Manager, Staff, Vendor, User`) |
| `AssignMenuToUserSerializer` | Validates `user_id` exists |
| `ProductSerializer` | Product CRUD |
| `OrgProductPurchaseSerializer` | Purchase records with `is_valid` computed field |
| `OrganizationSerializer` | Org with nested product purchases |

### Views / API Endpoints (`views.py` — 728 lines)

**`MenuViewSet`** — Core CRUD + custom actions:

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/api/menus/` | List all menus (filtered by role/org) |
| `POST` | `/api/menus/` | Create custom menu |
| `GET` | `/api/menus/{id}/` | Menu detail |
| `PUT/PATCH` | `/api/menus/{id}/` | Update menu |
| `DELETE` | `/api/menus/{id}/` | Soft-delete (sets `is_active=False`) |
| **`GET`** | **`/api/menus/my_menus/`** | **Main sidebar endpoint — returns pre-grouped, filtered menus (note: underscore in path)** |
| `POST` | `/api/menus/{id}/assign-role/` | Assign menu to role |
| `POST` | `/api/menus/{id}/remove-role/` | Remove menu from role |
| `POST` | `/api/menus/{id}/assign-user/` | Assign menu to individual user |
| `POST` | `/api/menus/{id}/remove-user/` | Remove menu from user |
| `GET/POST` | `/api/menus/user-assignments/` | Bulk get/set menu assignments per user |
| `GET` | `/api/menus/user-effective-menus/` | Admin inspection: shows all menus with role-based/direct/effective flags |

**`ProductViewSet`** — `GET /api/products/`, `GET /api/products/{id}/`
**`OrganizationViewSet`** — Full CRUD on orgs + `assign-product`/`revoke-product` actions

### Core Visibility Logic — `_get_visible_menus()` + `_auto_granted_system_menu_ids()`

```
1. Role-based menu IDs:      MenuRole where role=user.role (global + org-scoped)
2. User-specific menu IDs:   MenuUser where user=current_user
3. AUTO-GRANTED IDs:         All active SYSTEM menus (org IS NULL) if role in [Superadmin, Admin]
4. Union of all three ID sets
5. Filter:  is_active=True
            AND (required_product IS NULL OR required_product IN purchased_products)
            AND (SYSTEM + org_isnull OR CUSTOM + org=user.organization)
6. Order by: section, order
```

**Auto-grant helper** (`_auto_granted_system_menu_ids()`):
- Returns the IDs of every `type='SYSTEM'`, `organization__isnull=True`, `is_active=True` menu
- Called for `Superadmin`/`Admin` users in `_get_visible_menus`
- Called in `user_effective_menus` for admin **target** users — the SYSTEM menus are added to `role_menu_ids`, which makes them render as `role_based: true` (locked 🔒) in the User Management Assign-Menu modal

### Permissions (`permissions.py` — 90 lines)

| Class | Type | Logic |
|-------|------|-------|
| `IsSuperadmin` | Global | `user.role == 'Superadmin'` |
| `IsOrgOwner` | Global | User == org.owner |
| `CanEditMenu` | Object-level | Delegates to `menu.can_edit(user)` |
| `CanDeleteMenu` | Object-level | Delegates to `menu.can_delete(user)` |
| `IsOrgAdminOrSuperadmin` | Global | `role in ['Superadmin', 'Admin']` |

### URL Routing (`urls.py` — 24 lines)

Mounted at `/api/` in `core/urls.py`. Uses DRF `DefaultRouter`:
- `menus/` → MenuViewSet
- `products/` → ProductViewSet
- `organizations/` → OrganizationViewSet

### Migrations (`0001` → `0006`)

| Migration | Content |
|-----------|---------|
| `0001_initial` | All core models (Menu, MenuRole, Organization, Product, OrgProductPurchase) |
| `0002_seed_default_menus` | Seeds 15 SYSTEM menus on first `migrate` |
| `0003_menuuser` | Adds `MenuUser` model |
| `0004` | Adjusts MenuUser unique constraint/index naming |
| `0005_menu_unique_system_menu_code` | Global unique constraint on SYSTEM menu codes |
| **`0006_remove_nonadmin_roles_from_system_menus`** | **Data migration — deletes `MenuRole` rows on SYSTEM menus for roles other than Superadmin/Admin (staff access is now per-user only)** |

### Default Menu Seeding

**Management command** (`seed_menus.py` — 312 lines): Idempotent re-seeding with `--reset` and `--dry-run` flags.

**Role configuration (current):**
- `ADMIN_ONLY_ROLES = ["Superadmin", "Admin"]` — the **only** role group
- `MENU_ROLE_OVERRIDES = {}` — empty; all SYSTEM menus seed with `ADMIN_ONLY_ROLES`
- Role-based grants for staff/other roles are intentionally **not** seeded — those roles get menus via per-user assignment (`MenuUser`) from User Management
- Re-running the command also **removes stale role grants** (roles no longer in the config are deleted from `MenuRole`)

**Default menus (16):**

| Code | Name | Section | Icon | Auto-granted to |
|------|------|---------|------|-----------------|
| `dashboard` | Dashboard | Operations | LayoutDashboard | Superadmin, Admin |
| `contacts` | Contacts | Operations | Contact | Superadmin, Admin |
| `crm` | CRM | Operations | Briefcase | Superadmin, Admin |
| `docs` | Doc Tools | Operations | FileText | Superadmin, Admin |
| `inventory` | Inventory | Operations | Box | Superadmin, Admin |
| `hr` | HR | Operations | Users | Superadmin, Admin |
| `accounts` | Accounts | Operations | CreditCard | Superadmin, Admin |
| `media` | Media | Operations | ImageIcon | Superadmin, Admin |
| `lms` | LMS | Operations | GraduationCap | Superadmin, Admin |
| `sales-tasks` | Sales Tasks | Sales | Target | Superadmin, Admin |
| `sales-targets` | Targets | Sales | Crosshair | Superadmin, Admin |
| `sales-dashboard-team` | Team Dashboard | Sales | Users | Superadmin, Admin |
| `sales-dashboard-executive` | Executive Dashboard | Sales | BarChart3 | Superadmin, Admin |
| `invoices` | Invoices | Operations | FileText | Superadmin, Admin |
| `settings_pref` | Preferences | Settings | Settings | Superadmin, Admin |
| `admin` | Admin | Admin | ShieldCheck | Superadmin, Admin |

> **Note:** The auto-grant in `_get_visible_menus` guarantees admin visibility even if these `MenuRole` rows are missing. The seeded rows exist for consistency with the platform-management app and the Assign-Menu modal's "via role" display.

---

## Frontend Architecture (`crm_frontend/`)

### State Management — `MenuContext.jsx` (151 lines)

- **Fetches** `GET /api/menus/my_menus/` (underscore) on mount / user change
- **Caches** in `sessionStorage` (key: `menus_v2_{userId}`, TTL: 30s)
- **Refreshes** imperatively via `refreshMenus(force=false)` — pass `true` to bypass cache
- **Exports** via `useMenu()` hook: `{ menus, sections, loading, error, refreshMenus }`
- **Provider hierarchy**: `AuthProvider > MenuProvider` (in `App.jsx`)
- Warns in console if the API returns zero menus (likely unseeded DB)

### Sidebar Rendering — `Sidebar.jsx` (163 lines)

- Iterates `sections` object (e.g., `{ Operations: [...], Sales: [...], Admin: [...] }`)
- Renders section headings (uppercase, e.g. "OPERATIONS")
- Sorts items by `item.order` within each section
- Each item renders as `<Link>` with:
  - Dynamic icon via `getLucideIcon(item.icon)` (from `iconMapper.js`)
  - Display name, href, ChevronRight indicator
- **Active link detection**: exact match first, then prefix match for nested routes
- **States handled**: loading (spinner), error (red message), empty (suggestive text pointing users to ask an admin for menu assignment), empty section ("No menus available")

### Icon Resolution — `iconMapper.js` (189 lines)

- Static mapping from Lucide name strings to imported React components
- `getLucideIcon(name)` — lookup with fallback to `LayoutDashboard`
- `getAvailableIcons()` — returns full list for the (separate) platform-management app's form dropdown

### User-Management Menu Assignment UI

| Component | File | Purpose |
|-----------|------|---------|
| `UserMenuAssignModal` | `UserMenuAssignModal.jsx` (476 lines) | **Per-user menu assignment** — SYSTEM menus auto-granted to admins show as 🔒 locked (`role_based`); other menus are toggleable direct assignments. Uses `GET /user-effective-menus/` + `POST /user-assignments/` |
| `UserMenusPanel` | `UserMenusPanel.jsx` (167 lines) | Read-only view of a user's effective menus split by "Via Role" / "Direct Assigned" |

### Admin API Service — `menuService.js` (116 lines)

| Method | Endpoint |
|--------|----------|
| `getAllMenus(params)` | `GET /api/menus/` |
| `getUserDirectAssignments(userId)` | `GET /api/menus/user-assignments/` |
| `getUserEffectiveMenus(userId)` | `GET /api/menus/user-effective-menus/` |
| `bulkAssignMenusToUser(userId, menuIds)` | `POST /api/menus/user-assignments/` |
| `assignMenuToRole(menuId, role, orgId)` | `POST /api/menus/{id}/assign-role/` |
| `removeMenuFromRole(menuId, role, orgId)` | `POST /api/menus/{id}/remove-role/` |

### Admin Pages (current)

| Page | File | Path | Purpose |
|------|------|------|---------|
| Admin home | `Admin.jsx` (91 lines) | `/admin` | Card grid — currently **Company Profile** and **User Management** only |
| AdminUsers | `AdminUsers.jsx` | `/admin/users` | User Management (users/groups/audit + per-user menu assignment) |

> **Removed:** `AdminMenus.jsx`, `AdminMenuRoles.jsx`, `AdminMenuForm.jsx` and the `/admin/menus*` routes were deleted — Platform Management is now a separate app that consumes the backend API directly.

### Routing (`App.jsx`)

Routes are hardcoded but linked dynamically via menu `href` fields. Key route-to-menu mapping:

| Route | Component | Menu Code |
|-------|-----------|-----------|
| `/dashboard` | Dashboard | `dashboard` |
| `/crm` | CRM | `crm` |
| `/contacts` | Contacts | `contacts` |
| `/docs` | Doc Tools | `docs` |
| `/hr/*` | HR | `hr` |
| `/accounts` | Accounts | `accounts` |
| `/media` | Media | `media` |
| `/lms` | LMS | `lms` |
| `/inventory/*` | InventoryRoutes | `inventory` |
| `/invoices/*` | Invoice pages | `invoices` |
| `/sales/*` | SalesTaskManager | `sales-tasks` / `sales-targets` / `sales-dashboard-*` |
| `/admin` | Admin overview | `admin` |
| `/admin/users` | AdminUsers | `admin` |
| `/settings` | Settings | `settings_pref` |

---

## Complete Data Flow

```
[PostgreSQL DB]
    ↓
Django REST API → GET /api/menus/my_menus/  (filtered by role, org, products + admin auto-grant)
    ↓
Axios → MenuContext.jsx  (cached in sessionStorage, TTL 30s)
    ↓
useMenu() hook → { sections, loading, error, refreshMenus }
    ↓
Sidebar.jsx  →  renders grouped nav links with Lucide icons
    ↓
react-router-dom  →  page components
```

## Security & Access Control

1. **Authentication**: JWT token (required for all endpoints)
2. **Admin auto-grant**: SYSTEM menus are always visible to `Superadmin`/`Admin` — hard-coded, cannot be revoked
3. **Per-user assignment**: `MenuUser` rows — staff only see what an admin explicitly assigns from User Management
4. **Role grants**: `MenuRole` rows — still supported by the API (assign-role/remove-role) for the platform-management app; stale non-admin grants on SYSTEM menus are removed by migration `0006` / the seed command
5. **Product gating**: `required_product` FK — menu hidden unless org purchased the product (applies to everyone, including admins)
6. **Org scoping**: CUSTOM menus isolated per organization; SYSTEM menus are global (`organization IS NULL`)
7. **Soft-delete**: `is_active=False` hides menus without data loss
8. **Object-level checks**: `can_edit` / `can_delete` / `can_assign_user` on the Menu model gate mutations

## Key Design Decisions

1. **100% dynamic menus** — no hardcoded sidebar items
2. **Admins always see SYSTEM menus** — auto-grant makes admin visibility immune to missing role rows
3. **Staff access is per-user opt-in** — cleaner governance than bulk role grants
4. **Product gating** — menus can require a purchased product license
5. **Two menu types** — SYSTEM (global, admin-visible) and CUSTOM (org-managed)
6. **Sections are data-driven** — grouping and ordering configured in DB
7. **Static icon mapping** — icons resolved client-side via `iconMapper.js`
8. **Backend is the contract** — the separate platform-management app consumes `/api/menus/*` without coupling to this frontend

## Files Summary

### Backend (17 files)
- `menus/models.py` (231), `menus/views.py` (728), `menus/serializers.py` (160), `menus/permissions.py` (90), `menus/urls.py` (24), `menus/admin.py`, `menus/apps.py`, `menus/__init__.py`
- `menus/management/commands/seed_menus.py` (312)
- `menus/migrations/0001_initial.py` → `0006_remove_nonadmin_roles_from_system_menus.py`
- `core/settings.py`, `core/urls.py`

### Frontend (10 files)
- `src/context/MenuContext.jsx` (151), `src/components/Sidebar.jsx` (163), `src/components/Layout.jsx`
- `src/utils/iconMapper.js` (189)
- `src/modules/admin/services/menuService.js` (116)
- `src/modules/admin/pages/Admin.jsx` (91), `AdminUsers.jsx`
- `src/modules/admin/components/UserManagement/UserMenuAssignModal.jsx` (476), `UserMenusPanel.jsx` (167)
- `src/App.jsx`

## Operational Notes

- **Fresh DB**: run `python manage.py migrate` (applies `0002` seed + `0006` cleanup) then `python manage.py seed_menus` to ensure role rows match current config.
- **Re-seed safely**: `python manage.py seed_menus` is idempotent; `--dry-run` previews changes; `--reset` deletes SYSTEM menus first (destructive).
- **Assign a menu to a staff user**: User Management → Users tab → open a user → Assign Menu → toggle menus → Save (writes `MenuUser` rows via `POST /api/menus/user-assignments/`).
