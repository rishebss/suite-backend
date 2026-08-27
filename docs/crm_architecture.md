# CRM Architectures

## Overview

The CRM module manages sales pipelines with dynamic stages, drag-and-drop Kanban board, deal tracking, and a Lead Nurture feature that creates retarget pipelines. Built with Django REST Framework (3.17.1) backend and React frontend.

Supports **single** and **bulk** operations for moving, adding (copying), and deleting deals across pipelines, with chunked processing and progress bars for large batches.

---

## Database Models

### Pipeline (`crm/models.py`)
- `name`, `description` — basic info
- `departments` — M2M to `authentication.Department` (staff access control)
- `assignment_type` — `round_robin`, `least_loaded`, `single_user`, or `manual`
- `pipeline_type` — `sales`, `retarget`, or `clients`
- `mandatory_fields` — JSON list of required fields per pipeline
- `custom_fields_enabled` — toggle for custom fields
- Auto-creates 6 default stages on creation: Lead → Lost

### Stage (`crm/models.py`)
- FK to `Pipeline`
- `name`, `slug`, `order`, `color`
- `unique_together = ('pipeline', 'slug')`
- DB index: `(pipeline, order)`

### CRM (`crm/models.py`) — the "deal" table
- FK to `Pipeline` (nullable, CASCADE)
- FK to `Stage` (nullable, SET_NULL on delete)
- FK to `Contact` (CASCADE)
- FK to `assigned_user` (nullable, SET_NULL)
- `value` — DecimalField(max_digits=12, decimal_places=2)
- `priority` — `Low` / `Medium` (default) / `High`
- `notes` — TextField
- DB indexes: `(pipeline, stage)`, `(created_at)`, `(pipeline, assigned_user)`

### Priority Choices
| Value | Display |
|-------|---------|
| Low   | Low     |
| Medium| Medium  |
| High  | High    |

### Stage Color Choices
`blue`, `purple`, `amber`, `orange`, `green`, `red`, `pink`, `cyan`

### Pipeline Type Choices
| Value      | Display |
|------------|---------|
| sales      | Sales   |
| retarget   | Retarget|
| clients    | Clients |

### Assignment Type Choices
| Value         | Display        |
|---------------|----------------|
| round_robin   | Round Robin    |
| least_loaded  | Least Loaded   |
| single_user   | Single User    |
| manual        | Manual         |

### Contact Status (from contacts app)
Standard: `Lead`, `Prospect`, `Customer`, `Inactive`, **`Retarget`** (added for Lead Nurture)

---

## Backend Architecture

### Settings (`core/settings.py`)
```python
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "core.pagination.CustomPageNumberPagination",
    "PAGE_SIZE": 100,
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        ...
    ],
}
```

**Note:** DRF 3.17.1's `PageNumberPagination` does NOT read `PAGE_SIZE_QUERY_PARAM` or `MAX_PAGE_SIZE` from settings. A custom class is required.

### Custom Pagination (`core/pagination.py`)
```python
class CustomPageNumberPagination(PageNumberPagination):
    page_size_query_param = "page_size"
    max_page_size = 1000
```

### Serializers (`crm/serializers.py`)

| Serializer | Purpose | Fields |
|------------|---------|--------|
| `UserBriefSerializer` | Lightweight user (avoids N+1 from DepartmentSerializer) | id, email, first_name, last_name, mobile, role, is_active |
| `ContactBriefSerializer` | Lightweight contact (avoids N+1 from ContactSerializer.get_pipelines) | id, name, email, phone, status, contact_id |
| `StageSerializer` | Stage CRUD | id, pipeline, name, slug, order, color |
| `PipelineSerializer` | Pipeline with nested stages + departments + deals_count | Full pipeline with embedded stages, departments, deals_count, assignment_type, pipeline_type, mandatory_fields, custom_fields_enabled |
| `CRMSerializer` | Deal CRUD with nested brief serializers | contact_details (ContactBrief), stage_details (StageSerializer), assigned_user_details (UserBriefSerializer) |

### Views (`crm/views.py`)

