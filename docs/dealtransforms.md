# Deal Transforms — Architecture & Usage

## Overview

Deal Transforms is a 4-step wizard (`LeadNurtureModal.jsx`) for bulk-operating on deals across pipelines. It supports three actions: **Retarget**, **Add to Pipeline**, and **Move to Pipeline**. Simpler single-step alternatives (`MultipleDealMove.jsx`, `MultipleDealAdd.jsx`) exist for quick operations from the KanbanBoard's select mode.

---

## Step Structure

| Step | Title | Purpose |
|------|-------|---------|
| 1 | Select Criteria | Choose **Stages** (multi-select) OR **Field Value** (single key-value) |
| 2 | Target Deals | Server-paginated deal list (50/page) with search and deselect |
| 3 | Choose Action | Select **Retargeting**, **Add to Pipeline**, or **Move to Pipeline** |
| 4 | Pipeline Setup | Pick existing pipeline or create new one, configure assignment |

---

## Step 1 — Select Criteria

Two mutually exclusive tabs sit in the subheader pill toggle:

### Tab A: Select Stages (multi-select)

- Grid of stage cards, 2 per row, matching the pipeline's stages
- Click toggles selection (multi-select)
- Each card shows a check indicator when selected
- Gradient overlay on hover/selected (`bg-blue-500/10` + `from-blue-500/0 via-blue-500/0 to-blue-500/5`)
- "Next" requires at least one stage selected

### Tab B: Select Fields (single key-value)

Lists all fields from `pipeline.mandatory_fields`:

**System Fields** (`Name`, `Email`, `Phone`):
- Rendered as muted, non-interactive cards with `opacity-40` and a "System" badge
- Not queryable — they're direct DB columns, not in `additional_data`
- No expand, no chevron, no selection

**Custom/Additional Fields**:
- Rendered as expandable cards with a chevron and selection count badge
- Clicking a field card expands its value distribution dropdown
- Each value row shows:
  - Radio circle indicator (single-select — `rounded-full border-2`, dot when active)
  - Value name
  - Occurrence count
- Only **one** value can be selected across **all** fields
- Clicking the same value again deselects it
- "Next" requires a field value selected
- Expanded dropdown caps at 7 rows (`max-h-[280px]`) with scroll

#### State
```javascript
const [selectedFilter, setSelectedFilter] = useState(null);
// Shape: { field: "Payment Status", value: "Paid" }
const [expandedField, setExpandedField] = useState(null);
const [fieldValues, setFieldValues] = useState({});
// Shape: { "Payment Status": { field, total: 165, values: [{ value: "Paid", count: 120 }, ...] } }
const [loadingValues, setLoadingValues] = useState(null);
```

---

### LeadSettingsModal — Configuring Fields

The `LeadSettingsModal.jsx` manages which fields appear in the Select Fields tab via `pipeline.mandatory_fields`:

- **System fields** (`Name`, `Email`, `Phone`) — always present, non-removable
- **Custom fields** — user-defined, added manually or via **Track Fields**
- **Toggle**: `custom_fields_enabled` — when off, custom fields are disabled in the modal and the Select Fields tab gets a tooltip ("Custom field not enabled")

#### Track Fields Button

- Positioned inline with "Configured Fields" label (right-aligned)
- Calls `GET /api/contacts/track-fields/?pipeline_id=X`
- Deduplicates against system fields + existing custom fields
- Appends tracked field names as new custom field pills

**Backend** — `ContactViewSet.track_fields`:
```sql
SELECT DISTINCT jsonb_object_keys(c.additional_data)
FROM contacts_contact c
JOIN crm_crm deal ON deal.contact_id = c.id
WHERE deal.pipeline_id = %s
  AND c.additional_data IS NOT NULL
  AND c.additional_data != '{}'::jsonb
```

Filters out system field names (`name`, `email`, `phone`, `status`, `contact_id`, `source`, `id`, `created_at`, `updated_at`).

---

## Step 1 → Step 2 — Data Flow

### When using Stage Selection
`fetchDeals` sends:
```
GET /api/crm/pipeline/?pipeline=<id>&stages=<id1,id2>&page=1&page_size=50
```
Backend filters by `pipeline_id` AND `stage_id__in`.

### When using Field Value Selection
`fetchDeals` sends:
```
GET /api/crm/pipeline/?pipeline=<id>&additional_field=Payment%20Status&additional_value=Paid&page=1&page_size=50
```
Backend filters by `pipeline_id` AND `contact__additional_data__contains={field: value}`.

**Backend** — `CRMViewSet.get_queryset`:
```python
additional_field = self.request.query_params.get("additional_field")
additional_value = self.request.query_params.get("additional_value")

if additional_field and additional_value:
    qs = qs.filter(
        contact__additional_data__contains={additional_field: additional_value}
    )
```

