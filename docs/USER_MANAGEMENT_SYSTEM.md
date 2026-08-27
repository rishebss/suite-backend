# ByteHive User Management System - Implementation Plan

**Date**: 17 April 2026
**Version**: 1.0
**Status**: In Development

---

## 📋 Overview

The User Management System provides comprehensive CRUD operations (Create, Read, Update, Delete) for managing users within ByteHive, along with complete audit logging and activity tracking. This page in the admin panel allows authorized administrators to manage all users, control their access, and monitor all user-related activities.

---

## 🎯 Key Features

### 1. **User CRUD Operations**

- ✅ Create users with roles and departments
- ✅ Read/retrieve user information
- ✅ Update user details, roles, departments
- ✅ Soft delete users (mark as inactive)
- ✅ Bulk operations (activate/deactivate, assign department)

### 2. **User Management Features**

- ✅ Role-based user management (Superadmin, Admin, Manager, Staff, Vendor, User)
- ✅ Department assignments and management
- ✅ Supervisor/subordinate relationships
- ✅ Organization multi-tenancy support
- ✅ Status management (active/inactive)

### 3. **Activity & Audit Logging**

- ✅ Track all user creation activities
- ✅ Track all user update activities
- ✅ Track all user deletion activities
- ✅ Track login/logout activities
- ✅ Track role/permission changes
- ✅ Track email/mobile verification
- ✅ Store IP address and user agent
- ✅ Detailed audit trail with timestamps

### 4. **User Interface Features**

- ✅ User list with pagination
- ✅ Advanced search and filters (role, department, status, date range)
- ✅ User creation form with validation
- ✅ User edit dialog
- ✅ User detail view
- ✅ Audit log viewer for each user
- ✅ Bulk user operations
- ✅ Activity timeline dashboard

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│              Frontend (React/Vite)                      │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Admin Panel - User Management Module            │  │
│  │  ├─ UserList.jsx (List with filters)            │  │
│  │  ├─ CreateUserForm.jsx (Create new users)       │  │
│  │  ├─ EditUserDialog.jsx (Update user)            │  │
│  │  ├─ UserDetail.jsx (View user info)             │  │
│  │  ├─ AuditLog.jsx (View user activities)         │  │
│  │  └─ ActivityDashboard.jsx (Timeline view)       │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                           ↕️
                    [API Layer]
                           ↕️
┌─────────────────────────────────────────────────────────┐
│              Backend (Django/DRF)                       │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Backend APIs                                   │  │
│  │  ├─ /api/users/ (List/Create)                   │  │
│  │  ├─ /api/users/{id}/ (Detail/Update/Delete)     │  │
│  │  ├─ /api/users/{id}/activities/ (Audit log)     │  │
│  │  ├─ /api/users/bulk-update/ (Bulk ops)          │  │
│  │  └─ /api/activities/ (Global audit log)         │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Database Models                                │  │
│  │  ├─ User (Extended model)                       │  │
│  │  ├─ AuditLog (Activity tracking)               │  │
│  │  ├─ Department                                  │  │
│  │  └─ Organization                               │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 Database Models

### **User Model** (Already exists - extending)

```python
User
├── id: UUID (Primary Key)
├── email: String (Unique)
├── first_name: String
├── last_name: String
├── mobile: String
├── password: String (Hashed)
├── role: Choice (Superadmin, Admin, Manager, Staff, Vendor, User, Others)
├── department: ForeignKey (Department)
├── supervisor: ForeignKey (User - Self)
├── organization: ForeignKey (Organization)
├── account_id: String (Unique)
├── avatar: ImageField
├── is_active: Boolean
├── is_email_verified: Boolean
├── is_mobile_verified: Boolean
├── is_staff: Boolean
├── created_at: DateTime
├── updated_at: DateTime
└── last_login: DateTime
```

### **AuditLog Model** (Already exists - extending)

```python
AuditLog
├── id: UUID (Primary Key)
├── user: ForeignKey (User) - Who performed action
├── action: String (create, update, delete, login, logout, etc.)
├── action_target: ForeignKey (User) - Which user was affected (new)
├── ip_address: String
├── user_agent: String
├── status: Choice (success, failed, pending)
├── details: JSON (Additional metadata)
├── created_at: DateTime
└── target_changes: JSON (What changed - for updates)
```