#### CRMViewSet
- **Queryset**: `CRM.objects.all().select_related("contact", "pipeline", "stage", "assigned_user").prefetch_related("pipeline__stages", "pipeline__departments")`
- **Staff filtering**: Staff users only see deals where `assigned_user = self` (their own deals)
- **Query params** for filtering:
  - `stage` — single stage ID
  - `stages` — comma-separated stage IDs (UUIDs supported, `if s` guard instead of `isdigit()`)
  - `pipeline` — pipeline ID
  - `assigned_user` — user ID
  - `search` — text search by `search_by` field(s)
  - `search_by` — comma-separated fields from `{name, email, phone}` (default: `name`)
- **Pagination**: respects `page_size` query param via `CustomPageNumberPagination`

##### Auto-Assignment Logic
- `get_pipeline_users(pipeline)` — gets active users in pipeline's departments
- `assign_round_robin(pipeline)` — finds last assigned deal's user, returns next user cyclically
- `assign_least_loaded(pipeline)` — annotates users with `deal_count`, returns lowest

##### `perform_create`
- Auto-assigns via round_robin / least_loaded / single_user (falls back to least_loaded)
- Logs "Pipeline Added" and optionally "Assignment Changed" activity

##### `perform_update`
- Tracks **stage changes** → logs "Stage Changed"
- Tracks **pipeline changes** → logs "Pipeline Changed" on both source and target, **resets `assigned_user = None`** when pipeline changes
- Tracks **assignment changes** → logs "Assignment Changed" (including "Unassigned")
- All activity logs via `ContactLog` bulk operations

##### `destroy` (Single Delete)
- Creates "Deal Deleted" activity log before deletion (`crm=None` on log since CRM will be deleted)

##### `copy_to_pipeline` (Single Deal Add)
- **Detail action** — `POST /api/crm/pipeline/{id}/copy-to-pipeline/`
- Creates a **new CRM entry** with same contact, value, priority
- **Does NOT inherit** `assigned_user` from source — starts as `None`
- Auto-assigns if target pipeline has round_robin or least_loaded strategy
- Creates "Pipeline Changed" log on source deal, "Pipeline Added" + "Assignment Changed" on new deal

##### `bulk_add_to_pipeline` (Bulk Deal Add)
- **List action** — `POST /api/crm/pipeline/bulk-add-to-pipeline/`
- Accepts `{ deal_ids: [...], pipeline_id: "..." }`
- Creates **new CRM entries** for each source deal (copy semantics)
- Staff access check against target pipeline's departments
- **Bulk create** with `batch_size=1000`
- Pre-calculates assignments in memory for performance:
  - round_robin: tracks `rr_index` cyclically
  - least_loaded: tracks `ll_loads` dict in memory
- Bulk creates activity logs (both "Pipeline Added" on new + "Pipeline Changed" on source)

##### `bulk_add_from_batch` (Import Batch → Pipeline)
- **List action** — `POST /api/crm/pipeline/bulk-add-from-batch/`
- Adds contacts from an import `batch_id` into a pipeline
- Supports `offset` / `limit` for chunked processing
- **Deduplicates** — skips contacts already in the target pipeline
- Updates contact status to `"Lead"` after adding
- Deduplicates activity logs (skips if "Pipeline Added" log already exists for CRM)
- Chunks in 1500-contact batches internally

##### `bulk_add_contacts` (Legacy + Lead Nurture)
- **List action** — `POST /api/crm/pipeline/bulk-add-contacts/`
- Two modes via `source_pipeline` param:
  - **With `source_pipeline`** (Lead Nurture): **Moves** existing deals from source pipeline → updates pipeline_id, stage, priority="High", contact status="Retarget"
  - **Without `source_pipeline`** (Legacy): Creates new CRM entries, deduplicates, updates contact status="Lead"
- Both modes: auto-assignment, bulk activity logs, chunked processing

##### `bulk_move_deals` (Bulk Deal Move)
- **List action** — `POST /api/crm/pipeline/bulk-move-deals/`
- Accepts `{ deal_ids: [...], pipeline_id: "...", stage_id: "..." }`
- **Updates existing CRM rows** — same CRM IDs preserved
- **Resets `assigned_user = None`** when moving between pipelines
- Creates "Pipeline Changed" logs for both target and source pipelines
- Staff access check against target pipeline

