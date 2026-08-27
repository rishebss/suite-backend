# 🎯 Sales Task Manager Module — Target-Based Execution Engine

**Version:** 1.0  
**Status:** Planning / Design Phase  
**Standard:** Enterprise ERP Best Practice + Industry Project Management Standards  
**Target:** Sales-First Execution Platform with Project Management DNA

---

## 📌 Table of Contents

1. [Executive Summary & Vision](#1-executive-summary--vision)
2. [Module Philosophy & Key Design Principles](#2-module-philosophy--key-design-principles)
3. [System Architecture Overview](#3-system-architecture-overview)
4. [Data Models — Backend Schema](#4-data-models--backend-schema)
5. [API Design — REST Endpoints](#5-api-design--rest-endpoints)
6. [Business Logic & Workflows](#6-business-logic--workflows)
7. [Frontend Architecture & UI/UX Blueprint](#7-frontend-architecture--uiux-blueprint)
8. [Target Assignment Engine & Strategies](#8-target-assignment-engine--strategies)
9. [Task Execution & Project Management Patterns](#9-task-execution--project-management-patterns)
10. [Integration Points with Existing Modules](#10-integration-points-with-existing-modules)
11. [Permissions & Role-Based Access Control](#11-permissions--role-based-access-control)
12. [Reporting, Analytics & Dashboards](#12-reporting-analytics--dashboards)
13. [Industry Standards & Best Practices](#13-industry-standards--best-practices)
14. [Implementation Roadmap](#14-implementation-roadmap)
15. [Appendices](#15-appendices)

---

## 1. Executive Summary & Vision

### 1.1 What It Is

The **Sales Task Manager** module is a **target-driven execution engine** purpose-built for sales organisations. It fuses the **planning rigour of a project management tool** (tasks, milestones, dependencies, timelines) with the **performance DNA of a sales platform** (targets, quotas, commissions, pipeline stages).

This is **not** a generic task manager. It is a **sales-first execution platform** where:

- **Sales Targets** drive **Task Generation**
- **Tasks** have **Deal Context** (linked to CRM deals, contacts, pipelines)
- **Progress** is measured in **Revenue Impact** (₹ values), not just completion %
- **Managers** get **Programme Management** views (Gantt, timelines, resource load)
- **Reps** get a **Personal Mission Control** — everything they need to hit their number

### 1.2 The Core Problem

| Problem | Current State | Solution |
|---|---|---|
| Targets are static spreadsheets | No dynamic task breakdown | Targets auto-cascade into actionable tasks |
| Activities are disconnected from targets | Reps do busywork, not target-driving work | Every task links back to a target & deal |
| Managers lack visibility | "Who is working on what for which target?" | Programme-level dashboard with Gantt/resource views |
| Task assignment is manual | No intelligent routing | Smart assignment by workload, skillset, deal stage |
| Progress is binary (done/not done) | No partial credit, no revenue weighting | Tasks weighted by revenue impact, % completion tracked |

### 1.3 Design Philosophy

This module is built on three pillars:

1. **Sales-First DNA** — Every feature answers the question: *"Does this help close deals faster and hit targets?"*
2. **Project Management Rigour** — We borrow the best patterns from Jira, Asana, MS Project: milestones, dependencies, timelines, resource levelling, sprint-style cadences.
3. **ByteHive Architectural Consistency** — All patterns (UUID PKs, Main base model, ViewSets, routers, serializers, permissions, black/dark industrial UI) strictly follow existing conventions.

### 1.4 Key User Personas

| Persona | Role | Primary Need |
|---|---|---|
| **Sales Rep (Individual Contributor)** | Staff | See daily/weekly tasks linked to their targets and deals |
| **Sales Manager** | Manager | Assign tasks, track team progress, adjust targets mid-cycle |
| **Sales Director / Head of Sales** | Admin | View programme timelines, resource allocation, forecast attainment |
| **VP Sales / CRO** | Superadmin | Dashboard of all teams, real-time pipeline + target attainment |
| **HR** | Admin | Configure target templates from PMS goals (integration) |

---

## 2. Module Philosophy & Key Design Principles

### 2.1 Design Principles

| # | Principle | Rationale |
|---|---|---|
| 1 | **Targets Drive Everything** | No task exists without a target root cause. Every task is traceable upstream to a quarterly/annual target. |
| 2 | **Revenue-Weighted Progress** | A ₹10L deal task gets more weight than a ₹50K deal task. Progress is measured in pipeline impact, not checkbox count. |
| 3 | **Kanban + Gantt, Not Just Kanban** | Kanban for daily execution (what's next), Gantt for planning (what's coming, what depends on what). Both views co-exist. |
| 4 | **Intelligent Assignment** | Tasks aren't just dumped on reps. They're routed by workload balance, skillset match, deal ownership, and timezone. |
| 5 | **Audit Everything** | Every status change, assignment change, target adjustment is logged with user, timestamp, and reason — matching ByteHive's ContactLog pattern. |
| 6 | **Pipeline-Native** | Tasks live inside deal context. When you open a deal, you see its task plan. When you open a task, you see the deal. |
| 7 | **Progressive Cadence** | Annual targets → Quarterly sprints → Weekly tasks → Daily actions. Break down big numbers into small, winnable steps. |

### 2.2 What This Is NOT

- ❌ **Not a generic project management tool** (no software development workflows, no bug tracking, no CI/CD)
- ❌ **Not a standalone CRM** — it extends the existing CRM module
- ❌ **Not a replacement for the Payroll module** (incentive/commission calculation remains in HR/Payroll)
- ❌ **Not a document management system** — task attachments are lightweight references

### 2.3 Mental Model: Sales as a Portfolio of Programmes

```
┌────────────────────────────────────────────┐
│         FY 2026 ANNUAL REVENUE TARGET       │
│              ₹50Cr ARR                       │
├────────────────────────────────────────────┤
│                                             │
│  Q1 Target ($12Cr)  →  Q2 Target ($13Cr)   │
│    ├─ Jan Sprint                             │
│    ├─ Feb Sprint                             │
│    └─ Mar Sprint                             │
│                                             │
│  Q1 Programmes:                              │
│    ├─ Enterprise Expansion (6 deals, 4Cr)   │
│    ├─ SMB Acquisition (20 deals, 3Cr)        │
│    ├─ Renewal Campaign (15 deals, 3.5Cr)    │
│    └─ New Market Entry (5 deals, 1.5Cr)      │
│                                             │
│  Each Programme has:                          │
│    ├─ Milestones (target dates)              │
│    ├─ Tasks (assigned to reps)              │
│    ├─ Dependencies (task A → task B)        │
│    ├─ Resource Allocation (who, how much %) │
│    └─ Progress Tracking (₹ weighted)        │
└────────────────────────────────────────────┘
```

---

## 3. System Architecture Overview

### 3.1 Module Location & Structure

```
bytehive_business_backend/
├── sales_task_manager/           # NEW Django App
│   ├── models.py                 # All data models
│   ├── views.py                  # ViewSets for all models
│   ├── serializers.py            # API serializers
│   ├── urls.py                   # Router-based URL patterns
│   ├── permissions.py            # Role-based access
│   ├── admin.py                  # Django admin config
│   ├── apps.py                   # App configuration
│   ├── signals.py                # Auto-create tasks on deal/target events
│   ├── services/
│   │   ├── target_engine.py      # Target calculation & cascade logic
│   │   ├── task_generator.py     # Auto-generate tasks from targets
│   │   ├── assignment_engine.py  # Smart task assignment strategies
│   │   └── progress_tracker.py   # Weighted progress calculation
│   └── migrations/
│       └── 0001_initial.py
│
├── core/
│   ├── urls.py                   # Add: path('api/sales/', include('sales_task_manager.urls'))
│   └── settings.py               # Add 'sales_task_manager' to INSTALLED_APPS
│
└── crm/                          # Extended (not modified)
    └── models.py                 # No changes needed — CRM model already has all we need
```

### 3.2 Technology Stack Alignment

| Component | Standard | Notes |
|---|---|---|
| Framework | Django 6.0 + DRF | Matching existing setup |
| API Auth | JWT (SimpleJWT) + Session | Matching existing setup |
| Base Model | `Main` (UUID PK, created_at, updated_at) | From `core.models` |
| Permissions | Custom `permissions.py` per module | Matching HR module pattern |
| Serializers | Flat + Nested pattern | Matching CRM serializer pattern |
| Database | PostgreSQL (Neon) | Matching existing setup |
| Frontend | React + Vite + TailwindCSS | Matching existing setup |
| UI Design | "Industrial Instrument" dark theme | Matching DESIGN ARCHITECTURE.md |
| Icons | Lucide | Matching existing icon mapper |
| HTTP Client | `axios` with token interceptors | Matching `lib/api.js` |

### 3.3 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React/Vite)                          │
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐   │
│  │ Target Dashboard │  │ Task Board       │  │ Programme Gantt    │   │
│  │ (Rep/Manager)    │  │ (Kanban + Sprint)│  │ (Timeline View)    │   │
│  └────────┬─────────┘  └────────┬─────────┘  └─────────┬──────────┘   │
│           │                     │                        │             │
│           └─────────────────────┼────────────────────────┘             │
│                                 │                                      │
│                    ┌────────────┴────────────┐                         │
│                    │  API Layer (axios/JWT)   │                         │
│                    └────────────┬────────────┘                         │
└─────────────────────────────────┼───────────────────────────────────────┘
                                  │
┌─────────────────────────────────┼───────────────────────────────────────┐
│                    BACKEND (Django/DRF)                                │
│                                 │                                      │
│  ┌──────────────────────────────┴──────────────────────────────┐      │
│  │                   SALES TASK MANAGER APP                     │      │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐    │      │
│  │  │ Target Mgt │  │ Programme  │  │ Task Execution     │    │      │
│  │  │ - Cycles   │  │ Management │  │ - Daily Tasks      │    │      │
│  │  │ - Targets  │  │ - Programmes│ │ - Task Dependencies │    │      │
│  │  │ - Quotas   │  │ - Milestones│ │ - Time Tracking    │    │      │
│  │  └─────┬──────┘  └──────┬─────┘  └────────┬───────────┘    │      │
│  │        │                │                  │                │      │
│  │        └────────────────┼──────────────────┘                │      │
│  │                         │                                   │      │
│  │  ┌──────────────────────┴──────────────────────┐           │      │
│  │  │         Assignment Engine                   │           │      │
│  │  │   (round_robin, least_loaded, skillset,     │           │      │
│  │  │    deal_owner, manual)                      │           │      │
│  │  └──────────────────────┬──────────────────────┘           │      │
│  │                         │                                   │      │
│  └─────────────────────────┼───────────────────────────────────┘      │
│                            │                                          │
│  ┌─────────────────────────┴───────────────────────────────────┐      │
│  │              INTEGRATION LAYER                              │      │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │      │
│  │  │ CRM      │  │ Contacts │  │ HR       │  │ Invoices │   │      │
│  │  │ (Deals)  │  │ (People) │  │ (Emp,Dept)│  │ (Revenue)│   │      │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │      │
│  └────────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Data Models — Backend Schema

### 4.1 Model Relationship Diagram

```
TargetCycle (Annual/Half/Quarterly)
    ├── SalesTarget (per rep/team per period)
    │     ├── TargetLineItem (deal-level breakdown: "Close Deal X by date")
    │     └── TargetTaskCategory (task type: calls, meetings, proposals)
    │
    ├── SalesProgramme (programme-level initiative)
    │     ├── ProgrammeMilestone (key dates, revenue gates)
    │     ├── SalesTask (individual tasks)
    │     │     ├── TaskDependency (task A depends on task B)
    │     │     ├── TaskTimeLog (time spent on task)
    │     │     └── TaskAttachment (files, notes)
    │     └── ProgrammeResourceAllocation (who % allocated)
    │
    └── TargetAssignmentRule (how tasks auto-generate)
```

### 4.2 Core Models (in `models.py`)

#### 4.2.1 `TargetCycle` — Target Period Definition

```python
class TargetCycle(Main):
    """Defines a target period — Annual, Half-Yearly, or Quarterly"""
    name = models.CharField(max_length=100)  # "FY 2026-27", "Q1 FY26"
    code = models.CharField(max_length=20, unique=True, db_index=True)  # "FY2026", "Q1FY26"

    CYCLE_TYPE_CHOICES = (
        ('ANNUAL', 'Annual'),
        ('HALF_YEARLY', 'Half-Yearly'),
        ('QUARTERLY', 'Quarterly'),
        ('MONTHLY', 'Monthly'),
    )
    cycle_type = models.CharField(max_length=20, choices=CYCLE_TYPE_CHOICES)

    start_date = models.DateField()
    end_date = models.DateField()

    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('ACTIVE', 'Active'),
        ('CLOSED', 'Closed'),
        ('ARCHIVED', 'Archived'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')

    # Total revenue target for this cycle
    total_revenue_target = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Configuration
    task_auto_generation_enabled = models.BooleanField(default=True)
    sprint_duration_days = models.IntegerField(default=14)  # Sprint length in days

    # Optional link to HR AppraisalCycle
    appraisal_cycle = models.ForeignKey(
        'hr.AppraisalCycle', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='target_cycles'
    )

    class Meta:
        ordering = ['-start_date']
        verbose_name = 'Target Cycle'
        verbose_name_plural = 'Target Cycles'

    def __str__(self):
        return f"{self.name} ({self.get_cycle_type_display()})"
```

#### 4.2.2 `SalesTarget` — Per-Rep/Team Target

```python
class SalesTarget(Main):
    """Individual or team-level target for a specific cycle"""
    cycle = models.ForeignKey(TargetCycle, on_delete=models.CASCADE, related_name='sales_targets')

    ASSIGNEE_TYPE_CHOICES = (
        ('USER', 'Individual'),
        ('TEAM', 'Team'),
        ('DEPARTMENT', 'Department'),
    )
    assignee_type = models.CharField(max_length=20, choices=ASSIGNEE_TYPE_CHOICES, default='USER')

    # Polymorphic assignee
    assigned_user = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sales_targets'
    )
    assigned_department = models.ForeignKey(
        'authentication.Department', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sales_targets'
    )

    # Target value
    target_amount = models.DecimalField(max_digits=15, decimal_places=2)
    achieved_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    weighted_progress_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    STATUS_CHOICES = (
        ('NOT_STARTED', 'Not Started'),
        ('IN_PROGRESS', 'In Progress'),
        ('ACHIEVED', 'Achieved'),
        ('EXCEEDED', 'Exceeded'),
        ('MISSED', 'Missed'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NOT_STARTED')

    # Target breakdown
    new_business_target = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    renewal_target = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    upsell_target = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Approval
    assigned_by = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_targets'
    )
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ('cycle', 'assignee_type', 'assigned_user', 'assigned_department')
        verbose_name = 'Sales Target'
        verbose_name_plural = 'Sales Targets'
        indexes = [
            models.Index(fields=['cycle', 'assigned_user']),
            models.Index(fields=['cycle', 'assigned_department']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        assignee = self.assigned_user or self.assigned_department
        return f"{self.cycle.name} → {assignee}: ₹{self.target_amount}"
```

#### 4.2.3 `TargetLineItem` — Deal-Level Target Breakdown

```python
class TargetLineItem(Main):
    """A specific revenue expectation — linked to a CRM deal or a new opportunity"""
    sales_target = models.ForeignKey(SalesTarget, on_delete=models.CASCADE, related_name='line_items')

    # Link to CRM deal (optional — can be a pipeline target before deal exists)
    crm_deal = models.ForeignKey(
        'crm.CRM', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='target_line_items'
    )

    description = models.CharField(max_length=255)  # "Close Acme Corp Expansion"
    expected_amount = models.DecimalField(max_digits=15, decimal_places=2)
    expected_close_date = models.DateField()

    LINE_ITEM_TYPE_CHOICES = (
        ('NEW_BUSINESS', 'New Business'),
        ('RENEWAL', 'Renewal'),
        ('UPSELL', 'Upsell'),
        ('EXPANSION', 'Expansion'),
    )
    line_item_type = models.CharField(max_length=20, choices=LINE_ITEM_TYPE_CHOICES, default='NEW_BUSINESS')

    PROBABILITY_CHOICES = (
        ('LOW', 'Low (<25%)'),
        ('MEDIUM', 'Medium (25-50%)'),
        ('HIGH', 'High (50-75%)'),
        ('COMMITTED', 'Committed (>75%)'),
    )
    probability = models.CharField(max_length=20, choices=PROBABILITY_CHOICES, default='MEDIUM')

    is_attained = models.BooleanField(default=False)
    attained_date = models.DateField(null=True, blank=True)
    actual_revenue = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name = 'Target Line Item'
        verbose_name_plural = 'Target Line Items'
        ordering = ['expected_close_date']

    def __str__(self):
        return f"{self.description} — ₹{self.expected_amount}"
```

#### 4.2.4 `SalesProgramme` — Programme Management

```python
class SalesProgramme(Main):
    """A focused sales initiative — the 'project' in our sales+PM hybrid"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Link to target
    target_cycle = models.ForeignKey(
        TargetCycle, on_delete=models.CASCADE, related_name='programmes'
    )
    sales_target = models.ForeignKey(
        SalesTarget, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='programmes'
    )

    # Programme timeline
    start_date = models.DateField()
    end_date = models.DateField()

    PRIORITY_CHOICES = (
        ('CRITICAL', 'Critical'),
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low'),
    )
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM')

    STATUS_CHOICES = (
        ('PLANNING', 'Planning'),
        ('ACTIVE', 'Active'),
        ('ON_HOLD', 'On Hold'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PLANNING')

    # Revenue
    target_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    actual_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Team (many-to-many — who is working on this programme)
    team_members = models.ManyToManyField(
        'authentication.User', blank=True, related_name='sales_programmes'
    )

    # Programme manager
    programme_manager = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='managed_programmes'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Sales Programme'
        verbose_name_plural = 'Sales Programmes'
        indexes = [
            models.Index(fields=['target_cycle', 'status']),
            models.Index(fields=['priority', 'status']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
```

#### 4.2.5 `ProgrammeMilestone` — Key Milestones

```python
class ProgrammeMilestone(Main):
    """Significant events within a programme — borrowed from project management"""
    programme = models.ForeignKey(
        SalesProgramme, on_delete=models.CASCADE, related_name='milestones'
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    target_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)

    MILESTONE_TYPE_CHOICES = (
        ('REVENUE_GATE', 'Revenue Gate'),           # "Reach ₹50L in pipeline"
        ('CLOSE_DATE', 'Close Date'),                # "Close Acme Corp deal"
        ('ACTIVITY_TARGET', 'Activity Target'),      # "Complete 50 demos"
        ('TEAM_BUILDING', 'Team Building'),          # "Hire 2 SDRs"
        ('PRODUCT_LAUNCH', 'Product Launch'),        # "Launch new pricing"
        ('TRAINING', 'Training'),                    # "Complete product training"
    )
    milestone_type = models.CharField(max_length=20, choices=MILESTONE_TYPE_CHOICES)

    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('ACHIEVED', 'Achieved'),
        ('MISSED', 'Missed'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    # Revenue milestone
    revenue_impact = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    class Meta:
        ordering = ['target_date']
        verbose_name = 'Programme Milestone'
        verbose_name_plural = 'Programme Milestones'

    def __str__(self):
        return f"{self.programme.name} → {self.name} ({self.target_date})"
```

#### 4.2.6 `SalesTask` — The Core Task Model

```python
class SalesTask(Main):
    """The atomic unit of work — deeply connected to CRM deals and targets."""
    programme = models.ForeignKey(
        SalesProgramme, on_delete=models.CASCADE, related_name='tasks'
    )
    sales_target = models.ForeignKey(
        SalesTarget, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='tasks'
    )

    # Task details
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    TASK_TYPE_CHOICES = (
        ('CALL', 'Call'),
        ('MEETING', 'Meeting'),
        ('DEMO', 'Demo'),
        ('PROPOSAL', 'Proposal'),
        ('QUOTE', 'Quote'),
        ('FOLLOW_UP', 'Follow Up'),
        ('EMAIL', 'Email'),
        ('RESEARCH', 'Research'),
        ('NEGOTIATION', 'Negotiation'),
        ('CONTRACT_REVIEW', 'Contract Review'),
        ('INTERNAL_REVIEW', 'Internal Review'),
        ('CLOSING', 'Closing'),
        ('OTHER', 'Other'),
    )
    task_type = models.CharField(max_length=30, choices=TASK_TYPE_CHOICES, default='OTHER')

    PRIORITY_CHOICES = (
        ('CRITICAL', 'Critical'),
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low'),
    )
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM')

    STATUS_CHOICES = (
        ('BACKLOG', 'Backlog'),
        ('TODO', 'To Do'),
        ('IN_PROGRESS', 'In Progress'),
        ('IN_REVIEW', 'In Review'),
        ('DONE', 'Done'),
        ('BLOCKED', 'Blocked'),
        ('CANCELLED', 'Cancelled'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='TODO')

    # Assignment
    assigned_to = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sales_tasks'
    )
    assigned_by = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_tasks'
    )

    # Timeline
    due_date = models.DateField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    estimated_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    actual_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    # CRM Links (optional — task may or may not be tied to a deal)
    crm_deal = models.ForeignKey(
        'crm.CRM', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sales_tasks'
    )
    contact = models.ForeignKey(
        'contacts.Contact', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sales_tasks'
    )

    # Revenue impact of completing this task
    revenue_impact = models.DecimalField(max_digits=15, decimal_places=2, default=0,
        help_text="Estimated revenue impact if this task is completed")

    # Weight for progress calculation
    weight_pct = models.DecimalField(max_digits=5, decimal_places=2, default=1.00,
        help_text="Relative weight for progress calculation (0-100%)")

    # Ordering within sprint/programme
    order = models.PositiveIntegerField(default=0)

    # Auto-generated flag
    is_auto_generated = models.BooleanField(default=False,
        help_text="True if created automatically by target engine")

    class Meta:
        ordering = ['order', 'due_date', 'created_at']
        verbose_name = 'Sales Task'
        verbose_name_plural = 'Sales Tasks'
        indexes = [
            models.Index(fields=['programme', 'status']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['crm_deal']),
            models.Index(fields=['due_date']),
            models.Index(fields=['sales_target']),
        ]

    def __str__(self):
        return f"{self.title} ({self.assigned_to or 'Unassigned'})"
```

#### 4.2.7 `TaskDependency` — Dependency Graph

```python
class TaskDependency(Main):
    """Track dependencies between tasks — borrowed from PM tools"""
    DEPENDENCY_TYPE_CHOICES = (
        ('FINISH_TO_START', 'Finish → Start'),  # Task B cannot start until Task A finishes
        ('START_TO_START', 'Start → Start'),    # Task B cannot start until Task A starts
        ('FINISH_TO_FINISH', 'Finish → Finish'), # Task B cannot finish until Task A finishes
        ('START_TO_FINISH', 'Start → Finish'),   # Task B cannot finish until Task A starts
    )

    task = models.ForeignKey(
        SalesTask, on_delete=models.CASCADE, related_name='dependencies'
    )
    depends_on = models.ForeignKey(
        SalesTask, on_delete=models.CASCADE, related_name='dependent_tasks'
    )
    dependency_type = models.CharField(
        max_length=20, choices=DEPENDENCY_TYPE_CHOICES, default='FINISH_TO_START'
    )

    class Meta:
        unique_together = ('task', 'depends_on')
        verbose_name = 'Task Dependency'
        verbose_name_plural = 'Task Dependencies'

    def __str__(self):
        return f"{self.task.title} depends on {self.depends_on.title}"
```

#### 4.2.8 `TaskTimeLog` — Time Tracking

```python
class TaskTimeLog(Main):
    """Time spent on a task — for effort tracking and load analysis"""
    task = models.ForeignKey(SalesTask, on_delete=models.CASCADE, related_name='time_logs')
    user = models.ForeignKey('authentication.User', on_delete=models.CASCADE)
    date = models.DateField()
    hours = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['-date']
        verbose_name = 'Task Time Log'
        verbose_name_plural = 'Task Time Logs'

    def __str__(self):
        return f"{self.user.get_full_name()} — {self.task.title}: {self.hours}h"
```

#### 4.2.9 `ProgrammeResourceAllocation` — Resource Management

```python
class ProgrammeResourceAllocation(Main):
    """Track how much of a person's time is allocated to each programme"""
    programme = models.ForeignKey(
        SalesProgramme, on_delete=models.CASCADE, related_name='resource_allocations'
    )
    user = models.ForeignKey('authentication.User', on_delete=models.CASCADE)
    allocation_pct = models.DecimalField(
        max_digits=5, decimal_places=2,
        help_text="Percentage of user's time allocated (e.g., 50.00 = 50%)"
    )
    start_date = models.DateField()
    end_date = models.DateField()

    ROLE_CHOICES = (
        ('LEAD', 'Programme Lead'),
        ('SDR', 'SDR'),
        ('AE', 'Account Executive'),
        ('SE', 'Solutions Engineer'),
        ('CSM', 'Customer Success'),
        ('MANAGER', 'Manager'),
        ('SUPPORT', 'Support'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='AE')

    class Meta:
        unique_together = ('programme', 'user', 'start_date')
        verbose_name = 'Resource Allocation'
        verbose_name_plural = 'Resource Allocations'

    def __str__(self):
        return f"{self.user.get_full_name()} — {self.programme.name}: {self.allocation_pct}%"
```

#### 4.2.10 `TargetAssignmentRule` — Task Auto-Generation Rules

```python
class TargetAssignmentRule(Main):
    """Rules for auto-generating tasks when targets are set or deals move stages"""
    sales_target = models.ForeignKey(
        SalesTarget, on_delete=models.CASCADE, related_name='assignment_rules'
    )

    # Trigger
    TRIGGER_CHOICES = (
        ('TARGET_CREATED', 'On Target Creation'),
        ('DEAL_STAGE_CHANGE', 'On Deal Stage Change'),
        ('DEAL_CREATED', 'On Deal Created'),
        ('WEEKLY', 'Weekly Recurring'),
        ('MONTHLY', 'Monthly Recurring'),
        ('MANUAL', 'Manual Only'),
    )
    trigger = models.CharField(max_length=30, choices=TRIGGER_CHOICES)

    # What tasks to generate
    task_type = models.CharField(max_length=30, choices=SalesTask.TASK_TYPE_CHOICES)
    task_title_template = models.CharField(
        max_length=255,
        help_text="Use {{deal_name}}, {{contact_name}}, {{target_amount}} as variables"
    )
    task_description_template = models.TextField(blank=True)
    due_date_offset_days = models.IntegerField(default=7,
        help_text="Days from trigger date to set as due date")
    priority = models.CharField(max_length=20, choices=SalesTask.PRIORITY_CHOICES, default='MEDIUM')

    # Assignment
    ASSIGNMENT_STRATEGY_CHOICES = (
        ('DEAL_OWNER', 'Deal Owner'),
        ('TARGET_OWNER', 'Target Owner'),
        ('LEAST_LOADED', 'Least Loaded'),
        ('ROUND_ROBIN', 'Round Robin'),
        ('MANAGER', 'Manager'),
    )
    assignment_strategy = models.CharField(
        max_length=20, choices=ASSIGNMENT_STRATEGY_CHOICES, default='TARGET_OWNER'
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Assignment Rule'
        verbose_name_plural = 'Assignment Rules'

    def __str__(self):
        return f"{self.sales_target} → {self.get_task_type_display()} ({self.get_trigger_display()})"
```

#### 4.2.11 `TaskAttachment` — File/Note Attachments

```python
class TaskAttachment(Main):
    """Files, notes, or links attached to a task"""
    task = models.ForeignKey(SalesTask, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='task_attachments/%Y/%m/', null=True, blank=True)
    file_name = models.CharField(max_length=255)
    file_size = models.IntegerField(default=0)
    note = models.TextField(blank=True)
    url = models.URLField(blank=True)
    uploaded_by = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Task Attachment'
        verbose_name_plural = 'Task Attachments'

    def __str__(self):
        return f"{self.task.title} — {self.file_name}"
```

#### 4.2.12 `SalesTaskLog` — Audit Trail (Matching ContactLog Pattern)

```python
class SalesTaskLog(Main):
    """Activity log for all task and target changes — matches ByteHive's ContactLog pattern"""
    task = models.ForeignKey(
        SalesTask, on_delete=models.CASCADE, null=True, blank=True,
        related_name='activity_logs'
    )
    sales_target = models.ForeignKey(
        SalesTarget, on_delete=models.CASCADE, null=True, blank=True,
        related_name='activity_logs'
    )
    user = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, null=True, blank=True
    )

    ACTIVITY_TYPE_CHOICES = (
        ('TASK_CREATED', 'Task Created'),
        ('TASK_ASSIGNED', 'Task Assigned'),
        ('TASK_REASSIGNED', 'Task Reassigned'),
        ('TASK_STATUS_CHANGED', 'Task Status Changed'),
        ('TASK_DUE_DATE_CHANGED', 'Task Due Date Changed'),
        ('TASK_PRIORITY_CHANGED', 'Task Priority Changed'),
        ('TARGET_CREATED', 'Target Created'),
        ('TARGET_UPDATED', 'Target Updated'),
        ('TARGET_ACHIEVED', 'Target Achieved'),
        ('MILESTONE_ACHIEVED', 'Milestone Achieved'),
        ('PROGRAMME_STATUS_CHANGED', 'Programme Status Changed'),
        ('COMMENT_ADDED', 'Comment Added'),
    )
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPE_CHOICES)
    description = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Task Activity Log'
        verbose_name_plural = 'Task Activity Logs'
        indexes = [
            models.Index(fields=['task', 'created_at']),
            models.Index(fields=['sales_target', 'created_at']),
        ]

    def __str__(self):
        return f"{self.get_activity_type_display()} — {self.description[:50]}"
```

### 4.3 Model Compliance with Existing Patterns

| Pattern | Existing Standard | This Module |
|---|---|---|
| Primary Key | UUID (`core.models.Main`) | ✅ All models inherit `Main` |
| Timestamps | `created_at`, `updated_at` auto | ✅ Inherited |
| Soft Delete | `is_active` boolean flag | ✅ On relevant models |
| Choices Pattern | Tuple constants in model file | ✅ Matching HR module style |
| Indexes | Named composite indexes | ✅ On frequently filtered fields |
| String Representation | `__str__` with meaningful display | ✅ Informative, debug-friendly |
| Foreign Key Naming | `related_name` explicit | ✅ All FKs have related_name |
| Audit Logging | `ContactLog` pattern | ✅ `SalesTaskLog` model |
| Unique Constraints | Composite where needed | ✅ On target/assignee combos |

---

## 5. API Design — REST Endpoints

### 5.1 Base URL Structure

```
Base: /api/sales/
```

All endpoints follow the router-based `ViewSet` pattern matching existing modules (CRM, HR, etc.).

### 5.2 Endpoint Map

#### 5.2.1 Target Cycle Management

| Method | Endpoint | Description | Permissions |
|---|---|---|---|
| GET | `/api/sales/target-cycles/` | List all target cycles | IsAuthenticated |
| POST | `/api/sales/target-cycles/` | Create new cycle | Admin/Superadmin |
| GET | `/api/sales/target-cycles/{id}/` | Cycle details with targets | IsAuthenticated |
| PUT/PATCH | `/api/sales/target-cycles/{id}/` | Update cycle | Admin/Superadmin |
| DELETE | `/api/sales/target-cycles/{id}/` | Soft-delete cycle | Superadmin |
| POST | `/api/sales/target-cycles/{id}/activate/` | Activate cycle → auto-generate tasks | Admin |
| POST | `/api/sales/target-cycles/{id}/close/` | Close cycle, finalise attainment | Admin |
| GET | `/api/sales/target-cycles/{id}/summary/` | Dashboard summary data | IsAuthenticated |

#### 5.2.2 Sales Targets

| Method | Endpoint | Description | Permissions |
|---|---|---|---|
| GET | `/api/sales/targets/` | List targets (filterable) | IsAuthenticated |
| POST | `/api/sales/targets/` | Create new target | Manager+ |
| GET | `/api/sales/targets/{id}/` | Target details with line items | IsAuthenticated |
| PUT/PATCH | `/api/sales/targets/{id}/` | Update target | Manager+ |
| DELETE | `/api/sales/targets/{id}/` | Delete target | Admin+ |
| POST | `/api/sales/targets/{id}/assign/` | Assign target to user/team | Manager+ |
| POST | `/api/sales/targets/{id}/generate-tasks/` | Auto-generate tasks from target | Manager+ |
| GET | `/api/sales/targets/{id}/progress/` | Weighted progress calculation | IsAuthenticated |
| POST | `/api/sales/targets/bulk-create/` | Bulk create targets (CSV/JSON) | Admin+ |

#### 5.2.3 Target Line Items

| Method | Endpoint | Description | Permissions |
|---|---|---|---|
| GET | `/api/sales/target-line-items/` | List line items (filter: target, deal) | IsAuthenticated |
| POST | `/api/sales/target-line-items/` | Create line item | Manager+ |
| PATCH | `/api/sales/target-line-items/{id}/` | Update (attain, adjust amount) | Manager+ |
| DELETE | `/api/sales/target-line-items/{id}/` | Delete | Admin+ |

#### 5.2.4 Sales Programmes

| Method | Endpoint | Description | Permissions |
|---|---|---|---|
| GET | `/api/sales/programmes/` | List programmes (filterable) | IsAuthenticated |
| POST | `/api/sales/programmes/` | Create programme | Manager+ |
| GET | `/api/sales/programmes/{id}/` | Full programme detail | IsAuthenticated |
| PUT/PATCH | `/api/sales/programmes/{id}/` | Update programme | Manager+ |
| DELETE | `/api/sales/programmes/{id}/` | Delete programme | Admin+ |
| POST | `/api/sales/programmes/{id}/add-member/` | Add team member | Manager+ |
| POST | `/api/sales/programmes/{id}/remove-member/` | Remove team member | Manager+ |
| GET | `/api/sales/programmes/{id}/gantt/` | Gantt chart data | IsAuthenticated |
| GET | `/api/sales/programmes/{id}/resource-load/` | Resource allocation view | Manager+ |

#### 5.2.5 Programme Milestones

| Method | Endpoint | Description | Permissions |
|---|---|---|---|
| GET | `/api/sales/milestones/` | List milestones | IsAuthenticated |
| POST | `/api/sales/milestones/` | Create milestone | Manager+ |
| PATCH | `/api/sales/milestones/{id}/` | Update milestone | Manager+ |
| POST | `/api/sales/milestones/{id}/achieve/` | Mark milestone achieved | Manager+ |

#### 5.2.6 Sales Tasks

| Method | Endpoint | Description | Permissions |
|---|---|---|---|
| GET | `/api/sales/tasks/` | List tasks (filterable — heavy filtering) | IsAuthenticated |
| POST | `/api/sales/tasks/` | Create task | IsAuthenticated |
| GET | `/api/sales/tasks/{id}/` | Task detail with deps, logs, attachments | IsAuthenticated |
| PUT/PATCH | `/api/sales/tasks/{id}/` | Update task | IsAuthenticated |
| DELETE | `/api/sales/tasks/{id}/` | Delete task | Manager+ |
| POST | `/api/sales/tasks/{id}/assign/` | Assign/reassign task | Manager+ |
| POST | `/api/sales/tasks/{id}/status/` | Update status (with audit log) | IsAuthenticated |
| POST | `/api/sales/tasks/{id}/start/` | Start task (set started_at) | IsAuthenticated |
| POST | `/api/sales/tasks/{id}/complete/` | Complete task (set completed_at) | IsAuthenticated |
| POST | `/api/sales/tasks/{id}/block/` | Mark as blocked (with reason) | IsAuthenticated |
| POST | `/api/sales/tasks/bulk-reorder/` | Reorder tasks (drag & drop) | Manager+ |
| POST | `/api/sales/tasks/bulk-update-status/` | Bulk status change | Manager+ |
| GET | `/api/sales/tasks/my-tasks/` | Current user's active tasks | IsAuthenticated |
| GET | `/api/sales/tasks/by-deal/{deal_id}/` | All tasks for a deal | IsAuthenticated |

#### 5.2.7 Task Dependencies

| Method | Endpoint | Description | Permissions |
|---|---|---|---|
| GET | `/api/sales/task-dependencies/` | List dependencies | IsAuthenticated |
| POST | `/api/sales/task-dependencies/` | Create dependency | Manager+ |
| DELETE | `/api/sales/task-dependencies/{id}/` | Remove dependency | Manager+ |

#### 5.2.8 Time Tracking

| Method | Endpoint | Description | Permissions |
|---|---|---|---|
| GET | `/api/sales/time-logs/` | List time logs | IsAuthenticated |
| POST | `/api/sales/time-logs/` | Log time | IsAuthenticated |
| PATCH | `/api/sales/time-logs/{id}/` | Update time log | Owner/Manager+ |
| DELETE | `/api/sales/time-logs/{id}/` | Delete time log | Owner/Admin+ |
| GET | `/api/sales/time-logs/summary/` | Time summary per user/programme | Manager+ |

#### 5.2.9 Resource Allocations

| Method | Endpoint | Description | Permissions |
|---|---|---|---|
| GET | `/api/sales/resource-allocations/` | List allocations | Manager+ |
| POST | `/api/sales/resource-allocations/` | Create allocation | Manager+ |
| PATCH | `/api/sales/resource-allocations/{id}/` | Update allocation | Manager+ |
| DELETE | `/api/sales/resource-allocations/{id}/` | Delete allocation | Admin+ |

#### 5.2.10 Assignment Rules

| Method | Endpoint | Description | Permissions |
|---|---|---|---|
| GET | `/api/sales/assignment-rules/` | List rules | Admin+ |
| POST | `/api/sales/assignment-rules/` | Create rule | Admin+ |
| PATCH | `/api/sales/assignment-rules/{id}/` | Update rule | Admin+ |
| DELETE | `/api/sales/assignment-rules/{id}/` | Delete rule | Admin+ |

#### 5.2.11 Task Attachments

| Method | Endpoint | Description | Permissions |
|---|---|---|---|
| GET | `/api/sales/task-attachments/` | List attachments | IsAuthenticated |
| POST | `/api/sales/task-attachments/` | Upload attachment | IsAuthenticated |
| DELETE | `/api/sales/task-attachments/{id}/` | Delete attachment | Owner/Admin+ |

#### 5.2.12 Activity Logs

| Method | Endpoint | Description | Permissions |
|---|---|---|---|
| GET | `/api/sales/activity-logs/` | List logs (filter: task, target, user) | IsAuthenticated |

#### 5.2.13 Dashboard & Analytics

| Method | Endpoint | Description | Permissions |
|---|---|---|---|
| GET | `/api/sales/dashboard/executive/` | Executive overview (all teams) | Admin+ |
| GET | `/api/sales/dashboard/manager/` | Manager view (own team) | Manager+ |
| GET | `/api/sales/dashboard/my-target/` | Rep's personal dashboard | IsAuthenticated |

### 5.3 Response Format

All responses follow the existing ByteHive convention:

```json
{
  "success": true,
  "message": "Optional status message",
  "data": {
    // ... model data
  }
}
```

Paginated list responses:

```json
{
  "count": 150,
  "next": "http://...?page=2",
  "previous": null,
  "results": [
    // ... serialized objects
  ]
}
```

### 5.4 Filtering & Search Patterns

Following CRM and HR patterns — extensive filtering via `django-filter`:

| Endpoint | Filters |
|---|---|
| `/targets/` | `cycle`, `assigned_user`, `assigned_department`, `status`, `assignee_type` |
| `/tasks/` | `programme`, `assigned_to`, `status`, `priority`, `task_type`, `due_date__gte`, `due_date__lte`, `crm_deal`, `sales_target`, `is_auto_generated` |
| `/programmes/` | `target_cycle`, `status`, `priority`, `programme_manager`, `team_members` |

---

## 6. Business Logic & Workflows

### 6.1 Target Lifecycle

```
DRAFT → ACTIVE → CLOSED → ARCHIVED
                         ↓
                    MISSED / ACHIEVED / EXCEEDED
```

**Workflow:**

1. **Admin creates TargetCycle** (e.g., Q1 FY 2027)
2. **Manager creates SalesTargets** for each rep/team (amount, line items)
3. **Draft period**: Admin/Manager fine-tune targets, add line items, set rules
4. **Activate**: Cycle status → `ACTIVE`, auto-generates initial tasks if enabled
5. **During cycle**: Tasks are tracked, deals progress, target `achieved_amount` updates
6. **Close**: Cycle status → `CLOSED`, final attainment calculated, comparison report generated
7. **Archive**: Historical data preserved

### 6.2 Task Auto-Generation Rules

The `task_generator.py` service implements these generation triggers:

#### 6.2.1 On Target Activation

For each `SalesTarget` with active `TargetAssignmentRule`:

```
For each rule with trigger=TARGET_CREATED:
    Create N tasks based on:
    - task_type from rule
    - title from template (variable substitution)
    - due_date = activation_date + due_date_offset_days
    - assigned_to = based on assignment_strategy
    - revenue_impact = target_amount / number_of_tasks
```

#### 6.2.2 On Deal Stage Change

When a CRM deal moves to a new stage:

```
For each rule with trigger=DEAL_STAGE_CHANGE:
    Check if the deal's SalesTarget has an active rule
    Create task:
        - crm_deal = the deal
        - title: "Follow up on {{deal_name}}" (template)
        - due_date: today + offset
        - assigned_to: deal's assigned_user
```

#### 6.2.3 Weekly/Monthly Recurring

For recurring tasks:

```
For each rule with trigger=WEEKLY or MONTHLY:
    Check if a task of this type already exists for the period
    If not, create new recurring task
```

### 6.3 Weighted Progress Calculation (`progress_tracker.py`)

Progress is **not** a simple count of tasks completed. It uses a revenue-weighted model:

```
Total Progress % = Σ(weight_pct × revenue_impact × status_factor) for each task

Where:
- weight_pct: Relative importance of this task (0-100%)
- revenue_impact: ₹ value of this task
- status_factor:
    DONE = 1.0
    IN_REVIEW = 0.8
    IN_PROGRESS = 0.5
    TODO = 0.0
    BLOCKED = 0.0
    CANCELLED = 0.0

Normalised: Sum(weighted_progress) / Sum(max_possible_weighted_progress) × 100
```

#### 6.3.1 Derived Fields

- `SalesTarget.achieved_amount` = Sum of `TargetLineItem.actual_revenue` where `is_attained=True`
- `SalesTarget.weighted_progress_pct` = Weighted task completion % across all tasks in that target
- `SalesProgramme.actual_revenue` = Sum of linked deal values that reached "Won" stage

### 6.4 Dependency Chain Resolution

The `progress_tracker.py` also handles dependency-aware scheduling:

```
Task D → Task C → Task B → Task A
(F→S)    (F→S)    (F→S)

If Task B is DONE, Task C becomes available (TODO → can be started)
If Task C is DONE, Task D becomes available

Blocked detection:
- A task is BLOCKED if it has any FINISH_TO_START dependency that is not DONE
- A task is WARNING if its dependency is IN_PROGRESS but not DONE
```

### 6.5 Programme Dashboard Calculations

For each programme:

```
Programme Health Score = 
    milestone_health × 0.3 +
    task_completion × 0.3 +
    revenue_attainment × 0.4

Where:
- milestone_health: % of milestones achieved on time
- task_completion: weighted task progress (see above)
- revenue_attainment: actual_revenue / target_revenue
```

---

## 7. Frontend Architecture & UI/UX Blueprint

### 7.1 Module Structure

```
bytehive_business_frontend/src/modules/sales-task-manager/
├── pages/
│   ├── TargetCycleList.jsx          # List all cycles
│   ├── TargetCycleDetail.jsx        # Single cycle with targets
│   ├── SalesTargetDetail.jsx        # Single target with tasks + progress
│   ├── SalesProgrammeDetail.jsx     # Programme view (Gantt + Kanban)
│   ├── TaskBoard.jsx                # Kanban board for tasks
│   ├── TaskDetail.jsx               # Modal/page for task details
│   ├── DashboardExecutive.jsx       # VP/CRO dashboard
│   ├── DashboardManager.jsx         # Team-level dashboard
│   └── DashboardMyView.jsx          # Rep's personal mission control
│
├── components/
│   ├── TargetCycleForm.jsx          # Create/edit cycle
│   ├── SalesTargetForm.jsx          # Create/edit target
│   ├── TargetLineItemForm.jsx       # Add line items
│   ├── SalesProgrammeForm.jsx       # Create/edit programme
│   ├── TaskCard.jsx                 # Kanban card (matching KanbanCard.jsx)
│   ├── TaskColumn.jsx               # Kanban column (matching KanbanBoard.jsx)
│   ├── TaskDetailDialog.jsx         # Task details modal (split-screen)
│   ├── TaskCreateDialog.jsx         # Quick task creation modal
│   ├── ProgrammeGantt.jsx           # Gantt chart component
│   ├── ProgressBar.jsx              # Weighted progress bar
│   ├── ResourceLoadView.jsx         # Resource allocation matrix
│   ├── DependencyGraph.jsx          # Task dependency visualization
│   ├── TimeTrackingWidget.jsx       # Quick time log entry
│   ├── FilterBar.jsx                # Advanced filters (matching CRM pattern)
│   ├── SprintSelector.jsx           # Sprint/week selector
│   └── WeightedProgressIndicator.jsx # Circular/bar progress with ₹ weight
│
├── hooks/
│   ├── useTargetCycles.js
│   ├── useSalesTargets.js
│   ├── useSalesProgrammes.js
│   ├── useSalesTasks.js
│   └── useDashboard.js
│
├── services/
│   ├── salesTaskService.js          # All API calls
│   └── salesTaskUtils.js            # Helper functions
│
├── context/
│   └── SalesTaskContext.jsx         # Global state for tasks/targets
│
└── SalesTaskRoutes.jsx              # Route definitions
```

### 7.2 Route Map

| Route | Component | Access |
|---|---|---|
| `/sales` | Navigate to `/sales/tasks` | All |
| `/sales/targets` | `TargetCycleList` | All |
| `/sales/targets/{cycleId}` | `TargetCycleDetail` | All |
| `/sales/targets/{cycleId}/{targetId}` | `SalesTargetDetail` | All |
| `/sales/programmes/{programmeId}` | `SalesProgrammeDetail` | All |
| `/sales/tasks` | `TaskBoard` (Kanban) | All |
| `/sales/tasks/{taskId}` | `TaskDetail` | All |
| `/sales/dashboard` | `DashboardMyView` (rep) | Staff |
| `/sales/dashboard/team` | `DashboardManager` | Manager+ |
| `/sales/dashboard/executive` | `DashboardExecutive` | Admin+ |

### 7.3 UI/UX Design Principles

Every component follows the **"Industrial Instrument"** design philosophy from `DESIGN ARCHITECTURE.md`:

| Element | Implementation |
|---|---|
| Background | True Black (`#000000`) with radial point grid |
| Containers | `bg-zinc-900/30` with `border-zinc-800` |
| Dividers | `border-white/5` |
| Unified Header | Consistent `px-10 py-8` with `backdrop-blur-xl` |
| Tab Navigation | Sliding highlighter (blue-500/20) with uppercase tracking |
| Modals | `max-w-lg` for forms, `max-w-3xl` for split-screen details |
| Badges | Micro-size `text-[9px] px-2 py-0.5` with accent colors |
| Buttons | HSL semi-transparent (blue/red/zinc) per component blueprint |
| Cards | Dense, scannable `p-6` with `gap-6` grid spacing |

### 7.4 Key UI Screens (Wireframe Descriptions)

#### 7.4.1 Executive Dashboard (`DashboardExecutive.jsx`)

```
┌──────────────────────────────────────────────────────────────┐
│  HEADER: Sales Dashboard │ Q1 FY 2027 │ [Cycle Selector ▼]  │
├──────────────────────────────────────────────────────────────┤
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────┐    │
│ │₹12Cr    │ │₹8.5Cr   │ │71%      │ │ 18 Programmes   │    │
│ │Target   │ │Achieved │ │Attainmnt│ │ (4 Behind)      │    │
│ └─────────┘ └─────────┘ └─────────┘ └─────────────────┘    │
│                                                              │
│ ┌─────────────────────────┐ ┌──────────────────────────┐    │
│ │ Revenue Attainment      │ │ Programme Health         │    │
│ │ (Bar chart by month)    │ │ (Coloured donuts)        │    │
│ └─────────────────────────┘ └──────────────────────────┘    │
│                                                              │
│ ┌────────────────────────────────────────────────────┐     │
│ │ Top Programmes by Revenue                          │     │
│ │ ├─ Enterprise Expansion │ ₹2.1Cr │ 🟢 On Track    │     │
│ │ ├─ SMB Acquisition     │ ₹1.8Cr │ 🟡 At Risk     │     │
│ │ └─ Renewal Campaign    │ ₹1.5Cr │ 🔴 Behind      │     │
│ └────────────────────────────────────────────────────┘     │
│                                                              │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐    │
│ │ Top Reps     │ │ At Risk      │ │ Upcoming         │    │
│ │ (by target)  │ │ (tasks due)  │ │ Milestones       │    │
│ └──────────────┘ └──────────────┘ └──────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

#### 7.4.2 Task Kanban Board (`TaskBoard.jsx`)

```
┌──────────────────────────────────────────────────────────────┐
│  HEADER: Tasks │ Q1 FY 2027 │ [Programme ▼] │ [Rep ▼]       │
├──────────────────────────────────────────────────────────────┤
│ ┌──────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌──────┐ ┌──────┐│
│ │TODO  │ │IP      │ │REVIEW  │ │DONE    │ │BLOCK │ │BKLG  ││
│ │(12)  │ │(8)     │ │(3)     │ │(25)    │ │(2)   │ │(5)   ││
│ ├──────┤ ├────────┤ ├────────┤ ├────────┤ ├──────┤ ├──────┤│
│ │Card1 │ │Card4   │ │Card8   │ │Card11  │ │Card14│ │Card16││
│ │Card2 │ │Card5   │ │Card9   │ │Card12  │ │Card15│ │      ││
│ │Card3 │ │Card6   │ │        │ │Card13  │ │      │ │      ││
│ │      │ │Card7   │ │        │ │        │ │      │ │      ││
│ └──────┘ └────────┘ └────────┘ └────────┘ └──────┘ └──────┘│
│                                                              │
│ [Drag & Drop between columns] -> [Status updates auto-sync] │
└──────────────────────────────────────────────────────────────┘
```

#### 7.4.3 Programme Gantt View (`ProgrammeGantt.jsx`)

```
┌──────────────────────────────────────────────────────────────┐
│  HEADER: Enterprise Expansion │ 🟢 On Track │ [Gantt/Kanban]│
├──────────────────────────────────────────────────────────────┤
│ Milestones:                                                  │
│ ● Initial Meeting ████████████████░░░░░░░░░░░░░░░░░░░░░░│
│ ● Demo Scheduled ░░░░░░░░░░████████████░░░░░░░░░░░░░░░░│
│ ● Proposal Sent  ░░░░░░░░░░░░░░░░████████████████░░░░░░│
│ ● Negotiation   ░░░░░░░░░░░░░░░░░░░░░░░░░░███████████░│
│ ● Closed Won    ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░███│
│                                                              │
│ Tasks (grouped by assignee):                                 │
│ [Rahul K]:                                                   │
│   Call Acme Corp    ████████████████░░░░░░░░░░░░░░░░░░    │
│   Send Proposal     ░░░░░░░░░░░░░░████████████████░░░░    │
│ [Priya S]:                                                   │
│   Product Demo      ░░░░██████████████░░░░░░░░░░░░░░░░    │
│   Follow-up Email   ░░░░░░░░░░░░░░░░░░████████████░░░░    │
│                                                              │
│ Dependency lines: │---F→S---│---F→S---│---F→S---│          │
└──────────────────────────────────────────────────────────────┘
```

#### 7.4.4 Rep Mission Control (`DashboardMyView.jsx`)

```
┌──────────────────────────────────────────────────────────────┐
│  HEADER: My Mission Control │ Rahul K │ AE                    │
├──────────────────────────────────────────────────────────────┤
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐   │
│ │ ₹2Cr     │ │ ₹1.2Cr  │ │ 60%      │ │ Target Status │   │
│ │ Target   │ │ Achieved│ │ Attainmnt│ │ 🟡 At Risk    │   │
│ └──────────┘ └──────────┘ └──────────┘ └───────────────┘   │
│                                                              │
│ Today's Must-Dos (4)                                         │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ 🔴 Call: Acme Corp - VP Eng     | Due: Today 5pm    │   │
│ │ 🟡 Demo: TechStart - Product   | Due: Today 3pm    │   │
│ │ 🟢 Follow-up: MegaCorp - Quote  | Done: 10:30am    │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                              │
│ ┌──────────────┐ ┌──────────────────────────┐              │
│ │ My Tasks (8)  │ │ Deal Pipeline (this Q)   │              │
│ │ [List view]   │ │ ├─ Acme Corp │ ₹50L │🔥 │              │
│ │               │ │ ├─ TechStart │ ₹25L │   │              │
│ └──────────────┘ │ └─ MegaCorp  │ ₹15L │   │              │
│                   └──────────────────────────┘              │
└──────────────────────────────────────────────────────────────┘
```

### 7.5 Active Menu Registration

Following the Menu System pattern, add this module to the menus:

```json
{
  "code": "sales-tasks",
  "name": "Sales Tasks",
  "href": "/sales/tasks",
  "icon": "Target",
  "section": "Operations",
  "order": 6,
  "roles": ["Manager", "Admin", "Superadmin"]
}
```

Add a new menu for the dashboard:

```json
{
  "code": "sales-targets",
  "name": "Targets",
  "href": "/sales/targets",
  "icon": "Crosshair",
  "section": "Operations",
  "order": 7,
  "roles": ["Staff", "Manager", "Admin", "Superadmin"]
}
```

---

## 8. Target Assignment Engine & Strategies

### 8.1 Assignment Strategies for Tasks

Matching and extending the CRM's existing assignment pattern:

| Strategy | Description | When to Use |
|---|---|---|
| `DEAL_OWNER` | Assign task to whoever owns the linked CRM deal | Deal-specific tasks (proposals, demos) |
| `TARGET_OWNER` | Assign task to the user whose target it falls under | General target-driving tasks |
| `LEAST_LOADED` | Find user with fewest active tasks in the programme | Balanced workload distribution |
| `ROUND_ROBIN` | Cycle through eligible users sequentially | Unqualified lead follow-ups |
| `SKILLSET_MATCH` | Match task type to user's role/skillset | Technical demos → SE, Closing → AE |
| `MANAGER` | Assign to the programme manager | Review, approval, coaching tasks |
| `MANUAL` | No auto-assignment — manager assigns explicitly | Complex, high-judgment tasks |

### 8.2 Assignment Engine Implementation (`assignment_engine.py`)

```python
class AssignmentEngine:
    """Core engine for intelligent task assignment"""

    def assign_task(self, task, strategy, context=None):
        if strategy == 'DEAL_OWNER':
            return self._assign_deal_owner(task)

        elif strategy == 'TARGET_OWNER':
            return self._assign_target_owner(task)

        elif strategy == 'LEAST_LOADED':
            return self._assign_least_loaded(task, context)

        elif strategy == 'ROUND_ROBIN':
            return self._assign_round_robin(task, context)

        elif strategy == 'SKILLSET_MATCH':
            return self._assign_by_skillset(task)

        elif strategy == 'MANAGER':
            return self._assign_manager(task)

        return None  # Manual — no auto-assignment

    def _assign_least_loaded(self, task, context):
        """Find user with fewest active tasks in the programme"""
        from django.db.models import Count
        users = context.get('eligible_users', [])
        user_loads = SalesTask.objects.filter(
            programme=task.programme,
            assigned_to__in=users,
            status__in=['TODO', 'IN_PROGRESS']
        ).values('assigned_to').annotate(
            task_count=Count('id')
        )
        # ... find minimum load
```

### 8.3 Resource Levelling

The `resource_allocations` model tracks how much of each person's time is allocated:

```
User: Rahul K (AE)
├─ Enterprise Expansion:   50% allocation → 20h/week
├─ Renewal Campaign:      30% allocation → 12h/week
├─ Buffer:                20% allocation → 8h/week
                         ─────────────────────
Total:                  100% → 40h/week ✅

If a new task needs 5h/week:
- Check if total allocation allows
- Suggest rebalancing if over 100%
```

---

## 9. Task Execution & Project Management Patterns

### 9.1 Sprint Cadence

```
TargetCycle: Q1 FY 2027 (Jan 1 - Mar 31)
├── Sprint 1: Jan 1-14
├── Sprint 2: Jan 15-28
├── Sprint 3: Jan 29 - Feb 11
├── Sprint 4: Feb 12-25
├── Sprint 5: Feb 26 - Mar 11
└── Sprint 6: Mar 12-25
        └── Sprint Review + Retro Mar 26-31
```

Sprint duration is configurable via `TargetCycle.sprint_duration_days` (default: 14).

### 9.2 Task Lifecycle

```
BACKLOG → TODO → IN_PROGRESS → IN_REVIEW → DONE
                    ↓               ↓
                 BLOCKED        CANCELLED
```

Transitions with validation:

| Transition | From | To | Validation |
|---|---|---|---|
| Start | TODO | IN_PROGRESS | Must not have unstarted dependencies |
| Complete | IN_PROGRESS | DONE | All subtasks complete |
| Review | IN_PROGRESS | IN_REVIEW | Manager action required |
| Block | IN_PROGRESS | BLOCKED | Must provide reason |
| Unblock | BLOCKED | IN_PROGRESS | Must resolve blocker |
| Cancel | Any | CANCELLED | Must provide reason (audit logged) |

### 9.3 Daily Standup Integration

Tasks can be tagged with "Today's Priority" for daily standup:

```
Standup data for a team:
- What I completed yesterday (DONE tasks)
- What I'm working on today (IN_PROGRESS, marked priority)
- Blockers I need help with (BLOCKED tasks)
```

This is surfaced via the `DashboardMyView` and `DashboardManager` components.

### 9.4 Commenting & Collaboration

Instead of creating a separate comment model (to avoid over-engineering), comments are handled via:

1. **TaskAttachments with `note` field** — lightweight text notes
2. **SalesTaskLog with `COMMENT_ADDED` activity_type** — threaded activity stream
3. **ContactRemark reuse** — if the task is linked to a contact/deal, remarks flow through

---

## 10. Integration Points with Existing Modules

### 10.1 CRM Integration (Deepest Integration)

| CRM Feature | Task Manager Integration |
|---|---|
| `Pipeline.deals` | Tasks can be linked to deals via `SalesTask.crm_deal` |
| `Stage changes` | Triggers auto-task generation (e.g., "Negotiation" → "Prepare contract") |
| `Deal value` | Feeds into `revenue_impact` field on tasks |
| `Assigned user` | Default task assignee = deal owner |
| `KanbanBoard` | Task board mirrors Kanban pattern — consistent UX |
| `ContactLog` | Tasks log activities on contacts/deals for unified audit trail |

#### 10.1.1 Signal Handlers (`signals.py`)

```python
@receiver(post_save, sender=CRM)
def on_deal_created(sender, instance, created, **kwargs):
    """When a new deal is added to a pipeline, check for auto-generation rules"""
    if created:
        # Find active target cycles
        # Find assignment rules with trigger=DEAL_CREATED
        # Generate tasks

@receiver(pre_save, sender=CRM)
def on_deal_stage_changing(sender, instance, **kwargs):
    """When a deal moves stages, check for stage-change task rules"""
    if instance.pk:
        try:
            old = CRM.objects.get(pk=instance.pk)
            if old.stage_id != instance.stage_id:
                # Trigger stage-change task generation
                pass
        except CRM.DoesNotExist:
            pass
```

### 10.2 Contacts Integration

| Contact Feature | Task Manager Integration |
|---|---|
| `Contact` model | Tasks can reference contacts directly for non-deal activities |
| `ContactLog` | Task activities logged against contacts for unified timeline |
| `ImportBatch` | Campaign-level targets can be created from import batches |

### 10.3 HR Integration

| HR Feature | Task Manager Integration |
|---|---|
| `Employee` | Task assignment uses `User` model (matching HR pattern) |
| `Department` | Team-level targets assigned to departments |
| `AppraisalCycle` | `TargetCycle` can optionally link to PMS cycles |
| `PerformanceGoal` | Sales targets can feed into individual performance goals |
| `SalaryComponent` | Bonus/incentive calculation can reference target attainment |
| `EmployeeLeaveBalance` | Resource allocation adjusts for planned leaves |

#### 10.3.1 Future Integration: Commission Calculation

When an `Invoice` is paid for a deal that was in a `TargetLineItem`:
- Mark line item as `attained`
- Update `SalesTarget.achieved_amount`
- Feed attainment data to HR Payroll for commission calculation

### 10.4 Invoices Integration

| Invoice Feature | Task Manager Integration |
|---|---|
| `Invoice.status → APPROVED` | Triggers target line item attainment |
| `Invoice.amount` | Feeds into `actual_revenue` on line items |

### 10.5 Payments Integration

When a `Payment` is received for an invoiced deal:
- Auto-mark target line items as attained
- Update pipeline revenue achievements

---

## 11. Permissions & Role-Based Access Control

### 11.1 Permission Matrix

| Action | Staff (Rep) | Manager | Admin | Superadmin |
|---|---|---|---|---|
| View own targets/tasks | ✅ | ✅ | ✅ | ✅ |
| View team targets/tasks | ❌ | ✅ | ✅ | ✅ |
| View all targets/tasks | ❌ | ❌ | ✅ | ✅ |
| Create target cycles | ❌ | ❌ | ✅ | ✅ |
| Create targets (assign) | ❌ | ✅ (team) | ✅ | ✅ |
| Create tasks | ✅ (own) | ✅ | ✅ | ✅ |
| Assign tasks | ❌ | ✅ | ✅ | ✅ |
| Update task status | ✅ (own) | ✅ | ✅ | ✅ |
| Log time | ✅ (own) | ✅ | ✅ | ✅ |
| View dashboard | ✅ (own) | ✅ (team) | ✅ (all) | ✅ (all) |
| Create programmes | ❌ | ✅ | ✅ | ✅ |
| Manage milestones | ❌ | ✅ | ✅ | ✅ |
| Delete tasks/programmes | ❌ | ❌ | ✅ | ✅ |
| Configure assignment rules | ❌ | ❌ | ✅ | ✅ |

### 11.2 Permission Classes (`permissions.py`)

Following the HR permission pattern:

```python
class IsSalesManager(permissions.BasePermission):
    """Manager role — can assign tasks, manage programmes, view team data"""

class IsSalesAdmin(permissions.BasePermission):
    """Admin/Superadmin — full access to all data and configuration"""

class IsTaskOwnerOrManager(permissions.BasePermission):
    """Object-level: task owner, their manager, or admin"""

class CanAssignTasks(permissions.BasePermission):
    """Only managers and above can assign tasks to others"""
```

### 11.3 Department Scoping

Following the CRM pattern where Staff users only see their department's pipelines:

```python
def get_queryset(self):
    user = self.request.user
    if user.role == 'Superadmin':
        return SalesTask.objects.all()
    if user.role in ['Admin', 'Manager']:
        # Can see tasks from their department(s)
        return SalesTask.objects.filter(
            programme__target_cycle__sales_targets__assigned_department__in=user.departments.all()
        ).distinct()
    # Staff: only their own tasks
    return SalesTask.objects.filter(assigned_to=user)
```

---

## 12. Reporting, Analytics & Dashboards

### 12.1 Dashboard Types

| Dashboard | User | Key Metrics |
|---|---|---|
| **Executive** | VP Sales / CRO | Total attainment %, programme health, top/bottom performers, forecast vs actual |
| **Manager** | Sales Manager | Team attainment, individual rep progress, task completion rate, next milestones |
| **Rep Mission Control** | Sales Rep | Personal target %, today's tasks, deal pipeline, time logged this week |
| **Programme** | PM / Manager | Gantt timeline, milestone status, resource allocation, revenue trajectory |

### 12.2 Report Types

| Report | Frequency | Description |
|---|---|---|
| Target Attainment Report | Weekly | % achieved vs target, by rep and team |
| Task Completion Rate | Weekly | Tasks completed vs planned, by type |
| Pipeline Velocity | Monthly | Time from task to deal close, by stage |
| Resource Utilisation | Monthly | Hours logged vs allocated, overallocation alerts |
| Programme Health | Weekly | RAG status (Red/Amber/Green) per programme |
| Sprint Burndown | Bi-weekly | Tasks remaining vs time remaining in sprint |

### 12.3 Key Performance Indicators (KPIs)

| KPI | Formula | Target |
|---|---|---|
| Target Attainment | `achieved_amount / target_amount × 100` | >80% |
| Task Completion Rate | `tasks_completed / tasks_scheduled × 100` | >75% |
| On-Time Delivery | `tasks_completed_by_due / tasks_completed × 100` | >90% |
| Weighted Progress | Revenue-weighted task completion | Inline |
| Resource Utilisation | `hours_logged / hours_allocated × 100` | 80-100% |
| Programme Health Score | Compound score (milestones, tasks, revenue) | >70 |
| Average Task Cycle Time | Average hours from TODO → DONE | Varies by type |

---

## 13. Industry Standards & Best Practices

### 13.1 Sales Process Standards

| Standard | Application in Module |
|---|---|
| **MEDDIC** (Metrics, Economic Buyer, Decision Criteria, Decision Process, Identify Pain, Champion) | Task types include MEDDIC evaluation steps; milestones can be MEDDIC criteria |
| **BANT** (Budget, Authority, Need, Timeline) | Tasks can be tagged with BANT qualification status |
| **Challenger Sale** | Task types include "Teach," "Tailor," "Take Control" variants |
| **SPIN Selling** (Situation, Problem, Implication, Need-Payoff) | Task descriptions prompt SPIN questioning |
| **Sandler Rules** | Task status includes "Up-Front Contract" milestone |
| **Value Selling** | Revenue impact field captures deal value context |
| **Salesforce Sales Method** | Programme-level rollup (similar to Salesforce Campaigns) |
| **MEDDPICC** (MEDDIC + Competition, Commercial Terms) | Extended task metadata supports competitive tracking |

### 13.2 Project Management Standards

| Standard | Application in Module |
|---|---|
| **PMBOK** (Project Management Body of Knowledge) | Work Breakdown Structure via tasks; milestones; resource allocation; risk tracking |
| **PRINCE2** | Programme-level management; stage gates via milestones |
| **Agile/Scrum** | Sprints, daily standup integration, sprint burndown |
| **Critical Path Method (CPM)** | Dependency graph → critical path identification |
| **Earned Value Management (EVM)** | Weighted progress = Planned Value vs Earned Value |
| **Gantt Charts** | Timeline visualisation for programme planning |
| **RACI Matrix** | Resource allocation with roles (Responsible, Accountable, Consulted, Informed) |
| **OKR Framework** | TargetCycle = Objective, SalesTargets = Key Results |

### 13.3 Industry Best Practices

#### 13.3.1 Sales Management Best Practices

- **Pipeline Hygiene**: Tasks auto-generated when deals stay in a stage too long
- **Activity-Based Coaching**: Managers can see task completion patterns and coach specific behaviours
- **Forecast Accuracy**: Weighted progress → probabilistic revenue forecasting
- **Territory Alignment**: Department-level targets match sales territory design
- **Time Blocking**: Reps allocate time in the system, admin sees where energy goes
- **Top Grading**: Performance metrics identify A/B/C players for coaching/improvement/PIP

#### 13.3.2 Project Management Best Practices

- **Definition of Done**: Clear status criteria per task type
- **WIP Limits**: Configurable limits per Kanban column to prevent task-swamping
- **Retrospectives**: Sprint-end review capability with notes and action items
- **Risk Register**: Tasks tagged as BLOCKED with impact assessment
- **Change Control**: Programme milestone changes require approval (audit logged)
- **Capacity Planning**: Resource allocation shows % utilisation across programmes

#### 13.3.3 Scale Considerations

- **Up to 50 reps**: Real-time Kanban, instant updates (no caching needed)
- **50-200 reps**: Debounced API, Redis caching for dashboard metrics
- **200+ reps**: Pre-aggregated dashboard tables, async report generation

### 13.4 Matching ByteHive Patterns

| ByteHive Pattern | This Module |
|---|---|
| `Main` base model (UUID PK) | ✅ All models inherit `Main` |
| Router-based ViewSets | ✅ Matching CRM/HR patterns |
| Nested routers (pipeline/stages) | ✅ `target-cycles/{id}/targets/` |
| Wrapped responses (success/data) | ✅ Consistent envelope |
| `django-filter` for filtering | ✅ Heavy filter usage |
| DRF `PageNumberPagination` | ✅ Consistent pagination |
| `select_related` / `prefetch_related` | ✅ Performance patterns |
| Signal-based event triggers | ✅ `signals.py` for auto-generation |
| Audit logging per model | ✅ `SalesTaskLog` model |
| `is_active` for soft delete | ✅ On relevant models |
| Dark industrial UI with Tailwind | ✅ Matching DESIGN ARCHITECTURE.md |
| Consistent tab/button patterns | ✅ Sliding tabs, HSL semi-transparent buttons |
| Modular file structure | ✅ pages/, components/, hooks/, services/ |

---

## 14. Implementation Roadmap

### 14.1 Phase Breakdown

| Phase | Scope | Timeline | Dependencies |
|---|---|---|---|
| **Phase 1: Foundation** | Backend models, migrations, base API, admin | Week 1-2 | None (new app) |
| **Phase 2: Core Business Logic** | Target engine, task generator, assignment engine, signals | Week 3-4 | Phase 1 |
| **Phase 3: Frontend — Task Board** | TaskBoard, TaskCard, TaskDialog, drag-drop | Week 5-6 | Phase 1 |
| **Phase 4: Frontend — Targets & Programmes** | TargetCycleList, SalesTargetDetail, ProgrammeDetail, Gantt | Week 7-8 | Phase 3 |
| **Phase 5: Frontend — Dashboards** | Executive, Manager, Rep dashboards, reports | Week 9-10 | Phase 4 |
| **Phase 6: Integrations** | CRM signal handlers, contacts linkage, menu registration | Week 11 | Phase 2 |
| **Phase 7: Testing & Polish** | Unit tests, integration tests, performance, edge cases | Week 12 | All |

### 14.2 Detailed Sprint Breakdown

#### Sprint 1 (Week 1): Backend Foundation

| Task | Details |
|---|---|
| Create `sales_task_manager` app | `apps.py`, register in `INSTALLED_APPS`, add URL in `core/urls.py` |
| Implement all models | 12 models from Section 4, including fields, choices, indexes, `__str__` |
| Create migrations | `makemigrations` + `migrate` |
| Implement serializers | All serializers with nested reads, flat writes (matching CRM pattern) |
| Implement ViewSets | All CRUD endpoints with permission checks |
| Register in admin | All models in `admin.py` |
| Create permissions.py | All permission classes |
| Register URLs | Router-based URLs matching HR/CRM pattern |

#### Sprint 2 (Week 2): Core Business Logic

| Task | Details |
|---|---|
| Implement `target_engine.py` | Target cascade, achievement calculation, close-out logic |
| Implement `task_generator.py` | Auto-generation from targets, deal events, recurring rules |
| Implement `assignment_engine.py` | All 7 assignment strategies |
| Implement `progress_tracker.py` | Weighted progress calculation, dependency chain resolution |
| Create `signals.py` | Signal handlers for CRM deal creation/stage change |
| Write `TargetAssignmentRule` model CRUD | API for managing rules |

#### Sprint 3 (Week 3-4): Frontend Task Board

| Task | Details |
|---|---|
| Create route file | `SalesTaskRoutes.jsx`, register in App.jsx |
| Create `TaskCard.jsx` | Kanban card matching `KanbanCard.jsx` pattern |
| Create `TaskColumn.jsx` | Kanban column matching `KanbanBoard.jsx` |
| Create `TaskBoard.jsx` | Full Kanban with drag-drop (DndContext) |
| Create `TaskDetailDialog.jsx` | Split-screen modal (matching DealDetailsDialog) |
| Create `TaskCreateDialog.jsx` | Quick-add task modal |
| Create API service | `salesTaskService.js` |
| Create hooks | `useSalesTasks.js`, `useSalesProgrammes.js` |

#### Sprint 4 (Week 5-6): Targets & Programmes UI

| Task | Details |
|---|---|
| Create `TargetCycleList.jsx` | Cycle list with status badges |
| Create `TargetCycleForm.jsx` | Create/edit cycle form |
| Create `SalesTargetForm.jsx` | Target creation with line items |
| Create `TargetLineItemForm.jsx` | Deal-level line items |
| Create `SalesProgrammeDetail.jsx` | Programme view with tabs (Overview, Gantt, Tasks, Team) |
| Create `ProgrammeGantt.jsx` | Timeline/Gantt component |
| Create `ResourceLoadView.jsx` | Resource allocation matrix |
| Create `SalesProgrammeForm.jsx` | Programme CRUD |
| Create `FilterBar.jsx` | Advanced multi-filter component |

#### Sprint 5 (Week 7-8): Dashboards

| Task | Details |
|---|---|
| Create `DashboardMyView.jsx` | Rep mission control |
| Create `DashboardManager.jsx` | Team view with RAG status |
| Create `DashboardExecutive.jsx` | VP/CRO consolidated view |
| Create `ProgressBar.jsx` | Weighted progress bar |
| Create `WeightedProgressIndicator.jsx` | Circular progress with ₹ weight |
| Create `TimeTrackingWidget.jsx` | Quick time entry |
| Create `SprintSelector.jsx` | Sprint/week switcher |

#### Sprint 6 (Week 9-10): Integrations & Polish

| Task | Details |
|---|---|
| Connect CRM signals | Wire up deal create/update signals |
| Connect contacts | Task logging on contact timeline |
| Register menu items | Add menus with roles |
| Implement `SalesTaskContext.jsx` | Global state for active task/target |
| Performance pass | `select_related`, `prefetch_related`, pagination tuning |
| Error handling | Consistent error states matching existing modules |
| Loading states | Skeleton loaders, spinner patterns |
| Empty states | No-data illustrations matching CRM pattern |

#### Sprint 7 (Week 11-12): Testing & Documentation

| Task | Details |
|---|---|
| Unit tests for models | Model validation, constraints, str methods |
| Unit tests for business logic | Target engine, task generator, assignment engine, progress tracker |
| API integration tests | All endpoints, auth, permissions |
| Frontend component tests | Key components render correctly |
| API documentation | Update API reference |
| User documentation | How-to guides per persona |

---

## 15. Appendices

### 15.1 Appendix A: File Checklist

#### Backend (`bytehive_business_backend/sales_task_manager/`)

| File | Purpose | Pattern Source |
|---|---|---|
| `__init__.py` | Package init | Standard |
| `apps.py` | App config | `crm/apps.py` |
| `models.py` | 12 data models | `crm/models.py`, `hr/models.py` |
| `views.py` | ViewSets (15+) | `crm/views.py`, `hr/views.py` |
| `serializers.py` | Serializers | `crm/serializers.py` |
| `urls.py` | Router registrations | `crm/urls.py` |
| `permissions.py` | Permission classes (5+) | `hr/permissions.py` |
| `admin.py` | Django admin config | `crm/admin.py` |
| `signals.py` | Signal handlers | `invoices/signals.py` |
| `services/target_engine.py` | Target calculation logic | New |
| `services/task_generator.py` | Auto-task generation | New |
| `services/assignment_engine.py` | Task assignment strategies | Extends `crm/views.py` auto-assignment |
| `services/progress_tracker.py` | Weighted progress calc | New |
| `migrations/` | Auto-generated | Django |

#### Frontend (`bytehive_business_frontend/src/modules/sales-task-manager/`)

| Directory | Pattern Source |
|---|---|
| `pages/` (9 pages) | `crm/pages/`, `hr/pages/` |
| `components/` (20+ components) | `crm/components/` |
| `hooks/` (5 hooks) | `crm/services/` hooks pattern |
| `services/` (2 files) | `lib/api.js` + `crm/services/` |
| `context/` (1 context) | `AuthContext.jsx`, `MenuContext.jsx` |
| Routes file | `HRRoutes.jsx` |

### 15.2 Appendix B: URL Registration

In `bytehive_business_backend/core/urls.py`:

```python
urlpatterns = [
    # ... existing paths
    path('api/sales/', include('sales_task_manager.urls')),
]
```

In `bytehive_business_frontend/src/App.jsx`:

```jsx
import SalesTaskManager from './modules/sales-task-manager/SalesTaskRoutes';

// In Routes:
<Route
  path="/sales/tasks/*"
  element={
    <ProtectedRoute>
      <SalesTaskManager />
    </ProtectedRoute>
  }
/>
```

### 15.3 Appendix C: Key Design Decisions

| Decision | Rationale |
|---|---|
| **Separate app vs extending CRM** | Keeps concerns separated; CRM is pipeline-focused, this is execution-focused. Cleaner migrations and permissions. |
| **Task types as model choices vs dynamic** | Sales task types are well-defined (CALL, MEETING, etc.) — static choices are simpler and give type-specific UI. |
| **Revenue-weighted progress not task-count** | A ₹10L demo is not the same as a ₹10K call. Revenue weighting reflects real business impact. |
| **Programme abstraction** | Sales initiatives need PM-style management (Gantt, resources, milestones). A flat task list doesn't cut it. |
| **Dependencies as separate model vs JSONField** | Proper FK relationships enable dependency-aware scheduling, critical path analysis, and circular dependency detection. |
| **Audit logging as separate model** | Matches `ContactLog` pattern. Enables rich querying, timelines, and compliance. |
| **Gantt in frontend, not backend** | Gantt position data is derived from task due dates + dependencies. No need to store positions. |
| **Sprint concept** | Borrowed from Agile — gives reps a manageable timebox and creates urgency. Configurable duration. |
| **Signals for auto-generation** | Keeps core ViewSets clean. Business logic lives in signal handlers, not in views. |

### 15.4 Appendix D: Glossary

| Term | Definition |
|---|---|
| TargetCycle | A time-bounded target period (quarterly, annual) |
| SalesTarget | Revenue target assigned to a user, team, or department |
| TargetLineItem | A specific expected deal/revenue within a target |
| SalesProgramme | A focused sales initiative with milestones, tasks, and resources |
| ProgrammeMilestone | A key event or gate within a programme |
| SalesTask | An atomic work unit linked to a target, deal, or programme |
| TaskDependency | A relationship where one task depends on another |
| Revenue Impact | The estimated ₹ value of completing a task |
| Weighted Progress | Revenue-weighted task completion percentage |
| Sprint | A fixed-duration execution cycle (default 14 days) |
| Resource Allocation | % of a person's time assigned to a programme |
| Attainment | Actual achievement against target (%) |
| Assignment Strategy | Rule for auto-assigning tasks to users |

---

> **Document Status:** Planning / Design Phase  
> **Next Steps:**  
> 1. Review this plan with stakeholders  
> 2. Approve Phase 1 (Foundation) for development  
> 3. Begin Sprint 1: Create the Django app and implement all 12 models  
> 4. Create initial migration and verify in Django admin  
> 5. Proceed to API implementation