### **Department Model** (Already exists)

```python
Department
├── id: UUID
├── name: String (Unique)
├── description: Text
├── manager: ForeignKey (User)
├── created_at: DateTime
└── updated_at: DateTime
```

---

## 🔌 Backend API Endpoints

### **User Management Endpoints**

#### 1. **List Users**

```
GET /api/users/
Query Parameters:
  - page: integer (default: 1)
  - page_size: integer (default: 20)
  - role: string (filter by role)
  - department_id: UUID (filter by department)
  - organization_id: UUID (filter by organization)
  - status: string (active/inactive)
  - search: string (search email, name, account_id)
  - order_by: string (created_at, email, first_name)

Response:
{
  "count": 150,
  "next": "...",
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "account_id": "SA-ADM-AA00A00",
      "role": "Admin",
      "department": {"id": "uuid", "name": "IT"},
      "is_active": true,
      "is_email_verified": true,
      "last_login": "2026-04-17T10:30:00Z",
      "created_at": "2026-04-15T08:00:00Z"
    }
  ]
}

Permissions: Superadmin, Admin (own org only)
```

#### 2. **Create User**

```
POST /api/users/
Request Body:
{
  "email": "newuser@example.com",
  "first_name": "Jane",
  "last_name": "Smith",
  "mobile": "9876543210",
  "password": "SecurePass123!",
  "role": "Manager",
  "department_id": "uuid",
  "supervisor_id": "uuid (optional)",
  "gender": "Female",
  "organization_id": "uuid"
}

Response:
{
  "id": "uuid",
  "email": "newuser@example.com",
  "account_id": "SA-MGR-AA00A01",
  "role": "Manager",
  "is_active": true,
  "created_at": "2026-04-17T10:00:00Z"
}

Audit Log: Logged with action='user_create'
Permissions: Superadmin, Admin
```

#### 3. **Get User Details**

```
GET /api/users/{id}/
Response:
{
  "id": "uuid",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "mobile": "9876543210",
  "account_id": "SA-ADM-AA00A00",
  "role": "Admin",
  "department": {
    "id": "uuid",
    "name": "IT",
    "description": "..."
  },
  "supervisor": {
    "id": "uuid",
    "first_name": "Manager",
    "last_name": "Name"
  },
  "organization": {
    "id": "uuid",
    "name": "Main Office"
  },
  "avatar": "url",
  "is_active": true,
  "is_email_verified": true,
  "is_mobile_verified": false,
  "is_staff": false,
  "is_superuser": false,
  "created_at": "2026-04-15T08:00:00Z",
  "updated_at": "2026-04-15T08:00:00Z",
  "last_login": "2026-04-17T10:30:00Z"
}

Permissions: Self, Superadmin, Admin (same org)
```

#### 4. **Update User**

```
PATCH /api/users/{id}/
Request Body:
{
  "first_name": "John",
  "last_name": "Smith",
  "mobile": "9876543210",
  "role": "Manager",
  "department_id": "uuid",
  "supervisor_id": "uuid",
  "is_active": true,
  "avatar": "file"
}

Response:
{
  "id": "uuid",
  "email": "user@example.com",
  ... (updated fields)
}

Audit Log: Logged with action='user_update', target_changes shows what changed
Permissions: Self (limited), Superadmin, Admin
```

#### 5. **Delete User (Soft Delete)**

```
DELETE /api/users/{id}/
Response:
{
  "message": "User deactivated successfully"
}

Audit Log: Logged with action='user_delete'
Permissions: Superadmin, Admin
```

#### 6. **Get User Activities/Audit Log**