##### `bulk_delete_deals` (Bulk Deal Delete)
- **List action** — `POST /api/crm/pipeline/bulk-delete-deals/`
- Accepts `{ deal_ids: [...] }`
- Creates "Deal Deleted" activity logs before deletion (with `crm=None`)
- Bulk creates logs, then bulk deletes CRM entries

#### PipelineViewSet
- **Queryset**: `Pipeline.objects.annotate(deals_count=Count("deals")).prefetch_related("stages", "departments")`
- **Staff filtering**: restricts to pipelines whose departments match user's departments
- **Search**: by `name`, `description` via `SearchFilter`
- `perform_create`: auto-creates 6 default stages (Lead → Lost)
- `assignment_stats`: `GET /api/crm/pipelines/{id}/assignment-stats/` — returns `{ total_deals, assigned_deals, unassigned_deals, user_loads }`
- `trigger_assignment`: `POST /api/crm/pipelines/{id}/trigger-assignment/` — bulk-assigns all unassigned deals using specified strategy (`round_robin`, `least_loaded`, `single_user`). Accepts optional `strategy` and `target_user_id` (for single_user). Uses `bulk_update` with `batch_size=1000`.

#### StageViewSet
- Nested under `/api/crm/pipelines/{pipeline_pk}/stages/`
- **Staff filtering**: checks pipeline access via departments
- `perform_create`: auto-generates unique slug (handles collisions with `-1`, `-2` suffixes)
- `perform_update`: regenerates slug only if name changed, maintains uniqueness
- `reorder`: `POST /api/crm/pipelines/{pipeline_pk}/stages/reorder/` — bulk updates stage order

---

## Frontend Architecture

### Component Tree

```
CRM.jsx (page — main Kanban view)
├── PipelineSelector
├── KanbanColumn (KanbanBoard.jsx)
│   └── KanbanCard (KanbanCard.jsx)
├── CreatePipelineModal
├── SearchDialog
├── DealDetailsDialog
├── AddLeadDialog / AddLeadStructured
├── ConfirmDeleteDialog
├── SingleDealMove
├── SingleDealAdd
├── MultipleDealMove
├── MultipleDealAdd
├── Actions
└── LeadNurtureModal
```

### CRM.jsx — Main Kanban Page

**State**:
- `deals` — keyed by stage ID, each entry: `{ items, nextPage, hasMore, count, isLoadingMore }`
- `selectedPipeline` — current pipeline (persisted to `localStorage('crm_selected_pipeline_id')`)
- `isSelectMode` / `selectedCards` — multi-select mode with Set of selected card IDs
- `showBulkDropdown` — dropdown for bulk actions (Move, Add, Delete)
- `showBulkMoveModal`, `showBulkAddModal`, `showBulkDeleteConfirm` — bulk action modals
- `isBulkDeleting` / `bulkDeleteProgress` — bulk delete progress tracking

**Fetching**: `fetchDeals()` — parallel requests per stage, 100 deals per page, server-side paginated

**Load More**: `fetchMoreDeals(stageId)` — fetches next page for a specific stage, appends to items

**Drag & Drop**: `@dnd-kit` with `PointerSensor`, drag overlay renders `KanbanCardUI`

**Pipeline Selection**: stored in `localStorage('crm_selected_pipeline_id')`

**Tabs**: `pipeline` (Kanban view) / `actions` (admin tools, admin-only)

**Guards**: Non-admin users can't access Actions tab — forcibly reset to pipeline tab

#### Select Mode & Bulk Actions

When "Select" is toggled:
1. Each card shows a checkbox on hover
2. Selected card count badge appears next to buttons
3. An arrow dropdown expands showing:
   - **Move to Pipeline** → opens `MultipleDealMove`
   - **Add to Pipeline** → opens `MultipleDealAdd`
   - **Delete** (red, separated by divider) → opens `ConfirmDeleteDialog` with progress bar

**Bulk Delete flow**:
1. `handleBulkDeleteClick` — closes dropdown, opens confirmation dialog
2. `confirmBulkDelete` — chunks selected cards into groups of **500**, sends each chunk to `POST /api/crm/pipeline/bulk-delete-deals/`
3. Progress bar (red) replaces Cancel/Delete buttons during deletion
4. On error: dialog closes cleanly (no stuck progress state)
5. On success: clears selection, exits select mode, refreshes deals

