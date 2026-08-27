# ByteHive Contacts & Ingestion System Architecture

## Overview
The ByteHive Contacts System is an industrial-grade ingestion engine designed for high-performance data management and resilient storage. It utilizes a hybrid schema approach to ensure that "no data is left behind" during bulk imports. It is fully integrated with the ByteHive CRM module for a complete customer lifecycle management solution.

---

## 🛠 Architectural Pillars

### 1. The 4-Stage Ingestion Pipeline (Frontend)
The system moves data through a modular transformer before it ever reaches the server:
- **Phase A: Upload**: Peer-to-peer file ingestion using local CSV parsing.
- **Phase B: Targeting**: User-defined column selection to strip noise from raw datasets.
- **Phase C: Matching**: A logic bridge that maps "Known Fields" (Name, Email, Phone) to the database while flagging "Unknown Fields" for the Hybrid Storage layer.
- **Phase D: Verification**: Real-time high-fidelity grid preview for final data auditing.

### 2. The Hybrid Storage Pattern (PostgreSQL / JSONB)
Unlike traditional CRMs that fail on unknown columns, ByteHive uses a **Hybrid Core**:
- **Structured Columns**: Core fields are stored in traditional PostgreSQL columns for low-latency indexing, searching, and server-side filtering.
- **Unstructured JSONB (`additional_data`)**: All columns that do not match the system schema are automatically bundled into a high-performance JSONB block. This ensures 100% data integrity for every CSV import without requiring database migrations.

### 3. Tactical API Bursts
- **Pattern**: `bulk-create`
- **Performance**: The frontend transformer bundles the entire dataset into a single mechanical payload.
- **Efficiency**: Reduces database transaction overhead by a factor of 100x compared to standard row-by-row creation.

### 4. Operational Dashboard
- **Server-Side Sync**: The repository uses debounced server-side searching to maintain speed regardless of dataset scale.
- **Archive Pagination**: High-efficiency sequence-based navigation for deep archive scanning.

### 5. CRM Integration (Full Pipeline Integration)
Contacts are fully integrated with the CRM pipeline system, with:
- **Bulk Add to CRM**: Add multiple contacts from an import batch or selected list directly to a CRM pipeline.
- **Automatic Stage Assignment**: New deals are added to the first stage of the selected pipeline.
- **Smart Deal Assignment**: Uses the pipeline's assignment strategy (round-robin, least-loaded, manual) to assign deals to eligible users from the pipeline's assigned departments.
- **Two-Way Sync**: Contacts show all associated deals, and deals show full contact details.

### 6. Audit & Activity Logging
Every action on a contact or deal is logged for full traceability:
- **ContactLog**: Tracks all contact/deal activities:
  - Imported
  - Pipeline Added
  - Stage Changed
  - Assignment Changed
  - Remark Added
- **ContactRemark**: User-defined notes/updates on contacts or deals, which automatically create an activity log entry.
- **Data Model**: Both logs include `user`, `contact`, `crm`, `activity_type`, `description`, and timestamps.

---

## 🎨 Professional Aesthetic
The system adheres to the **"Industrial Instrument"** design philosophy:
- **Materials**: `bg-zinc-900/30` technical gray backgrounds and `border-zinc-800` machined edges.
- **Lighting**: Centrally illuminated headers with high-blur backdrops (`backdrop-blur-xl`).
- **Density**: High-density scannable rows designed for data professionals.

---

## 🧊 Key Components

### Frontend Components
| Component | File | Responsibility |
|-----------|------|----------------|
| `ImportModal` | `contacts/components/ImportModal.jsx` | Orchestrates the 4-stage data transformation. |
| `Contacts.jsx` | `contacts/pages/Contacts.jsx` | The "Command Center" repository with server-synchronized telemetry, batch management, and bulk CRM operations. |
| `ContactsTable` | `contacts/components/tabs/ContactsTable.jsx` | Data grid for displaying contacts with search, filter, and selection capabilities. |
| `AddToCRMModal` | `contacts/components/AddToCRMModal.jsx` | Modal for selecting pipeline and stage to bulk-add contacts to CRM. |