```
GET /api/users/{id}/activities/
Query Parameters:
  - page: integer
  - page_size: integer
  - action: string (filter by action type)
  - date_from: datetime
  - date_to: datetime

Response:
{
  "count": 45,
  "results": [
    {
      "id": "uuid",
      "action": "login",
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0...",
      "status": "success",
      "details": {},
      "created_at": "2026-04-17T14:30:00Z"
    },
    {
      "id": "uuid",
      "action": "password_change",
      "status": "success",
      "created_at": "2026-04-16T10:15:00Z"
    },
    {
      "id": "uuid",
      "action": "profile_update",
      "target_changes": {
        "first_name": {"old": "John", "new": "Jane"},
        "department_id": {"old": "uuid1", "new": "uuid2"}
      },
      "created_at": "2026-04-15T09:00:00Z"
    }
  ]
}

Permissions: Self, Superadmin, Admin
```

#### 7. **Bulk Update Users**

```
PATCH /api/users/bulk-update/
Request Body:
{
  "user_ids": ["uuid1", "uuid2", "uuid3"],
  "updates": {
    "department_id": "uuid",
    "is_active": true
  }
}

Response:
{
  "updated_count": 3,
  "updated_users": [...]
}

Audit Log: Individual logs for each user updated
Permissions: Superadmin, Admin
```

#### 8. **Get All Activities (Global Audit Log)**

```
GET /api/activities/
Query Parameters:
  - page: integer
  - page_size: integer
  - action: string
  - user_id: UUID (filter by actor)
  - action_target_id: UUID (filter by affected user)
  - date_from: datetime
  - date_to: datetime
  - status: string (success/failed)

Response:
{
  "count": 1250,
  "results": [
    {
      "id": "uuid",
      "user": {
        "id": "uuid",
        "email": "admin@example.com",
        "first_name": "Admin"
      },
      "action": "user_create",
      "action_target": {
        "id": "uuid",
        "email": "newuser@example.com",
        "first_name": "New"
      },
      "ip_address": "192.168.1.1",
      "status": "success",
      "details": {},
      "created_at": "2026-04-17T14:30:00Z"
    }
  ]
}

Permissions: Superadmin, Admin
```

---

## 🎨 Frontend Components & Pages

### **Module Structure**

```
src/modules/admin/
├── components/
│   ├── UserManagement/
│   │   ├─ UserList.jsx         # Main user list with filters
│   │   ├─ UserTable.jsx        # Table component
│   │   ├─ UserRow.jsx          # Individual user row
│   │   ├─ CreateUserForm.jsx   # Create new user form
│   │   ├─ EditUserDialog.jsx   # Edit user modal
│   │   ├─ UserDetail.jsx       # Full user detail view
│   │   ├─ AuditLog.jsx         # User's activity log
│   │   ├─ ActivityTimeline.jsx # Timeline view of activities
│   │   ├─ UserFilters.jsx      # Filter controls
│   │   ├─ BulkActions.jsx      # Bulk operation controls
│   │   └─ DeleteConfirm.jsx    # Delete confirmation dialog
│   └─ ...
├── pages/
│   ├─ AdminUsers.jsx           # Main page wrapper
│   └─ ...
├── hooks/
│   ├─ useUsers.js              # User CRUD operations hook
│   └─ useAuditLog.js           # Activity log hook
├── services/
│   ├─ userService.js           # API calls
│   └─ auditService.js          # Audit API calls
└─ ...
```

### **Key Pages**

#### 1. **User List Page** (`AdminUsers.jsx`)

- Display table with users
- Filters: Role, Department, Status, Date Range, Search
- Pagination
- Bulk select with actions (activate, deactivate, assign department)
- Create user button
- Edit/View/Delete actions per row

#### 2. **Create/Edit User Form** (`CreateUserForm.jsx`, `EditUserDialog.jsx`)

- Form fields: Email, First Name, Last Name, Mobile, Password
- Role selection
- Department selection
- Supervisor selection
- Gender selection
- Email verification status
- Organization selection (for admin)
- Form validation
- Loader on submit

#### 3. **User Detail View** (`UserDetail.jsx`)

- All user information
- Avatar display
- Account ID
- Department & Supervisor
- Verification status
- Creation date
- Last login
- Button to view activities
- Edit and Delete buttons

#### 4. **Activity/Audit Log** (`AuditLog.jsx`)