#### handleDealMoved / handleDealAdded (callbacks)
After bulk move/add, refetches pipelines to find the target pipeline and switches to it.

### KanbanBoard.jsx — KanbanColumn
- `useDroppable` from `@dnd-kit` for each column
- `SortableContext` with `verticalListSortingStrategy`
- Column color derived from stage color via `getColumnColor()`
- Shows "Load More (X/Y)" button when `hasMore` is true
- In select mode: passes `isSelectMode`, `selectedCards`, `onToggleCardSelect` to each card

### KanbanCard.jsx — Deal Card
- `useSortable` from `@dnd-kit` for drag
- `KanbanCardUI` — presentational component (also used in drag overlay)
- **Status colors** (contact status badges):
  | Status     | Style             |
  |------------|-------------------|
  | Lead       | blue gradient     |
  | Prospect   | purple gradient   |
  | Customer   | green gradient    |
  | Inactive   | zinc gradient     |
  | Retarget   | amber gradient    |
- **Priority colors** (priority badges):
  | Priority | Style                          |
  |----------|--------------------------------|
  | High     | red background/border          |
  | Medium   | amber background/border        |
  | Low      | emerald background/border      |
- **Card actions** (3-dot menu): View Details, Move to Pipeline, Add to Pipeline, Delete
- **Select mode**: checkbox appears on hover; checked cards show blue ring

### SingleDealMove.jsx
Modal to **move** a single deal to another pipeline:
- Lists all available pipelines, **disables the current pipeline** with "Current pipeline" text
- Inline pipeline creation (via CreatePipelineModal)
- On confirm: calls `PATCH /api/crm/pipeline/{dealId}/` with `{ pipeline, stage }`
- Backend logs "Pipeline Changed" on both source and target, **resets `assigned_user = None`**
- Visual: selected pipeline gets blue highlight + checkmark

### SingleDealAdd.jsx
Modal to **copy** a single deal to another pipeline (creates new CRM entry):
- Same pipeline list UI as move
- On confirm: calls `POST /api/crm/pipeline/{dealId}/copy-to-pipeline/`
- Backend creates new CRM with **`assigned_user = None`** (fresh auto-assignment if configured)
- Logs "Pipeline Changed" on source, "Pipeline Added" + "Assignment Changed" on new deal
- Business logic: same contact can purchase **different services** handled by different pipeline users

### MultipleDealMove.jsx
Modal to **move** multiple selected deals to another pipeline:
- Accepts `dealIds` array + `currentPipelineId`
- Same pipeline list UI (current disabled)
- Chunks deals into groups of **500**, sends to `POST /api/crm/pipeline/bulk-move-deals/`
- **Progress bar** (blue) shown when ≥500 deals: phase label + `current / total` counter
- `BiSolidAddToQueue` icon on the add button
- On completion: closes modal, calls `onMoved(targetPipelineId)`

### MultipleDealAdd.jsx
Modal to **copy** multiple selected deals to another pipeline (creates new CRM entries):
- Mirrors MultipleDealMove UI
- Sends to `POST /api/crm/pipeline/bulk-add-to-pipeline/`
- Same 500-chunk processing with progress bar
- Current pipeline disabled with "Current pipeline" label

### SearchDialog.jsx
Global search across all deals in the current pipeline:
- Text input with real-time filtering
- Fetches from `GET /api/crm/pipeline/?search=...&search_by=name,email,phone`
- Results displayed as a selectable list
- Selecting a deal opens DealDetailsDialog
- Keyboard shortcut or button triggers