The two filtering modes are independent — only one set of params is sent based on `activeTab`.

---

## Step 2 — Target Deals

- Server-paginated list (50 per page)
- All fetched deals are implicitly selected
- Users manually uncheck deals → tracked in `deselectedDealIds` (a `Set`)
- Top badge shows `Total leads: totalDealCount - deselectedDealIds.size`
- `totalDealCount` comes from `response.data.count`
- Search with 300ms debounce, filterable by name/email/phone
- "Load More" fetches next page, appends to display

---

## Step 3 — Choose Action

Three mutually exclusive action cards with radio indicators:

| Action | Description | Backend Endpoint | Behavior |
|--------|-------------|-----------------|----------|
| **Retargeting** (default) | Move deals into retarget pipeline, High priority, contact status → "Retarget" | `bulk-add-contacts` with `source_pipeline`, `priority: "High"` | Updates `pipeline_id` on existing CRM rows, resets `assigned_user`, sets priority=High, sets contact status=Retarget |
| **Add to Pipeline** | Copy contacts into pipeline without altering existing deals. Creates new CRM entries | `bulk-add-to-pipeline` with `deal_ids` | Creates fresh CRM entries, preserves contact info, priority preserved from source. Auto-assigns if pipeline strategy is round_robin/least_loaded |
| **Move to Pipeline** | Move the deal to a new pipeline. Same CRM ID preserved, `assigned_user` reset. No status/priority change | `bulk-move-deals` with `deal_ids` + `pipeline_id` | Updates `pipeline_id` on existing CRM rows, sets `assigned_user=None`, preserves priority and contact status |

---

## Step 4 — Pipeline Setup

### Pipeline Resolution

All three actions share the same pipeline selection UI:
- **Pipeline list** displayed in a `grid grid-cols-2 gap-2` with count inline: `Available Sales Pipelines: N`
- **"+ New" button** toggles a create form (pipeline name + description)
- Pipelines with `custom_fields_enabled=true` are **disabled** with a tooltip ("Cannot select custom field enabled pipeline")

Pipeline type on create:
- `retarget` for Retargeting action (so the pipeline appears in retarget pipeline lists)
- Not set (null/default) for Add/Move actions

### Assignment

#### New Pipeline (clicked "+ New")
- Department group selection (toggle shows searchable dropdown)
- Assignment strategies: Single User, Round Robin (Least Loaded available in backend but not exposed in UI)
- After moving deals, calls `POST /api/crm/pipelines/{id}/trigger-assignment/` if strategy is not manual

#### Existing Pipeline (selected from list)
- Automatically reads the pipeline's own `assignment_type`
- Auto-triggers assignment for `round_robin` / `least_loaded` strategies (no explicit trigger for `single_user` since target user is unknown)
- No assignment UI shown (pipeline already configured)

### Submission Flow

1. **Resolve target pipeline**: existing ID or create new via `POST /api/crm/pipelines/`
2. **Fetch deals** from source in a drain loop (page=1, page_size=500, re-fetches until empty):
   - **Move/Retarget**: source naturally drains since deals are removed from source on each chunk — re-fetching page 1 returns fresh deals
   - **Add**: source never drains (deals are copied, not moved), so the frontend sends `exclude_pipeline_id` (target pipeline ID) on each GET — the backend filters out contacts that already have a CRM row in the target pipeline, creating a natural drain
3. **Send action-specific API call** in chunks of 500 (iterates page 1 until all deals exhausted):
   - Retarget: `bulk-add-contacts` with `source_pipeline`
   - Add: `bulk-add-to-pipeline` with `deal_ids`
   - Move: `bulk-move-deals` with `deal_ids` + `stage_id`
4. **Auto-assign** if applicable (new pipeline with non-manual strategy, or existing pipeline with round_robin/least_loaded)
5. Progress bar shown during processing

---

## API Endpoints

### Backend — Contact Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/contacts/track-fields/` | Return unique `additional_data` keys from contacts in a pipeline |
| GET | `/api/contacts/track-field-values/` | Return value distribution for a specific field key |

**`track-field-values` params**: `field` (required), `pipeline_id` (optional)

Query:
```sql
SELECT c.additional_data->>%s AS val, COUNT(*) AS cnt
FROM contacts_contact c
JOIN crm_crm deal ON deal.contact_id = c.id
WHERE deal.pipeline_id = %s
  AND c.additional_data ? %s
GROUP BY val ORDER BY cnt DESC
```

Response:
```json
{
  "field": "Payment Status",
  "total": 165,
  "values": [
    { "value": "Paid", "count": 120 },
    { "value": "Not Paid", "count": 45 }
  ]
}
```