- List of all activities for a user
- Filter by action type
- Filter by date range
- Each log entry shows:
  - Action type with icon
  - Status (success/failed)
  - Details (IP, User Agent if login)
  - Changes if update (what changed)
  - Timestamp
- Activity Timeline view (`ActivityTimeline.jsx`)

#### 5. **Global Activity Dashboard** (`ActivityDashboard.jsx`)

- Overview statistics
- Recent activities
- Filter by action type, user, date
- Export capability

---

## 🔐 Permissions & Security

### **Backend Permissions**

```python
class IsUserAdmin(BasePermission):
    """
    Allow only superadmin or organization admin to manage users
    """
    def has_permission(self, request, view):
        return request.user.role in ['Superadmin', 'Admin']

    def has_object_permission(self, request, view, obj):
        # Admin can only manage users in their organization
        if request.user.role == 'Superadmin':
            return True
        if request.user.role == 'Admin':
            return obj.organization_id == request.user.organization_id
        # Users can only view/update their own profile
        return request.user.id == obj.id
```

### **Frontend Permission Checks**

- Only show user management to Admin/Superadmin
- Disable edit for users outside own organization (for org admins)
- Hide sensitive fields for non-admin users viewing other profiles
- Audit log visible by self, admins, and supervisors

---

## 📝 Audit Logging Actions

### **User Management Related Actions**

```
Action Types:
├── user_create: New user created
├── user_update: User information updated (shows what fields changed)
├── user_delete: User soft deleted (deactivated)
├── user_activate: User reactivated
├── user_role_change: User role changed
├── user_department_change: User department changed
├── user_supervisor_change: Supervisor assigned/changed
├── email_verify: Email verification completed
├── mobile_verify: Mobile verification completed
├── password_change: Password changed
├── avatar_upload: Profile picture changed
└── bulk_user_operation: Bulk operations performed

Each log includes:
├── action: Action type
├── user: Who performed the action
├── action_target: Which user was affected
├── ip_address: From where request came
├── user_agent: Browser/client info
├── status: success/failed/pending
├── details: JSON with additional data
├── target_changes: What fields changed (for updates)
└── created_at: Timestamp
```

---

## 🛠️ Implementation Phases

### **Phase 1: Backend Foundation** (Todo 2)

- [x] Extend AuditLog model with `action_target` field
- [x] Create UserSerializer for list/detail
- [x] Create UserCreateSerializer with validation
- [x] Create UserUpdateSerializer
- [x] Implement UserViewSet with CRUD
- [x] Implement AuditLogViewSet
- [x] Add permission classes
- [x] Create audit logging signals
- [x] Write tests

### **Phase 2: Frontend Components** (Todo 4)

- [x] Create UserList page with table
- [x] Create CreateUserForm component
- [x] Create EditUserDialog component
- [x] Create AuditLog viewer
- [x] Create UserFilters component
- [x] Add styling per design system

### **Phase 3: Integration & Testing** (Todo 6)

- [x] Connect frontend to backend APIs
- [x] Test CRUD operations
- [x] Test filters and search
- [x] Test audit logging
- [x] Test permissions
- [x] Load testing

---

## 🚀 Current Status

**Completed:**

- ✅ User and AuditLog models exist
- ✅ Basic authentication setup
- ✅ Menu system implementation

**To Be Completed:**

- ⏳ Extend AuditLog model (action_target, target_changes fields)
- ⏳ Create comprehensive UserViewSet with filtering
- ⏳ Implement audit logging for all user operations
- ⏳ Create frontend user management module
- ⏳ Implement activity dashboard

---

## 🔗 Related Documentation

- [Architecture Document](./architecture.md)
- [Menu System](./MENU_SYSTEM_IMPLEMENTATION.md)
- [API Endpoints Verification](./API_ENDPOINTS_VERIFICATION.md)

---

## 📞 Questions for Implementation

1. Should role changes require approval/confirmation?
2. Should bulk delete be allowed or only deactivation?
3. Do you want email notifications on user creation?
4. Should activity export be in CSV/PDF format?
5. Should there be a "super admin only" section separate from organization admins?

---

**Last Updated**: 17 April 2026
**Created By**: GitHub Copilot
**Status**: Implementation Ready