### Backend Components
| Component | File | Responsibility |
|-----------|------|----------------|
| `ContactViewSet` | `contacts/views.py` | CRUD operations on contacts, search, filtering, bulk-create. |
| `ImportBatchViewSet` | `contacts/views.py` | Manage import batches, optimized deletion using raw SQL for large datasets. |
| `ContactLogViewSet` | `contacts/views.py` | Audit trail for all contact/deal activities. |
| `ContactRemarkViewSet` | `contacts/views.py` | User remarks/notes on contacts or deals. |
| `track-fields` | `contacts/views.py` | Scans contacts' `additional_data` JSONB keys (scoped to a pipeline's deals) so CRM Lead Settings can auto-suggest custom mandatory fields; companion endpoint `track-field-values` returns distinct values for filtering. |
| `CRMViewSet` | `crm/views.py` | Deal management with smart assignment strategies and activity logging. |
| `PipelineViewSet` | `crm/views.py` | Pipeline management with stage auto-creation and assignment strategies. |
| `StageViewSet` | `crm/views.py` | Manage pipeline stages, reordering, and dynamic slug generation. |
| `bulk-add-from-batch` | `crm/views.py` | CRM action to bulk-add contacts from an import batch to a pipeline. |

---

## 📊 Data Models

### Contact Model (`contacts/models.py`)
- **Core Fields**: `contact_id` (auto-generated unique ID: CON-1001, CON-1002...), `name`, `email`, `phone`, `status` (Lead, Prospect, Customer, Inactive)
- **Hybrid Storage**: `additional_data` (JSONB) for all unrecognized fields from imports
- **Relations**: `import_batch` (FK to ImportBatch), `source` (denormalized batch name for fast filtering)
- **Validation**: Requires `name` + either `email` or `phone`

### ImportBatch Model (`contacts/models.py`)
- **Fields**: `name` (user-defined import name), `contact_count` (cached count of contacts in the batch)
- **Purpose**: Groups contacts by import session for organization and bulk operations

### ContactLog & ContactRemark Models (`contacts/models.py`)
- **Log Fields**: `contact` (FK), `crm` (FK, optional), `user` (FK), `activity_type`, `description`, timestamps
- **Remark Fields**: `contact` (FK), `crm` (FK, optional), `user` (FK), `text`, timestamps
- **Purpose**: Full audit trail of all contact and deal activities

### CRM Integration Models (`crm/models.py`)
- **Pipeline**: Sales funnel configuration with assignment type (round-robin, least-loaded, manual)
- **Stage**: Kanban columns per pipeline, ordered, color-coded
- **CRM (Deal)**: Links Contact → Pipeline → Stage → User, with value, priority, and notes
- **Key Indexes**: For pipeline + stage, pipeline + user, creation date for fast queries

---

## 🚀 CRM Deal Assignment Strategies

### Round Robin
- Distributes deals sequentially to eligible users
- Remembers last assigned user to maintain order
- Skips users not in pipeline departments

### Least Loaded
- Assigns to user with fewest deals in the pipeline
- Recalculates load after each assignment for optimal distribution

### Manual
- Default option, no automatic assignment
- Admin or user explicitly assigns deals

---

## 📈 Performance Optimizations

### Backend
1. **Bulk Operations**: Bulk create contacts, deals, logs using `bulk_create` with batch sizes up to 1000
2. **Raw SQL for Batch Deletion**: Bypasses Django's slow object collector for large import batches using raw SQL
3. **Database Indexes**:
   - `crm_stage_pipeline_order_idx`: Fast stage ordering by pipeline
   - `crm_crm_pipelin_stage_idx`: Fast deals lookup by pipeline and stage
   - `crm_crm_pipelin_user_idx`: Fast deals lookup by pipeline and assigned user
   - `crm_crm_created_at_idx`: Fast deals ordering by creation date
4. **Query Optimization**: Extensive use of `select_related` and `prefetch_related` to minimize database trips

### Frontend
1. **Single API Call**: Instead of making N API calls (one per stage), makes 1 call to fetch all deals in a pipeline and groups locally
2. **Debounced Search**: Reduces server load during contact searching
3. **Pagination**: Efficient pagination for deep archive scanning