### Backend — CRM Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/crm/pipeline/` | List deals, filterable by pipeline/stages/additional_field/exclude_ids/exclude_pipeline_id |
| POST | `/api/crm/pipeline/bulk-add-contacts/` | Move deals (update pipeline_id). Optional: `priority`, `skip_contact_status_update` |
| POST | `/api/crm/pipeline/bulk-add-to-pipeline/` | Copy deals to pipeline (new CRM entries). Preserves priority. Auto-assigns if pipeline has round_robin/least_loaded |
| POST | `/api/crm/pipeline/bulk-move-deals/` | Move deals to pipeline (update pipeline_id). Resets `assigned_user=None`. Takes `deal_ids`, `pipeline_id`, `stage_id` |
| POST | `/api/crm/pipeline/bulk-delete-deals/` | Bulk delete CRM entries with logging |

### Backend — Pipeline Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/crm/pipelines/{id}/trigger-assignment/` | Assign unassigned deals using pipeline's strategy. Accepts `strategy`, `target_user_id` (for single_user) |

---

## Action Comparison

| Aspect | Retarget | Add | Move |
|--------|----------|-----|------|
| **Operation** | MOVE (update pipeline_id) | COPY (new CRM entries) | MOVE (update pipeline_id) |
| **Priority** | Set to "High" | Preserved from source | Preserved from source |
| **Contact Status** | Changed to "Retarget" | Unchanged | Unchanged |
| **assigned_user** | Reset to None | Depends on pipeline strategy (None / round_robin / least_loaded) | Reset to None |
| **Deal IDs** | Same IDs preserved | New IDs created | Same IDs preserved |
| **Backend Endpoint** | `bulk-add-contacts` | `bulk-add-to-pipeline` | `bulk-move-deals` |
| **Use Case** | Retargeting campaign | Cross-pipeline listing | Pipeline reorganization |

---

## Related Components

### `MultipleDealMove.jsx` & `MultipleDealAdd.jsx`

Single-step modals accessible from KanbanBoard's select mode. Simpler than LeadNurtureModal:
- Receive pre-selected `dealIds` as props (no dynamic fetching or pagination)
- Show pipeline list with simple name-only create form (no departments/assignment strategy)
- Chunk via `Array.slice()` in a `for` loop (no API pagination needed)
- **No trigger-assignment call** — deals land unassigned unless the pipeline's backend auto-assigns (bulk-add-to-pipeline auto-assigns for round_robin/least_loaded; bulk-move-deals always resets to None)

### Component Map

| Component | Path | Purpose |
|-----------|------|---------|
| `LeadNurtureModal.jsx` | `crm/components/` | 4-step transform wizard |
| `MultipleDealMove.jsx` | `crm/components/` | Quick single-step move from KanbanBoard |
| `MultipleDealAdd.jsx` | `crm/components/` | Quick single-step add from KanbanBoard |
| `LeadSettingsModal.jsx` | `crm/components/` | Configure mandatory fields + Track Fields |
| `SingleDealMove.jsx` | `crm/components/` | Single deal move from KanbanCard context menu |
| `SingleDealAdd.jsx` | `crm/components/` | Single deal add from KanbanCard context menu |
| `AddToCRMModal.jsx` | `contacts/components/` | Add contacts from imports to CRM pipeline |
| `Tooltip` | `components/ui/tooltip.jsx` | Tooltip for disabled state (custom fields not enabled) |

---

## Known Limitations & Edge Cases

1. **Field value filter matches exact values** — `__contains` uses JSONB containment, which is exact for strings but not for partial matches
2. **Single-select only** — only one field + one value can be active at a time across the entire wizard
3. **No combined mode** — stages and field value cannot be used together; they are mutually exclusive paths
4. **System fields are not queryable** for value distribution — they're direct DB columns, not keys in `additional_data`
5. **Keys with special characters** — `additional_data` keys with spaces or special characters work via `->>` operator
6. **Contact dedup on move** — If a contact has multiple deals in the source pipeline, all move together since the API filters by `contact_id__in`. The UI shows individual deals, but the backend moves by contact.
7. **Pagination** — The `/api/crm/pipeline/` list endpoint works with page > 1 (used by KanbanBoard's Load More) but the transform loops always use `page: 1` for simplicity. Move/Retarget rely on the source draining naturally (deals removed from source on each POST). Add uses the `exclude_pipeline_id` query param to filter out contacts already in the target pipeline — a DB-level NOT EXISTS subquery, so the drain is handled server-side without frontend ID tracking.
8. **Existing pipeline assignment** — When using existing pipelines, only `round_robin` and `least_loaded` strategies auto-trigger. `single_user` requires a target user ID not available from pipeline selection alone; user must create a new pipeline to configure single_user assignment.
9. **Custom field pipelines disabled** — Pipelines with `custom_fields_enabled=true` cannot be selected as target in step 4; a tooltip explains the restriction.
