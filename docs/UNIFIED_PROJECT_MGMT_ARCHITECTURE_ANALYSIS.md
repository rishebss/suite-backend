# Unified Project & Work Management Module — Architectural Analysis & Implementation Blueprint
## Hertex Business Suite — *HertexFlow*

**Date:** July 22, 2026  
**Based On:** `Unified-Project-Management-Module-Plan.md`  
**Status:** Pre-Implementation Architecture Analysis v1.0

---

## Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [Current Codebase Analysis — Backend](#2-current-codebase-analysis--backend)
3. [Current Codebase Analysis — Frontend](#3-current-codebase-analysis--frontend)
4. [Gap Analysis: Current vs. Target Architecture](#4-gap-analysis-current-vs-target-architecture)
5. [Recommended Architecture](#5-recommended-architecture)
6. [Detailed Implementation Plan — Phase 0](#6-detailed-implementation-plan)
7. [Industry Best Practices Applied](#7-industry-best-practices-applied)
8. [Risk Assessment & Mitigations](#8-risk-assessment--mitigations)
9. [Appendix: Key Files & References](#9-appendix-key-files--references)

---

## 1. Executive Summary

This document analyzes the current **ByteHive Business ERP** codebase (both Django REST backend and React frontend) against the requirements in the **Unified Project Management Module Plan** (`docs/Unified-Project-Management-Module-Plan.md`). 

**Key finding:** The existing codebase already contains **~70% of the foundational building blocks** needed for this module — particularly:
- A working **CRM Pipeline → Stage → Deal** model (perfect workflow engine foundation)
- A sophisticated **Sales Task Manager** with targets, programmes, tasks, dependencies, time tracking, resource allocation, activity logs, and assignment engines
- **Kanban board** implementations already in CRM and Sales Task Manager using `@dnd-kit`
- A **robust RBAC permission system** with organization scoping
- **Activity audit logging** patterns (SalesTaskLog, ContactLog, AuditLog)

**What needs to be built:** The "unified engine" layer — Workspaces → Projects → Work Items → Configurable Workflows — that sits above and connects the existing CRM and Sales Task Manager modules, while adding Dev Mode (sprints, epics, story points) and Generic Mode (ticketing, approvals).

**Recommended Approach:** Evolve, don't replace. The existing `sales_task_manager` models should be generalized into a shared `project_management` app that the CRM module and any new department modes can hook into through `issue_type` differentiation.

---

## 2. Current Codebase Analysis — Backend

### 2.1 Core Architecture Patterns

| Pattern | Implementation | Notes |
|---|---|---|
| **Base Model** | `core.models.Main` | Abstract model with UUID `id`, `created_at`, `updated_at` — all models inherit from this |
| **Auth** | `authentication.models.User` | Custom user, email-based, JWT (SimpleJWT), roles: Superadmin/Admin/Manager/Staff/Vendor/Finance/etc. |
| **Permissions** | Role-based via custom classes in each module's `permissions.py` | Module-level, not yet unified for cross-module access |
| **API Pattern** | DRF ModelViewSets + Nested Routers (rest_framework_nested) | Consistent across all modules |
| **Business Logic** | `services/` directory per module | CRM has inline logic, but sales_task_manager has separated services |
| **Serialization** | DRF Serializers with nested read-only fields pattern | Consistent across modules |
| **Dept/Org** | `Department` (team) + `Organization` (company) | Organization scoping exists but not consistently applied |

### 2.2 Raw Material: CRM Module (`/crm/`)

**Models:**
```python
Pipeline(Main)           # Configurable pipeline with stages
  ├── departments M2M    # Which departments can access
  ├── assignment_type    # round_robin, least_loaded, single_user, manual
  ├── pipeline_type      # sales, retarget, clients
  ├── mandatory_fields   # JSON config for required fields
  └── custom_fields_enabled

Stage(Main)              # Dynamic stage tied to a pipeline
  ├── pipeline FK
  ├── name, slug, order, color
  └── unique_together: (pipeline, slug)

CRM(Main)                # Deal/Entry
  ├── pipeline FK
  ├── stage FK
  ├── contact FK → Contact
  ├── assigned_user FK → User
  ├── value, priority, notes
  └── Indexes: (pipeline, stage), (pipeline, assigned_user)
```

**Key strengths for HertexFlow:**
- Pipeline + Stage model is **exactly the configurable workflow engine** the plan describes
- Assignment strategies (round_robin, least_loaded) are already implemented
- Stage colors and ordering are configurable
- Bulk add/move operations exist

**Limitations:**
- Hardcoded to `Contact` — can't assign work items to non-contact entities
- No universal `issue_type` field — deals are just "deals"
- No `custom_fields` JSON field on the deal itself (only at pipeline level)
- No sprint/cycle or epic concepts
- No dependency tracking between deals

### 2.3 Raw Material: Sales Task Manager (`/sales_task_manager/`)

**Models (already very close to the plan's "Universal Work Item"):**

```python
TargetCycle(Main)            # Like a Sprint/Quarter
  ├── name, code, cycle_type (ANNUAL/HALF_YEARLY/QUARTERLY/MONTHLY)
  ├── start_date, end_date
  ├── status (DRAFT/ACTIVE/CLOSED/ARCHIVED)
  ├── total_revenue_target
  ├── task_auto_generation_enabled
  └── sprint_duration_days  # ← Already sprint-aware!

SalesTarget(Main)            # Target/Quota per user/team
  ├── cycle FK
  ├── assignee_type (USER/TEAM/DEPARTMENT)
  ├── assigned_user / assigned_department
  ├── target_amount, achieved_amount, weighted_progress_pct
  ├── new_business_target, renewal_target, upsell_target
  └── status (NOT_STARTED/IN_PROGRESS/ACHIEVED/EXCEEDED/MISSED)

TargetLineItem(Main)         # Revenue expectation linked to CRM deal
  ├── sales_target FK
  ├── crm_deal FK → CRM
  ├── description, expected_amount, expected_close_date
  ├── probability (LOW/MEDIUM/HIGH/COMMITTED)
  └── is_attained, actual_revenue

SalesProgramme(Main)         # Sales initiative / Project
  ├── name, description
  ├── target_cycle FK, sales_target FK
  ├── start_date, end_date, priority, status
  ├── target_revenue, actual_revenue
  ├── team_members M2M → User
  └── programme_manager FK → User

ProgrammeMilestone(Main)     # Significant events in a programme
  ├── programme FK
  ├── target_date, completed_date
  ├── milestone_type, status
  └── revenue_impact

SalesTask(Main) ✦            # *** The MOST IMPORTANT model ***
  ├── programme FK, sales_target FK (nullable)
  ├── title, description
  ├── task_type (CALL/MEETING/DEMO/PROPOSAL/.../OTHER)
  ├── priority (CRITICAL/HIGH/MEDIUM/LOW)
  ├── status (BACKLOG/TODO/IN_PROGRESS/IN_REVIEW/DONE/BLOCKED/CANCELLED)
  ├── assigned_to FK → User, assigned_by FK → User
  ├── due_date, started_at, completed_at
  ├── estimated_hours, actual_hours
  ├── crm_deal FK → CRM (nullable)
  ├── contact FK → Contact (nullable)
  ├── revenue_impact, weight_pct
  ├── order, is_auto_generated
  └── **Indexes**: (programme, status), (assigned_to, status), (crm_deal), (due_date), (sales_target)

TaskDependency(Main)         # FINISH_TO_START, START_TO_START, etc.
  ├── task FK, depends_on FK
  └── dependency_type

TaskTimeLog(Main)            # Time spent tracking
  ├── task FK, user FK
  └── date, hours, description

ProgrammeResourceAllocation(Main)
  ├── programme FK, user FK
  ├── allocation_pct, role
  └── start_date, end_date

TargetAssignmentRule(Main)   # Auto-assignment rule engine
  ├── trigger (TARGET_CREATED/DEAL_STAGE_CHANGE/etc.)
  ├── assignment_strategy (DEAL_OWNER/TARGET_OWNER/LEAST_LOADED/etc.)
  └── task_title/description_template (with {{variables}})

SalesTaskLog(Main)           # Activity log for all changes
  ├── task / sales_target (nullable FKs)
  ├── activity_type (15+ types including TASK_CREATED/STATUS_CHANGED/etc.)
  ├── description, metadata (JSON)
  └── indexes: (task, created_at), (sales_target, created_at)

TaskAttachment(Main)         # File attachments
```

**Key strengths for HertexFlow:**
- `SalesTask` is already **85% of the Universal Work Item** — has status, priority, assignee, time tracking, dependencies, attachments, activity logs
- Task dependencies with multiple types (FINISH_TO_START, etc.) already implemented
- Time tracking and resource allocation models exist
- Auto-generation engine with template variables
- Weighted progress calculation (complex algorithm in `progress_tracker.py`)
- Activity log with metadata JSON already in place
- Programme milestones model exists
- Kanban board already built for sales tasks with @dnd-kit

**Limitations:**
- `SalesTask` is hardcoded to sales context — no `issue_type` field (Epic/Story/Bug/Ticket/Deal)
- No Epic model (the hierarchical Epic → Story/Task/Bug pattern)
- No Sprint/Cycle model (TargetCycle is close but not identical)
- No generic Work Item shared across departments
- `revenue_impact` and `weight_pct` are sales-specific
- No custom_fields JSON on tasks
- No linked_items (blocks/is_blocked_by/relates_to) — only strict dependencies
- No SLA tracking
- No customer-facing portal concept

### 2.4 Raw Material: Permission System (`/authentication/`)

**Roles available:** Superadmin, Admin, Manager, Staff, Vendor, Finance, Payroll Executive, User, Others

**Key permission classes:**
| Class | Scope | Already Used In |
|---|---|---|
| `IsUserAdmin` | Superadmin/Admin | User management |
| `IsSuperAdmin` | Superadmin only | Critical ops |
| `IsAdminOrReadOnly` | Admin write, all read | Multiple modules |
| `IsSalesManager` | Superadmin/Admin/Manager | Sales Task Manager |
| `IsSalesAdmin` | Superadmin/Admin | Sales Task Manager config |
| `IsTaskOwnerOrManager` | Object-level: owner/supervisor/admin | Task operations |
| `CanAssignTasks` | Manager+ can assign | Task assignment |
| `CanManageProgrammes` | Manager+ can manage | Programme CRUD |
| `CanManageConfig` | Admin+ for config | Assignment rules |

**Strengths for HertexFlow:**
- Role hierarchy already supports the plan's Org Admin → Project Admin → Team Lead → Member → Viewer
- Organization scoping exists (Admin scoped to their org)
- Supervisor relationship enables manager views of team data
- Department M2M enables team-based access

**Gaps:**
- No workspace-level permissions (only org-level)
- No project-level role (Admin/Editor/Viewer per project)
- No client/requester portal role
- No field-level permission for sensitive data

### 2.5 Existing Services & Engines (Reusable)

| Service | Purpose | Reusability for HertexFlow |
|---|---|---|
| `target_engine.py` | Target achievement calculation, cascade finalization | Rename → `work_item_engine.py` |
| `task_generator.py` | Auto-generate tasks from rules/templates | Directly reusable for automation engine |
| `assignment_engine.py` | Round-robin, least-loaded, deal-owner, etc. | Directly reusable |
| `progress_tracker.py` | Weighted progress, critical path, dependency checking, programme health | Core engine for all dashboards |
| CRM `views.py` assignment logic | Round-robin/least-loaded for deals | Should be unified with assignment_engine |

---

## 3. Current Codebase Analysis — Frontend

### 3.1 Architecture Overview

| Aspect | Current Pattern | Notes |
|---|---|---|
| **Framework** | React 18+ with Vite | Modern, fast |
| **Routing** | React Router v6 with nested routes | `/module/*` pattern |
| **State** | Context API + custom hooks | AuthContext, SalesTaskContext, HRContext, MenuContext |
| **API Layer** | Direct axios calls in services files | Two patterns: shared `api.js` instance and module-level axios |
| **UI** | Tailwind CSS, dark theme, `cn()` utility | Consistent dark aesthetic |
| **Drag & Drop** | `@dnd-kit/core` + `@dnd-kit/sortable` | Already used in CRM and Sales Task boards |
| **Icons** | Lucide React | Consistent icon library |
| **Component Lib** | Custom shadcn/ui style components | `button.jsx`, `card.jsx`, `input.jsx`, `select.jsx` |

### 3.2 Raw Material: CRM Frontend

**KanbanBoard.jsx** — Implements droppable columns with:
- Column color coding (from DB `Stage.color`)
- Sortable cards via `@dnd-kit/sortable`
- Loading more items per column
- "Drop deals here" empty state
- Column header with count

**KanbanCard.jsx** — Implements draggable cards with:
- Status color badges
- Priority badges (High/Medium/Low)
- Contact info display
- "View" action button
- Drag overlay with visual feedback
- `useSortable` for drag-and-drop

**CRM Kanban is prototype-quality** — built for deals only, but the drag-and-drop logic, column color mapping, empty states, and card animations are all directly reusable.

### 3.3 Raw Material: Sales Task Manager Frontend

**SalesTaskContext.jsx** — Provides:
- Active selections (cycle, target, programme, task)
- Filter state (programme, assignee, status, priority, type, dates)
- View mode (kanban/list)
- Sidebar collapse state
- `clearSelection()`, `clearFilters()`, `setFilter()` actions

**TaskBoard.jsx** — Full-featured Kanban board:
- 6-column layout (Backlog → To Do → In Progress → In Review → Done → Blocked)
- Programme filter dropdown
- "Add Task" button
- `<FilterBar />` component
- Task detail dialog
- Task create dialog
- `DndContext` with drag detection and status update on drop
- Progress tracking (done/total)

**TaskCard.jsx** — Draggable task cards (not read but referenced in TaskBoard)

**Hooks pattern (critical pattern to follow):**
```javascript
// useSalesTasks.js - accepts params, returns {tasks, loading, refetch}
// useSalesProgrammes.js - returns {programmes, loading}
// useSalesTargets.js - returns {targets, loading, refetch}
// useTargetCycles.js - returns {cycles, loading}
// useDashboard.js - returns dashboard data by role
```

**SalesTaskService.js** — Complete API service with functions for:
- Target Cycles CRUD + activate/close/summary
- Sales Targets CRUD + assign/generate-tasks/progress/bulk-create
- Target Line Items CRUD
- Sales Programmes CRUD + members/gantt/resource-load
- Milestones CRUD + achieve
- Tasks CRUD + assign/start/complete/block/bulk-reorder/bulk-update-status/my-tasks/by-deal
- Task Dependencies CRUD
- Time Logs CRUD + summary
- Resource Allocations CRUD
- Assignment Rules CRUD
- Activity Logs (read-only)
- Dashboards (executive/manager/my-target)

### 3.4 Existing Patterns to Replicate for New Module

**Module structure (React):**
```
/src/modules/project-management/
  ├── context/ProjectManagementContext.jsx    # Global state (like SalesTaskContext)
  ├── pages/
  │   ├── WorkspaceDashboard.jsx              # Main workspace view
  │   ├── ProjectBoard.jsx                    # Kanban/Scrum board
  │   ├── Backlog.jsx                         # Sprint backlog
  │   ├── SprintDetail.jsx                    # Sprint planning
  │   ├── Roadmap.jsx                         # Epic/timeline view
  │   ├── PipelineView.jsx                    # Sales pipeline
  │   └── TicketQueue.jsx                     # Support ticket view
  ├── components/
  │   ├── KanbanBoard.jsx                     # Reuse pattern from CRM
  │   ├── KanbanCard.jsx                      # Reuse pattern from CRM
  │   ├── WorkItemDialog.jsx                  # Universal item detail
  │   ├── SprintSelector.jsx                  # Sprint/cycle picker
  │   ├── EpicGantt.jsx                       # Gantt/timeline
  │   ├── FilterBar.jsx                       # Reuse pattern
  │   └── PermissionGuard.jsx                 # Role-based visibility
  ├── services/projectService.js              # API service
  ├── hooks/
  │   ├── useWorkspaces.js
  │   ├── useProjects.js
  │   ├── useWorkItems.js
  │   ├── useSprints.js
  │   └── useDashboard.js
  └── ProjectRoutes.jsx                       # Nested routes
```

---

## 4. Gap Analysis: Current vs. Target Architecture

| Plan Requirement | Current State | Gap | Effort |
|---|---|---|---|
| **Org → Workspace → Project → Work Item** | Has Organization + Department, no Workspace/Project models | Missing hierarchy layer | **Medium** |
| **Universal Work Item with issue_type** | SalesTask (sales-specific) + CRM Deal (crm-specific) | No shared entity, no issue_type | **High** |
| **Configurable Workflow Engine** | Pipeline + Stage model exists, but tied to CRM | Stages tied to pipelines, not to work items | **Medium** |
| **Dev Mode (Sprints, Epics, Story Points)** | TargetCycle (close), no Epic, no backlogs | Missing sprint, epic, backlog concepts | **High** |
| **Sales Mode (Targets, Quotas)** | ✅ **Fully implemented** in sales_task_manager | None — build on existing | **None** |
| **Support Ticketing (SLAs, Queues)** | HR has basic ticket model, no SLA engine | Needs queue + SLA timer system | **High** |
| **Approval Workflows** | No generic approval engine | Needs multi-step approval system | **Medium** |
| **Automation Rule Builder** | TargetAssignmentRule exists for sales only | Needs generalization + trigger-action UI | **Medium** |
| **Multi-channel Notifications** | Email via Django, no Slack/WhatsApp integration | Needs notification framework | **Medium** |
| **Unified Dashboard** | Separate CRM + Sales dashboards | Needs cross-department executive view | **Low-Medium** |
| **Real-time Updates** | No WebSocket integration | Needs Django Channels + Redis | **High** |
| **Custom Fields** | Pipeline-level flag, no implementation | Needs JSON field UI + validation | **Medium** |
| **Global Search** | No cross-entity search | Needs Postgres full-text or Elasticsearch | **Medium** |
| **Mobile Responsive** | ✅ Works, but no dedicated mobile app | Phase 3 concern | **None now** |
| **Multi-tenancy** | Org exists but not fully isolated | Needs tenant isolation | **High** |

### 4.1 What Can Be DIRECTLY Reused (Minimal Changes)

| Component | Where | Action |
|---|---|---|
| SalesTask model → becomes Work Item base | `sales_task_manager/models.py` | Add `issue_type` field, rename conceptual |
| SalesTask services (progress, generation, assignment) | `sales_task_manager/services/` | Import in new module, extend |
| CRM Pipeline + Stage → becomes Workflow Engine | `crm/models.py` | Move to shared app, add workflow presets |
| SalesTask Log → becomes universal Activity Log | `sales_task_manager/models.py` | Add to shared models |
| KanbanBoard + KanbanCard (frontend) | CRM + Sales Task Manager | Refactor into shared components |
| TaskBoard (frontend) | Sales Task Manager | Refactor to use issue_type filtering |
| Permission classes | `auth/permissions.py`, `sales_task_manager/permissions.py` | Extend with workspace/project scope |
| TargetCycle → Sprint/Cycle | `sales_task_manager/models.py` | Add `sprint_goal`, `capacity` fields |
| TaskDependency | `sales_task_manager/models.py` | Directly reusable |
| TaskTimeLog | `sales_task_manager/models.py` | Directly reusable |
| ProgrammeResourceAllocation | `sales_task_manager/models.py` | Generalize to project resource allocation |
| ProgrammeMilestone | `sales_task_manager/models.py` | Generalize to project milestones |

### 4.2 What Needs to Be Built From Scratch

| Component | Priority | Estimated Work |
|---|---|---|
| **Workspace + Project models** | P0 | 2-3 days |
| **Work Item model (generalized from SalesTask)** | P0 | 2-3 days |
| **Sprint/Cycle model with capacity** | P0 (Dev Mode) | 1-2 days |
| **Epic model with hierarchy** | P0 (Dev Mode) | 1 day |
| **Configurable Workflow Engine (unified from Pipeline+Stage)** | P0 | 3-4 days |
| **SLA Timer engine** | P1 (Ticketing) | 2-3 days |
| **Backlog view (drag-to-reorder)** | P0 | 3-4 days |
| **Burndown/Velocity chart engine** | P1 | 2-3 days |
| **WebSocket real-time updates** | P1 | 3-5 days |
| **Customer portal (basic)** | P2 | 5-7 days |

---

## 5. Recommended Architecture

### 5.1 Backend: New `project_management` App

```
bytehive_business_backend/project_management/
├── __init__.py
├── apps.py                    # AppConfig: 'project_management'
├── models.py                  # All shared data models
│   ├── Organization           # (already exists in menus, extend)
│   ├── Workspace              # NEW — top-level container
│   ├── Project                # NEW — department-specific space
│   ├── ProjectTeam            # NEW — team within a project
│   ├── ProjectMember          # NEW — per-project roles
│   ├── WorkItemType           # NEW — configurable issue types
│   ├── WorkItemStatus         # NEW — configurable statuses
│   ├── Workflow               # NEW — ordered statuses + transitions
│   ├── WorkItem               # ✦ THE UNIVERSAL ENTITY
│   ├── Sprint                 # NEW — time-boxed iterations
│   ├── Epic                   # NEW — hierarchical parent
│   ├── WorkItemDependency     # ← FROM sales_task_manager
│   ├── WorkItemTimeLog        # ← FROM sales_task_manager
│   ├── WorkItemAttachment     # ← FROM sales_task_manager
│   ├── WorkItemComment        # ✦ NEW — threaded comments
│   ├── WorkItemActivityLog    # ← FROM sales_task_manager
│   ├── Milestone              # ← FROM ProgrammeMilestone
│   ├── ResourceAllocation     # ← FROM ProgrammeResourceAllocation
│   ├── SLA_Policy             # NEW — for ticketing mode
│   └── AutomationRule         # ← FROM TargetAssignmentRule (generalized)
├── serializers.py             # DRF serializers
├── views.py                   # ViewSets + custom actions
├── urls.py                    # REST router
├── permissions.py             # Permission classes
│   ├── IsOrgAdmin
│   ├── IsWorkspaceAdmin
│   ├── IsProjectAdmin
│   ├── IsProjectMember
│   └── HasProjectRole(role)
├── admin.py                   # Django admin
├── signals.py                 # Signal handlers
│   ├── WorkItem → auto-update parent progress
│   └── Sprint → auto-close tasks
├── services/
│   ├── __init__.py
│   ├── workflow_engine.py     # Validate transitions, enforce gates
│   ├── sprint_engine.py       # Sprint lifecycle, capacity calc
│   ├── backlog_engine.py      # Prioritization, reorder
│   ├── progress_engine.py     # ← FROM progress_tracker.py (generalized)
│   ├── assignment_engine.py   # ← FROM assignment_engine.py
│   ├── automation_engine.py   # ← FROM task_generator.py (generalized)
│   ├── sla_engine.py          # NEW — SLA timer management
│   ├── notification_engine.py # NEW — multi-channel dispatch
│   └── burndown_engine.py     # NEW — chart data computation
├── migrations/
│   └── ...
└── management/commands/
    └── seed_workflows.py      # Seed default workflow presets
```

> **⚠️ PHASE 0 MUST BE LEAN — SEE CORRECTED MODEL BELOW**
> The model shown here is the *final target state* after all phases. For Phase 0, use the **Corrected Phase 0 WorkItem Model** in the notes below.

### 5.2 The Universal Work Item Model

```python
class WorkItem(Main):
    """The universal entity — every ticket, task, story, bug, deal, or request."""
    
    # ═══ PHASE 0 MINIMUM: Only 12 core fields ═══
    
    # Hierarchy
    project = models.ForeignKey('Project', on_delete=models.CASCADE, related_name='work_items')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subtasks')
    
    # Identification
    key = models.CharField(max_length=20, db_index=True)  # e.g., "PROJ-142"
    issue_type = models.CharField(max_length=20, choices=ISSUE_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Workflow
    status = models.ForeignKey('WorkItemStatus', on_delete=models.PROTECT, related_name='work_items')
    
    # Prioritization
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES)
    order = models.IntegerField(default=0)
    
    # Assignment
    assignee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_items')
    reporter = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reported_items')
    
    # Dates
    due_date = models.DateTimeField(null=True, blank=True)
    
    # Extensibility (available from day one but optional)
    custom_fields = models.JSONField(default=dict, blank=True)
    labels = models.JSONField(default=list, blank=True)
    
    # ═══ ADD IN PHASE 1 (Dev Mode) ═══
    # epic = FK('self'), sprint = FK('Sprint'), story_points = IntegerField
    # started_at, completed_at, estimated_hours, actual_hours
    # watchers = M2M(User)
    
    # ═══ ADD IN PHASE 2 (Sales Mode) ═══
    # Use WorkItemLink table instead of direct FKs:
    #   WorkItemLink(source_item, target_item, relation_type)
    # Do NOT add direct FKs to crm.CRM or sales_task_manager.SalesTarget
    
    # ═══ ADD IN PHASE 2.5 (Ticketing) ═══
    # sla_policy = FK('SLA_Policy'), first_response_at
    
    class Meta:
        ordering = ['order', '-created_at']
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['assignee', 'status']),
            models.Index(fields=['key']),
            models.Index(fields=['issue_type']),
            models.Index(fields=['due_date']),
        ]
```

**CRITICAL DESIGN DECISIONS:**
1. **Use a `WorkItemLink` table, not JSON or direct FKs** for cross-module relationships. This preserves referential integrity, supports querying, and avoids schema migrations when new modules integrate.
2. **No direct FKs to `crm.CRM`, `invoices.Invoice`, or `sales_task_manager.SalesTarget`** in Phase 0. Use GenericForeignKey or the link table instead to prevent tight coupling.
3. **Reuse existing media storage** (`media.storage.SmartMediaCloudinaryStorage`) for `WorkItemAttachment` instead of creating a new storage system.
```

### 5.3 Frontend: Unified Work Management Module

```
/src/modules/work-management/
├── context/
│   ├── WorkManagementContext.jsx      # Global state (workspace, project, filters)
│   └── ProjectViewContext.jsx         # Per-project view state
├── pages/
│   ├── WorkspaceList.jsx              # Dashboard of all workspaces
│   ├── ProjectDashboard.jsx           # Per-project overview
│   ├── BoardView.jsx                  # Kanban/Scrum board (DRAGGABLE)
│   ├── BacklogView.jsx                # Prioritized backlog
│   ├── SprintPlanning.jsx             # Sprint planning board
│   ├── TimelineView.jsx               # Gantt/roadmap (Epics + dependencies)
│   ├── PipelineView.jsx               # Sales pipeline (reuses BoardView with sales-style)
│   ├── TicketQueue.jsx                # Support queue with SLA indicators
│   ├── CalendarView.jsx               # Sprint/cycle calendar
│   ├── DashboardMyWork.jsx            # Personal dashboard
│   └── DashboardExecutive.jsx         # Cross-department executive view
├── components/
│   ├── universal/
│   │   ├── KanbanBoard.jsx            # Generalized from CRM — takes columns config
│   │   ├── KanbanCard.jsx             # Generalized from CRM — renders any WorkItem
│   │   ├── WorkItemDialog.jsx         # Create/edit any issue type
│   │   ├── WorkItemDetail.jsx         # Full detail view with comments, activity, time
│   │   ├── FilterBar.jsx              # Reusable filter controls
│   │   ├── SprintSelector.jsx         # Sprint picker dropdown
│   │   ├── StatusBadge.jsx            # Color-coded status
│   │   └── PriorityBadge.jsx          # Priority indicator
│   ├── dev-mode/
│   │   ├── SprintCard.jsx             # Sprint info widget
│   │   ├── BurndownChart.jsx          # SVG burndown (use recharts or custom SVG)
│   │   ├── VelocityChart.jsx          # Velocity trend
│   │   └── EpicRoadmap.jsx            # Epic Gantt timeline
│   ├── sales-mode/
│   │   ├── PipelineStageCard.jsx      # Sales-specific card with value/probability
│   │   ├── TargetWidget.jsx           # Attainment % widget
│   │   └── Leaderboard.jsx            # Team ranking
│   ├── ticket-mode/
│   │   ├── SLAIndicator.jsx           # SLA timer bar
│   │   ├── TicketQueue.jsx            # Queue view
│   │   └── CustomerPortal.jsx         # Self-service portal
│   └── shared/
│       ├── PermissionGuard.jsx        # Role-based visibility wrapper
│       ├── CommentThread.jsx          # Threaded comments
│       ├── ActivityLog.jsx            # Activity feed
│       ├── TimeTracker.jsx            # Inline time logging
│       └── AttachmentUpload.jsx       # File upload
├── services/
│   ├── workspaceService.js
│   ├── projectService.js
│   ├── workItemService.js
│   ├── sprintService.js
│   ├── dashboardService.js
│   └── workflowService.js
├── hooks/
│   ├── useWorkspaces.js
│   ├── useProjects.js
│   ├── useWorkItems.js
│   ├── useSprints.js
│   ├── useEpics.js
│   ├── useDashboard.js
│   └── useWebSocket.js                # NEW — real-time connection
├── utils/
│   ├── issueTypeConfig.js             # Issue type definitions per mode
│   ├── workflowPresets.js             # Default workflows by department
│   └── slaCalculator.js               # SLA timer utilities
└── WorkManagementRoutes.jsx           # Routes: /work/*
```

### 5.4 Database Migration Strategy

**Approach: Incremental, not "big bang"**

1. **Phase 0**: Create `project_management` app with core models (Workspace, Project, WorkItem, Workflow, Sprint)
2. **Phase 0.5**: Data migration — create Workspace for existing `menus.Organization`, create Projects for existing CRM Pipelines and Sales Programmes
3. **Phase 1**: Point the existing `sales_task_manager.SalesTask` at WorkItem (as a link, initially), then gradually migrate
4. **Phase 2**: CRM deals become WorkItems with `issue_type=DEAL`
5. **Phase 3**: HR tickets become WorkItems with `issue_type=TICKET`

```python
# Migration strategy pseudocode
class MigrationStrategy:
    """Don't move data — link it, then deprecate old models gradually."""
    
    # Step 1: Create WorkItem with FK to existing models
    # Step 2: Create proxy models/views that read from WorkItem
    # Step 3: Write to both old and new for one release cycle
    # Step 4: Drop old tables once all consumers migrate
```

---

## 6. Detailed Implementation Plan

### Phase 0 — Foundation (Weeks 1-2)

**Goal:** Core data models, project CRUD, basic workflow engine

| Task | Files | Dependencies |
|---|---|---|
| 0.1 Create `project_management` Django app | `project_management/apps.py`, register in settings | None |
| 0.2 Implement Workspace model | `project_management/models.py` | Organization (menus) |
| 0.3 Implement Project model + ProjectMember | `project_management/models.py` | Workspace, User, Department |
| 0.4 Implement Workflow + WorkItemStatus models | `project_management/models.py` | Project |
| 0.5 Implement WorkItem model (core fields only) | `project_management/models.py` | Project, Workflow, User |
| 0.6 Implement basic serializers | `project_management/serializers.py` | Models above |
| 0.7 Implement ViewSets + URLs | `project_management/views.py`, `urls.py` | Serializers |
| 0.8 Implement permissions (workspace/project level) | `project_management/permissions.py` | Auth |
| 0.9 Register in core/urls.py | `core/urls.py` | All above |
| 0.10 Run migrations | `makemigrations` + `migrate` | All above |
| 0.11 Create default workflow seed script | `management/commands/seed_workflows.py` | Models |

> **Validation:** Can create a workspace, create a project within it, define a workflow with statuses, and create work items that move through the workflow.

### Phase 0.5 — Frontend Foundation (Weeks 2-3, parallel with Phase 1)

| Task | Files | Dependencies |
|---|---|---|
| 0.12 Create frontend module structure | `/src/modules/work-management/` | None |
| 0.13 Implement WorkManagementContext | `context/WorkManagementContext.jsx` | None |
| 0.14 Implement API service | `services/workspaceService.js`, `services/projectService.js`, etc. | Backend APIs |
| 0.15 Implement hooks | `hooks/useWorkspaces.js`, `useProjects.js`, `useWorkItems.js` | Services |
| 0.16 Build WorkspaceList page | `pages/WorkspaceList.jsx` | Hooks |
| 0.17 Build ProjectDashboard page | `pages/ProjectDashboard.jsx` | Hooks |
| 0.18 Build KanbanBoard (generalized) | `components/universal/KanbanBoard.jsx` | DnD kit |
| 0.19 Build KanbanCard (generalized) | `components/universal/KanbanCard.jsx` | @dnd-kit |
| 0.20 Build BoardView page | `pages/BoardView.jsx` | KanbanBoard, WorkItem dialog |
| 0.21 Implement routes | `WorkManagementRoutes.jsx`, update App.jsx | All pages |

> **Validation:** Can navigate to `/work`, see/create workspaces and projects, view a Kanban board, drag cards between columns.

### Phase 1 — Core Engine + Dev Mode (Weeks 3-6)

| Task | Details |
|---|---|
| 1.1 Sprint/Cycle model | Add to `models.py` with start/end dates, goal, capacity per member |
| 1.2 Epic model + hierarchy | Self-referential FK on WorkItem for Epic → Story/Task |
| 1.3 Backlog engine | Drag-to-reorder, priority calculator, sprint planning view |
| 1.4 Story points estimation | Fibonacci options, velocity calculation |
| 1.5 Burndown engine | Compute daily remaining points, generate chart data |
| 1.6 Scrum board | Sprint-scoped version of BoardView with sprint goal header |
| 1.7 Velocity chart | Data from last N sprints |
| 1.8 Release/version tagging | Tags on WorkItem for shipped versions |
| 1.9 Migration: Link SalesTask → WorkItem | Create WorkItems from existing SalesTasks, add FK |

> **Key integration:** The `sales_task_manager` module continues to work independently. WorkItems created from SalesTasks link back via FK. New Dev Mode WorkItems are created directly.

### Phase 1.5 — Frontend Dev Mode (Weeks 5-7)

| Task | Details |
|---|---|
| 1.10 SprintPlanning page | Sprint creation + task drag-in from backlog |
| 1.11 BacklogView page | Drag-to-reorder, epic grouping, filters |
| 1.12 Gantt/Timeline view (Epics) | Timeline with dependency arrows |
| 1.13 Burndown/Velocity charts | SVG/Recharts implementation |
| 1.14 WorkItemDialog for Dev types | Epic/Story/Task/Bug forms with story points |
| 1.15 Sprint completion workflow | Auto-move incomplete items, notify |

### Phase 2 — Sales Mode Integration (Weeks 6-8)

| Task | Details |
|---|---|
| 2.1 Sales Pipeline view in Work Management | Reuse BoardView with sales-style columns |
| 2.2 Deal (WorkItem issue_type=DEAL) | Link to existing CRM models |
| 2.3 Target/quota engine integration | Read from sales_task_manager, display in work items |
| 2.4 Attainment dashboard | Reuse existing DashboardManager + DashboardExecutive |
| 2.5 Leaderboard | Team ranking from existing data |
| 2.6 Forecast rollup | Weighted pipeline value → target forecast |

> **Key principle:** Don't rebuild what works. The sales_task_manager module is production-quality. Create **views and reports** in the new module that aggregate data, but keep the source of truth in the existing models.

### Phase 2.5 — Ticketing Mode (Weeks 8-10)

| Task | Details |
|---|---|
| 2.7 SLA Policy model | Response time, resolution time, business hours, escalation rules |
| 2.8 SLA timer engine | Start on creation, pause on "Waiting on Customer", auto-escalate |
| 2.9 Ticket queue view | Sort by SLA breach time, priority, age |
| 2.10 Auto-assignment rules | Reuse assignment_engine, trigger on ticket creation |
| 2.11 Basic customer portal | View own tickets, form submission (Phase 2 MVP) |
| 2.12 CSAT survey | Post-resolution feedback form |

### Phase 3 — Cross-Cutting Features (Weeks 10-12)

| Task | Details |
|---|---|
| 3.1 Milestones (department-agnostic) | Link to WorkItems/Sprints/Targets across projects |
| 3.2 OKR/Goal tree | Company → Department → Team → Individual |
| 3.3 Executive dashboard | Cross-department view: dev velocity + sales attainment + ticket SLAs |
| 3.4 Automation rule builder | Generalize TargetAssignmentRule → trigger/condition/action UI |
| 3.5 Multi-channel notifications | In-app + email (existing), add Slack/WhatsApp |
| 3.6 Custom fields UI | Admin-configurable fields per project/issue type |
| 3.7 Global search | Postgres full-text across all work items |

### Phase 4 — Hardening & Scale (Weeks 12-14)

| Task | Details |
|---|---|
| 4.1 WebSocket real-time updates | Django Channels + Redis for live board updates |
| 4.2 Performance tuning | Index review, query optimization, pagination audit |
| 4.3 Permission refinement | Field-level visibility for sensitive data |
| 4.4 Audit log expansion | Track all WorkItem mutations |
| 4.5 Mobile responsive polish | Ensure all views work on mobile |
| 4.6 Import/export | CSV import from Jira/Asana, export to Excel |

---

## 7. Industry Best Practices Applied

### 7.1 From the Existing Codebase (Preserve These)

| Best Practice | Evidence in Codebase |
|---|---|
| UUID primary keys | All models inherit from `Main` with UUID |
| Service layer separation | `sales_task_manager/services/*.py` |
| Activity logging | `SalesTaskLog`, `ContactLog`, `AuditLog` |
| Nested API routing | `rest_framework_nested` in CRM |
| Role-based permissions | Consistent permission classes per module |
| Token-based auth with refresh | SimpleJWT with 401 intercept |
| CORS configuration | Properly configured for multi-origin deployments |
| Dark theme UI | `dark` class on `html` element |

### 7.2 From Industry Research (Add These)

| Best Practice | Source | Implementation |
|---|---|---|
| **Modular monolith** — domain-driven Django apps | TestDriven.io 2026 | Keep `project_management` as a new app, integrate with existing via FKs and services |
| **Opinionated defaults, not blank slate** — Linear's approach | Plan doc §2 (insight from 2026 comparisons) | Ship 5 default workflow presets, hide advanced config under Admin |
| **Optimistic updates with TanStack Query** — for drag-and-drop | Industry 2026 standard | Update UI instantly on card drop, rollback on API failure |
| **Server state ≠ UI state** — TanStack Query + Zustand | React ecosystem 2026 | API caching via TanStack Query, UI state via Context/Zustand |
| **DB-level multi-tenancy** — schema isolation | `django-tenants` pattern | Phase 4: introduce schema isolation for Workspaces |
| **Real-time via Django Channels + Redis** — board updates | OneUptime 2026 guide | Phase 3: WebSocket group per project |
| **Adjacency list for task hierarchy** — parent FK on WorkItem | PostgreSQL PM patterns | Self-referential `parent` FK for subtasks, FKs for epic/child_items |
| **Composite indexes** — (project, status), (assignee, status) | PostgreSQL performance | Already in SalesTask model, replicate for WorkItem |
| **Cascading targets** — Everstage/QuotaPath pattern | Plan doc §6.2 | Already in sales_task_manager, extend with Workspace → Project cascade |
| **Configurable workflows = Pipeline + Stage** | ClickUp/Monday pattern | Already in CRM, generalize to Workflow + WorkItemStatus |
| **Rule engine: When → And → Then** | Monday/ClickUp automation | Generalize TargetAssignmentRule into AutomationRule |

### 7.3 Anti-Patterns to Avoid

| Anti-Pattern | Where We Might Be Tempted | Why To Avoid |
|---|---|---|
| **Single monolith model** — everything in one table with tons of nullable columns | Keeping `SalesTask` + `CRM` as-is without generalization | Query performance degrades, hard to add new modes |
| **Separate tables per department** — sales_tasks, dev_tasks, support_tickets | Creating per-department models | Lose cross-department reporting, duplicate comment/attachment/logging code |
| **Over-configurability on day one** — exposing all workflow options immediately | Full custom fields UI + unlimited issue types | "ClickUp syndrome" — poor onboarding and adoption (see Plan doc §2) |
| **Real-time everywhere** — WebSocket for every API call | Making every list view real-time | Over-engineering. Use real-time only for boards and dashboards |
| **Building a full CRM/HCM inside PM** — scope creep | Adding contact management, full HRIS | Plan doc explicitly lists as non-goal. Integrate, don't rebuild |
| **No migration from existing data** — leaving the old modules disconnected | Letting SalesTask and CRM operate in isolation | Confusion: "Do I create a SalesTask or a WorkItem?" Must have bidirectional sync |

---

## 8. Risk Assessment & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| **Scope creep** — feature requests from every department | High | High | Follow the plan's Phase structure. Lock Phase 0/1 scope before starting |
| **Legacy module divergence** — SalesTask and WorkItem get out of sync | High | Medium | Build sync signals from day one. Write to both models during migration window |
| **Performance at scale** — 10k+ work items per project | Medium | Medium | Index strategy from Phase 0, pagination from day one, virtual scroll on frontend |
| **Permission complexity** — too many roles and scopes | Medium | Medium | Start with 5 roles (Org Admin, Project Admin, Team Lead, Member, Viewer). Add more only when needed |
| **Frontend bundle size** — adding too many pages/charts | Low | Medium | Lazy load routes. Split charts into separate chunks |
| **Low adoption** — users prefer existing spreadsheets/tools | High | Medium | Pilot with 1 team per department. Show dashboard value early. Importers from Jira/CSV |
| **Data migration issues** — losing or duplicating existing data | Critical | Low | Never modify old models during migration. Add FKs and sync signals, always maintain backward compatibility |

---

## 9. Appendix: Key Files & References

### 9.1 Existing Files to Study Before Starting

| File | Why It's Important |
|---|---|
| `bytehive_business_backend/crm/models.py` | Pipeline + Stage model — the workflow engine prototype |
| `bytehive_business_backend/crm/views.py` | Assignment strategies implementation |
| `bytehive_business_backend/sales_task_manager/models.py` | SalesTask — 85% of Universal Work Item |
| `bytehive_business_backend/sales_task_manager/views.py` | ViewSet patterns, custom actions, activity logging |
| `bytehive_business_backend/sales_task_manager/services/progress_tracker.py` | Weighted progress, critical path, dependency checker |
| `bytehive_business_backend/sales_task_manager/services/target_engine.py` | Target cascade, achievement calculation |
| `bytehive_business_backend/sales_task_manager/services/task_generator.py` | Template-based auto-generation |
| `bytehive_business_backend/sales_task_manager/services/assignment_engine.py` | Multi-strategy assignment |
| `bytehive_business_backend/sales_task_manager/permissions.py` | Permission class patterns |
| `bytehive_business_backend/authentication/models.py` | User, Department — role hierarchy foundation |
| `bytehive_business_backend/core/models.py` | Main abstract base class |
| `bytehive_business_backend/core/urls.py` | Module registration pattern |
| `bytehive_business_frontend/src/App.jsx` | Route configuration, ProtectedRoute pattern |
| `bytehive_business_frontend/src/modules/sales-task-manager/SalesTaskRoutes.jsx` | Nested route pattern with context provider |
| `bytehive_business_frontend/src/modules/sales-task-manager/context/SalesTaskContext.jsx` | State management pattern |
| `bytehive_business_frontend/src/modules/sales-task-manager/services/salesTaskService.js` | Complete API service layer pattern |
| `bytehive_business_frontend/src/modules/sales-task-manager/pages/TaskBoard.jsx` | Full Kanban board with DnD, filters, dialogs |
| `bytehive_business_frontend/src/modules/crm/components/KanbanBoard.jsx` | CRM Kanban column with droppable area |
| `bytehive_business_frontend/src/modules/crm/components/KanbanCard.jsx` | Draggable card with useSortable |
| `bytehive_business_frontend/src/modules/crm/services/crmService.js` | API service pattern with error handling |
| `bytehive_business_frontend/src/lib/api.js` | Shared axios instance with JWT interceptors |

### 9.2 New Files to Create (Priority Order)

**Backend (First Sprint):**
1. `project_management/apps.py`
2. `project_management/models.py` (Workspace, Project, ProjectMember, Workflow, WorkItemStatus, WorkItem)
3. `project_management/serializers.py`
4. `project_management/permissions.py`
5. `project_management/views.py`
6. `project_management/urls.py`
7. `project_management/management/commands/seed_workflows.py`
8. Update `core/urls.py` and `core/settings.py`

**Frontend (Second Sprint, parallel):**
1. `src/modules/work-management/context/WorkManagementContext.jsx`
2. `src/modules/work-management/services/workItemService.js`
3. `src/modules/work-management/hooks/useWorkspaces.js`
4. `src/modules/work-management/hooks/useWorkItems.js`
5. `src/modules/work-management/components/universal/KanbanBoard.jsx`
6. `src/modules/work-management/components/universal/KanbanCard.jsx`
7. `src/modules/work-management/pages/WorkspaceList.jsx`
8. `src/modules/work-management/pages/BoardView.jsx`
9. `src/modules/work-management/WorkManagementRoutes.jsx`
10. Update `src/App.jsx`

---

*End of Architectural Analysis Document — Ready for Phase 0 Implementation*