### DealDetailsDialog.jsx
Full deal detail view with editable fields:
- Shows contact info (name, email, phone, status)
- Shows stage, pipeline, value, priority, notes
- **Assignment dropdown**: lists eligible users (from pipeline's departments)
- Stage change dropdown
- Inline save via `PATCH /api/crm/pipeline/{id}/`
- Delete button opens ConfirmDeleteDialog

### ConfirmDeleteDialog (reusable via `@/components/ConfirmDeleteDialog`)
- Used for single delete (deal, contact, etc.) and bulk delete
- Props: `isOpen`, `onClose`, `onConfirm`, `isDeleting`, `title`, `description`, `progress`
- **Progress mode**: when `progress != null`, replaces Cancel/Delete buttons with a **red progress bar** showing phase label + `current / total`
- Backdrop click disabled during loading/progress

### Actions.jsx — Admin Panel
Admin-only tab containing **6 action cards**. Each card shows a badge of the currently selected pipeline name (except Manage Pipeline). Not tied to any specific `pipeline_type` — available for sales, retarget, and clients pipelines alike.

| Card | Opens | Backend Endpoints | Models Touched |
|------|-------|-------------------|----------------|
| Manage Pipeline | `CreatePipelineModal` | `GET/POST /api/crm/pipelines/`, `PATCH/DELETE /api/crm/pipelines/{id}/`, `POST .../{id}/delete-chunk/` (chunked pipeline deletion, 500 deals/chunk) | Pipeline (+ cascade stages/deals) |
| Manage Stage | `ManageStageModal` | Nested stage CRUD `/api/crm/pipelines/{id}/stages/` + `.../stages/reorder/` | Stage |
| Manage Users | `UserPipelineManager` | `GET .../assignment-stats/`, `POST .../trigger-assignment/` | CRM (bulk reassign) |
| Lead Settings | `LeadSettingsModal` | `PATCH /api/crm/pipelines/{id}/` (`mandatory_fields`, `custom_fields_enabled`) + `GET /api/contacts/track-fields/` | Pipeline, Contact (JSONB scan) |
| Payment Actions | *(nothing — stub card, no onClick handler wired yet)* | none | none |
| Deal Transforms (Lead Nurture) | `LeadNurtureModal` | see LeadNurtureModal section below | Pipeline, Stage, CRM, Contact |

**Lead Settings modal details:**
- System fields (`Name`, `Email`, `Phone`) are always mandatory and non-removable.
- Custom mandatory fields added/removed as pills; saved via `PATCH /api/crm/pipelines/{id}/`.
- "Track Fields" button calls `GET /api/contacts/track-fields/?pipeline_id=...` which scans contacts' `additional_data` JSONB keys in the pipeline's deals and auto-suggests new custom fields.
- Toggle for `custom_fields_enabled` disables/greys out custom field editing when off.

**CreatePipelineModal details:**
- Lists all pipelines, create/rename, inline delete.
- Deleting a large pipeline is chunked: `POST /api/crm/pipelines/{id}/delete-chunk/` with `{ limit: 500 }` per call until empty (mirrors the batch-deletion pattern used for import batches).

#### Related Components (not on Actions tab)
| Component | Purpose |
|-----------|---------|
| `MoveToStage.jsx` | Bulk-move selected deals between stages within a pipeline → `POST /api/crm/pipeline/bulk-move-to-stage/` |
| `crmlogs.jsx` | Per-deal activity log viewer + remarks (`POST /api/contacts/remarks/`), follow-up todo creation (`POST /api/calendar/todos/`), log fetch via `GET /api/crm/pipeline/{id}/activity/` |

### LeadNurtureModal.jsx — Lead Nurture Setup
*(See full detailed documentation below)*

### Additional Components

| Component | Path | Purpose |
|-----------|------|---------|
| `LeadSettingsModal.jsx` | `crm/components/` | Lead settings configuration |
| `ManageStageModal.jsx` | `crm/components/` | Stage CRUD modal |
| `UserPipelineManager.jsx` | `crm/components/` | Manage user access to pipelines |
| `CRMTable.jsx` | `crm/components/` | Table view for CRM data |
| `CRMFilter.jsx` | `crm/components/` | Advanced filtering UI |
| `DealStatusBadge.jsx` | `crm/components/` | Reusable status badge component |
| `CRMLayout.jsx` | `crm/components/` | Alternative layout wrapper |

### LeadNurtureModal.jsx — Lead Nurture Setup (Detailed)

A 3-step wizard modal for creating retarget pipelines:

**Step 1: Select Stages** — User picks source stages from the current pipeline.

**Step 2: Target Deals** — Server-side paginated deal list (50 per page).
- All deals from selected stages are implicitly selected.
- User manually unchecks deals → tracked in `deselectedDealIds` (Set).
- Top badge shows `Total leads: totalDealCount - deselectedDealIds.size`
- `totalDealCount` comes from `response.data.count` — static total unaffected by pagination.
- Search with 300ms debounce, filterable by name/email/phone.
- "Load More" fetches next page from server, appends to display.

**Step 3: Create Pipeline** — Name, description, optional department assignment.

**Submission Flow** (triggered by "Create & Retarget"):
1. Create new pipeline via `POST /api/crm/pipelines/` (with `pipeline_type` — retarget or sales depending on mode)
2. Fetch target pipeline's stages via `GET /api/crm/pipelines/{id}/stages/`
3. **If total selected > 100**: fetch all remaining pages from server
4. **If total selected > 100**: show progress bar (replaces right-side stepper indicators)
   - Phase 1: "Collecting deals..." (during remaining page fetches)
   - Phase 2: "Moving deals to retarget pipeline..." (during chunked submission)
5. Send deals in chunks to `POST /api/crm/pipeline/bulk-add-to-pipeline/` (copy mode) **or** `POST /api/crm/pipeline/bulk-move-deals/` (move mode, with `source_pipeline`)
   - Legacy path also supported: `POST /api/crm/pipeline/bulk-add-contacts/` with `source_pipeline` param
6. Backend moves/copies deals; move mode sets `priority="High"` and contact status `"Retarget"`
7. After submission, triggers bulk auto-assignment via `POST /api/crm/pipelines/{targetPipelineId}/trigger-assignment/`
8. Footer shows "Processing, please wait..." during submission
9. Calls `onPipelineCreated(newPipeline)` on success

**Field Value Filtering**: Step 2 supports filtering deals by custom field values via `GET /api/contacts/track-field-values/`.

**Progress Bar**: Only replaces the right-side stepper indicators (3 numbered circles), not the left-side title/description/total leads. Uses `w-48` fixed width with phase label, progress bar, and count.

---

## Key Behavioral Differences: Move vs Add

| Aspect | Move | Add (Copy) |
|--------|------|------------|
| **CRM ID** | **Stays the same** (updated row) | **New ID generated** (new row) |
| **Behavior** | Updates `pipeline_id` on existing row | Creates brand new CRM row |
| **Use case** | Same deal moves to new pipeline | Same contact purchases **another service** — different pipeline, different assigned user |
| **Contact** | Same `contact_id` (FK) | Same `contact_id` (FK) |
| **assigned_user** | **Reset to `None`** when pipeline changes | **Starts as `None`** (no inheritance) |
| **Activity log (source)** | "Pipeline Changed" — moved from/to | "Pipeline Changed" — copied to |
| **Activity log (target)** | "Pipeline Changed" — moved to | "Pipeline Added" — copied from |
| **Single endpoint** | `PATCH /api/crm/pipeline/{id}/` | `POST /api/crm/pipeline/{id}/copy-to-pipeline/` |
| **Bulk endpoint** | `POST /api/crm/pipeline/bulk-move-deals/` | `POST /api/crm/pipeline/bulk-add-to-pipeline/` |
| **Frontend single** | `SingleDealMove.jsx` | `SingleDealAdd.jsx` |
| **Frontend bulk** | `MultipleDealMove.jsx` | `MultipleDealAdd.jsx` |

---

## API Endpoints (Complete)

### CRM Deals — `/api/crm/pipeline/`

| Method | Path | Purpose | Details |
|--------|------|---------|---------|
| GET | `/api/crm/pipeline/` | List deals | Paginated, filterable by stage/pipeline/assigned_user/search |
| POST | `/api/crm/pipeline/` | Create deal | Auto-assignment + activity logs |
| PATCH | `/api/crm/pipeline/{id}/` | Update deal | Tracks stage/pipeline/assignment changes; resets user on pipeline change |
| DELETE | `/api/crm/pipeline/{id}/` | Delete deal | Creates "Deal Deleted" log before deletion |
| POST | `/api/crm/pipeline/create_deal/` | Create deal with contact lookup | — |
| POST | `/api/crm/pipeline/{id}/copy-to-pipeline/` | **Copy deal** to pipeline | Creates new CRM entry; no user inheritance |
| POST | `/api/crm/pipeline/bulk-add-to-pipeline/` | **Bulk copy** deals | Chunked; bulk create CRM + logs |
| POST | `/api/crm/pipeline/bulk-move-deals/` | **Bulk move** deals | Updates existing rows; resets assigned_user |
| POST | `/api/crm/pipeline/bulk-delete-deals/` | **Bulk delete** deals | Creates logs before deletion |
| POST | `/api/crm/pipeline/bulk-move-to-stage/` | **Bulk move** deals between stages (same pipeline) | Updates stage FK on existing rows |
| GET | `/api/crm/pipeline/{id}/activity/` | Deal activity logs | Paginated ContactLog feed for a deal |
| POST | `/api/crm/pipeline/bulk-add-contacts/` | Add contacts to pipeline | Lead Nurture (moves with High priority + Retarget) or legacy (creates new) |
| POST | `/api/crm/pipeline/bulk-add-from-batch/` | Add import batch to pipeline | Chunked; deduplicates; updates status to Lead |

### Pipelines — `/api/crm/pipelines/`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/crm/pipelines/` | List pipelines (staff-filtered) |
| POST | `/api/crm/pipelines/` | Create pipeline (auto-creates 6 stages) |
| GET | `/api/crm/pipelines/{id}/` | Pipeline detail |
| PATCH | `/api/crm/pipelines/{id}/` | Update pipeline |
| DELETE | `/api/crm/pipelines/{id}/` | Delete pipeline |
| POST | `/api/crm/pipelines/{id}/delete-chunk/` | Chunked pipeline deletion (500 deals per call, until empty) |
| GET | `/api/crm/pipelines/{id}/assignment-stats/` | Assignment breakdown + user loads |
| POST | `/api/crm/pipelines/{id}/trigger-assignment/` | Bulk-assign unassigned deals |

### Stages — `/api/crm/pipelines/{pipeline_pk}/stages/`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/crm/pipelines/{id}/stages/` | List stages |
| POST | `/api/crm/pipelines/{id}/stages/` | Create stage (auto-slug, collision-safe) |
| PATCH | `/api/crm/pipelines/{id}/stages/{stage_id}/` | Update stage (regenerates slug if name changed) |
| DELETE | `/api/crm/pipelines/{id}/stages/{stage_id}/` | Delete stage |
| POST | `/api/crm/pipelines/{id}/stages/reorder/` | Bulk reorder stages |

---

## Performance Optimizations

### 1. N+1 Query — ContactSerializer.get_pipelines (Fixed)
`CRMSerializer` used `ContactSerializer` which has a `SerializerMethodField('pipelines')`. This fired 1 extra query per deal on the reverse `crm_pipelines` relation. **Fixed** by replacing with `ContactBriefSerializer` that only exposes flat fields.

### 2. N+1 Query — UserSerializer → DepartmentSerializer → get_user_count (Fixed)
`UserSerializer` nested `DepartmentSerializer` which has a `SerializerMethodField('user_count')`. For each deal's assigned user, this queried all departments + COUNT queries. **Fixed** by replacing with `UserBriefSerializer`.

### 3. Bloated Payload — Pipeline Details Per Row (Fixed)
Removed `PipelineSerializer` from each deal row. The pipeline FK ID remains, but stages/departments are no longer serialized per deal.

### 4. Stage UUID Filter Bug (Fixed)
`stage_ids = [s for s in stages.split(',') if s.isdigit()]` silently dropped UUID stage IDs. Changed to `if s`.

### 5. Prefetch Cleanup
Removed unnecessary `.prefetch_related("contact__crm_pipelines__pipeline", ...)` since brief serializers don't trigger reverse relations.

### 6. Bulk Assignment Pre-computation
For bulk operations (bulk_add_to_pipeline, bulk_add_from_batch, bulk_move_deals), assignment is pre-calculated **in memory** (round-robin index tracking / least-loaded dict) rather than per-row database queries.

### 7. Bulk Activity Logs
All activity logs are created via `ContactLog.objects.bulk_create()` with `batch_size=1000` instead of individual `Model.objects.create()` calls.

### 8. Deduplication
- `bulk_add_from_batch`: Skips contacts already in target pipeline + skips duplicate activity logs
- `bulk_add_contacts` (legacy): Skips contacts already in target pipeline

---

## Known Limitations

- **No database indexes** on `Contact.name`, `Contact.email`, `Contact.phone` — `icontains` text searches are slow at scale
- **UUID primary keys** may cause index fragmentation at >100k rows
- **No polling/SSE/WebSocket** — the CRM page does not auto-refresh
- **No django-filter** — all filtering is manual in `get_queryset()`
- `PipelineSerializer` still uses `DepartmentSerializer` with `get_user_count()` — acceptable since it only fires on `GET /pipelines/` (list), not per deal
- **Copy-to-pipeline** (single/bulk) doesn't handle `single_user` assignment type (only round_robin and least_loaded)

---

## Frontend File Reference

| File | Role |
|------|------|
| `crm_frontend/src/modules/crm/pages/CRM.jsx` | Main Kanban page — all state, select mode, bulk actions, modals |
| `crm_frontend/src/modules/crm/components/KanbanBoard.jsx` | KanbanColumn droppable component with Load More |
| `crm_frontend/src/modules/crm/components/KanbanCard.jsx` | Draggable deal card with status/priority colors, 3-dot menu, select checkbox |
| `crm_frontend/src/modules/crm/components/SingleDealMove.jsx` | Modal — move one deal to another pipeline |
| `crm_frontend/src/modules/crm/components/SingleDealAdd.jsx` | Modal — copy one deal to another pipeline |
| `crm_frontend/src/modules/crm/components/MultipleDealMove.jsx` | Modal — move multiple deals with chunking + progress bar |
| `crm_frontend/src/modules/crm/components/MultipleDealAdd.jsx` | Modal — copy multiple deals with chunking + progress bar |
| `crm_frontend/src/modules/crm/components/LeadNurtureModal.jsx` | 3-step retarget wizard modal |
| `crm_frontend/src/modules/crm/components/CreatePipelineModal.jsx` | Pipeline creation modal |
| `crm_frontend/src/modules/crm/components/DealDetailsDialog.jsx` | Deal detail view with assignment, stage, value editing |
| `crm_frontend/src/modules/crm/components/SearchDialog.jsx` | Global search dialog |
| `crm_frontend/src/modules/crm/components/AddLeadDialog.jsx` | Quick lead add |
| `crm_frontend/src/modules/crm/components/AddLeadStructured.jsx` | Structured lead add with custom fields |
| `crm_frontend/src/modules/crm/components/PipelineSelector.jsx` | Pipeline dropdown selector |
| `crm_frontend/src/modules/crm/components/Actions.jsx` | Admin actions panel |
| `crm_frontend/src/modules/crm/components/ManageStageModal.jsx` | Stage CRUD modal |
| `crm_frontend/src/modules/crm/components/LeadSettingsModal.jsx` | Lead settings configuration |
| `crm_frontend/src/modules/crm/components/UserPipelineManager.jsx` | User-pipeline access management |
| `crm_frontend/src/modules/crm/components/CRMTable.jsx` | Table view for CRM data |
| `crm_frontend/src/modules/crm/components/CRMFilter.jsx` | Advanced filtering UI |
| `crm_frontend/src/modules/crm/components/DealStatusBadge.jsx` | Reusable status badge |
| `crm_frontend/src/modules/crm/components/CRMLayout.jsx` | Alternative layout wrapper |
| `crm_frontend/src/modules/crm/components/MoveToStage.jsx` | Bulk-move selected deals to another stage (same pipeline) |
| `crm_frontend/src/modules/crm/components/crmlogs.jsx` | Per-deal activity logs, remarks, and follow-up todos |
| `crm_frontend/src/components/ConfirmDeleteDialog.jsx` | Reusable delete confirmation with progress bar support |

## Backend File Reference

| File | Role |
|------|------|
| `crm_backend/crm/models.py` | Pipeline, Stage, CRM models |
| `crm_backend/crm/views.py` | CRMViewSet, PipelineViewSet, StageViewSet with all actions |
| `crm_backend/crm/serializers.py` | All CRM serializers (brief + full) |
| `crm_backend/crm/urls.py` | Router + nested router configuration |
| `crm_backend/core/pagination.py` | CustomPageNumberPagination |
| `crm_backend/core/settings.py` | Django + DRF config |
| `crm_backend/contacts/models.py` | Contact, ImportBatch, ContactLog (shared with CRM) |
