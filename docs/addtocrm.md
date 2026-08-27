# Add to CRM — Chunked Import Failure Analysis

## The Problem

When importing a batch of contacts (e.g., 3000 contacts via Excel) and using **Add to CRM**, only the first chunk succeeds. The second chunk fails with:

```
AxiosError: Network Error
    at handleAddToCRM (ImportsTab.jsx:87)
    at handleConfirm (AddToCRMModal.jsx:52)
```

"Network Error" means the HTTP request never reached Django — it's a transport-level failure (connection refused / server unresponsive). This is **not** a 500 error with a JSON body.

### What Works

| Flow | Endpoint | Chunk Size | Works? |
|------|----------|------------|--------|
| Lead Nurture retargeting | `POST /api/crm/pipeline/bulk-add-contacts/` with `source_pipeline` | 100 | Yes |
| Delete batch | `POST /api/contacts/batches/{id}/delete-chunk/` | 1500 | Yes |
| Import Excel | `POST /api/contacts/bulk-create/` | N/A | Yes |
| **Add to CRM** | `POST /api/crm/pipeline/bulk-add-contacts/` **without** `source_pipeline` | **500** | **No (chunk 2+)** |

---

## Architecture

### Data Models

All models extend `Main` which uses **UUID primary keys** (not auto-increment integers):

`crm_backend/core/models.py`:
```python
class Main(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True
```

**Contact** (`crm_backend/contacts/models.py:34`):
```python
class Contact(Main):
    contact_id = models.CharField(max_length=50, unique=True, editable=False)
    name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    status = models.CharField(max_length=50, choices=CONTACT_STATUS, default="Lead")
    import_batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, null=True, blank=True, related_name="contacts")
```

**CRM** (`crm_backend/crm/models.py:86`):
```python
class CRM(Main):
    pipeline = models.ForeignKey(Pipeline, on_delete=models.CASCADE, related_name="deals", null=True, blank=True)
    stage = models.ForeignKey(Stage, on_delete=models.SET_NULL, related_name="deals", null=True, blank=True)
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="crm_pipelines")
    assigned_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    priority = models.CharField(max_length=20, choices=CRM_PRIORITY_CHOICES, default="Medium")
```

**ContactLog** (`crm_backend/contacts/models.py:96`):
```python
class ContactLog(Main):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="logs")
    crm = models.ForeignKey("crm.CRM", on_delete=models.CASCADE, null=True, blank=True, related_name="logs")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    activity_type = models.CharField(max_length=100)
    description = models.TextField()
```

**Pagination** (`crm_backend/core/pagination.py`):
```python
class CustomPageNumberPagination(PageNumberPagination):
    page_size_query_param = "page_size"
    max_page_size = 50000
```

---

## Backend: `bulk-add-contacts` Endpoint

**File:** `crm_backend/crm/views.py:625-809`

### Entry Point

```python
@action(detail=False, methods=["post"], url_path="bulk-add-contacts")
def bulk_add_contacts(self, request):
    pipeline_id = request.data.get("pipeline_id")
    contact_ids = request.data.get("contact_ids", [])
    source_pipeline = request.data.get("source_pipeline")
```

Two branches based on `source_pipeline`:

### Branch A: `if source_pipeline:` (WORKS — used by Lead Nurture)

```python
if source_pipeline:
    # MOVE existing deals from source pipeline to new pipeline
    moved_count = CRM.objects.filter(
        pipeline_id=source_pipeline, contact_id__in=contact_ids
    ).update(pipeline_id=pipeline_id, stage=first_stage, priority="High")

    Contact.objects.filter(id__in=contact_ids).update(status="Retarget")

    # Activity logs
    moved_deals = CRM.objects.filter(
        pipeline_id=pipeline_id, contact_id__in=contact_ids
    )
    log_entries = []
    for crm in moved_deals:
        log_entries.append(ContactLog(
            contact=crm.contact, crm=crm,
            activity_type="Pipeline Changed",
            description=f"Moved to retarget pipeline '{pipeline.name}' under stage '{...}'",
            user=request.user,
        ))
    ContactLog.objects.bulk_create(log_entries, batch_size=1000)
    return Response(...)
```

This branch only does **UPDATE** queries (on existing CRM rows) — no `bulk_create`. Chunk size is 100 in Lead Nurture.

### Branch B: `else:` (FAILS on chunk 2+ — used by Add to CRM)

```python
else:
    contact_ids_list = list(contact_ids)
    existing_ids = set(
        CRM.objects.filter(
            pipeline_id=pipeline_id, contact_id__in=contact_ids_list
        ).values_list("contact_id", flat=True)
    )

    new_contact_ids = [cid for cid in contact_ids_list if cid not in existing_ids]
    new_contacts = list(Contact.objects.filter(id__in=new_contact_ids))

    # Assignment logic (round_robin / least_loaded / manual)...

    crm_entries = []
    for contact in new_contacts:
        # build CRM objects...
        crm_entries.append(CRM(
            contact=contact,
            pipeline_id=pipeline_id,
            stage=first_stage,
            priority="Medium",
            assigned_user=assigned_user,
        ))

    CRM.objects.bulk_create(crm_entries, batch_size=1000)
    Contact.objects.filter(id__in=new_contact_ids).update(status="Lead")

    # Activity logs
    saved_crms = CRM.objects.filter(
        pipeline_id=pipeline_id, contact_id__in=new_contact_ids
    )
    log_entries = []
    for crm in saved_crms:
        log_entries.append(ContactLog(
            contact=crm.contact, crm=crm,
            activity_type="Pipeline Added",
            description=f"Added to pipeline '{pipeline.name}' under stage '{...}' (Retargeting/Bulk)",
            user=request.user,
        ))
        if crm.assigned_user:
            log_entries.append(ContactLog(...))
    ContactLog.objects.bulk_create(log_entries, batch_size=1000)
    return Response(...)
```

This branch does **significantly more work** per chunk:
1. Queries CRM for existing entries (dedup check)
2. Fetches Contact objects from DB into memory
3. Creates CRM model instances in memory
4. `bulk_create` — inserts CRM rows
5. `update` — updates contact statuses
6. Queries CRM again (to get IDs for logs)
7. Creates ContactLog model instances in memory
8. `bulk_create` — inserts ContactLog rows

---

## Frontend: Add to CRM Flow

### Step 1: User clicks "Add to CRM" from Import tab

**File:** `crm_frontend/src/modules/contacts/components/tabs/ImportsTab.jsx:65-96`

```javascript
const handleAddToCRM = async (pipelineId, stageId, onProgress) => {
    if (!batchForCRM) return;
    const CHUNK_SIZE = 500;
    try {
        onProgress({ phase: 'Fetching contacts...', current: 0, total: 0 });
        const res = await axios.get(`/api/contacts/?batch=${batchForCRM.id}&page_size=50000`);
        const contacts = res.data.results || res.data;
        const allIds = contacts.map(c => c.id);
        const total = allIds.length;
        const totalChunks = Math.ceil(total / CHUNK_SIZE);

        onProgress({ phase: 'Adding to CRM...', current: 0, total });

        for (let i = 0; i < totalChunks; i++) {
            const chunk = allIds.slice(i * CHUNK_SIZE, (i + 1) * CHUNK_SIZE);
            await axios.post('/api/crm/pipeline/bulk-add-contacts/', {
                pipeline_id: pipelineId,
                contact_ids: chunk,
            });
            onProgress({
                phase: 'Adding to CRM...',
                current: Math.min((i + 1) * CHUNK_SIZE, total),
                total,
            });
        }
    } catch (err) {
        console.error('Failed to add to CRM:', err);
        throw err;
    }
};
```

### Step 2: Modal calls handleAddToCRM

**File:** `crm_frontend/src/modules/contacts/components/AddToCRMModal.jsx:44-57`

```javascript
const handleConfirm = async () => {
    if (!selectedPipeline) return;
    setIsProcessing(true);
    setProcessingError(null);
    try {
        const firstStage = selectedPipeline.stages?.sort((a, b) => a.order - b.order)[0];
        await onConfirm(selectedPipeline.id, firstStage?.id, setProgress);
        onSuccess?.(selectedPipeline.id);
        onClose();
    } catch (err) {
        console.error('Failed to add to CRM:', err);
        setProcessingError('Failed to add contacts. Please try again.');
    }
};
```

### Footer: Shows progress bar or error state

**File:** `crm_frontend/src/modules/contacts/components/AddToCRMModal.jsx:209-261`

```javascript
{(isProcessing || processingError) && contactCount >= 500 ? (
    <div className="w-full space-y-2">
        <div className="flex items-center justify-between">
            <span className="text-[10px] text-white/40">
                {processingError ? `${progress.phase} — Failed` : progress.phase}
            </span>
            <span className="text-[10px] font-mono text-white/20">
                {progress.total > 0 ? `${progress.current} / ${progress.total}` : ''}
            </span>
        </div>
        <div className="w-full h-1.5 bg-zinc-900 rounded-full overflow-hidden">
            <div className={cn("h-full rounded-full transition-all", processingError ? "bg-red-500" : "bg-blue-500")}
                style={{ width: progress.total > 0 ? `${Math.round((progress.current / progress.total) * 100)}%` : '0%' }}
            />
        </div>
        {processingError && (
            <p className="text-[10px] text-red-400 text-center">{processingError}</p>
        )}
    </div>
) : isProcessing ? (
    // spinner for <500 contacts
) : (
    // Cancel + Confirm Export buttons
)}
```

---

## What's Been Fixed / Tried

### Fix 1: Nested Subquery → Flat ID List

**Problem:** The else branch used queryset chaining that created deeply nested Postgres subqueries.

**Before (original code):**
```python
contacts = Contact.objects.filter(id__in=contact_ids)
existing_ids = CRM.objects.filter(
    pipeline_id=pipeline_id, contact__in=contacts  # subquery: contact_id IN (SELECT id FROM contacts WHERE id IN (...))
).values_list("contact_id", flat=True)
new_contacts = contacts.exclude(id__in=existing_ids)  # triple-nested subquery
```

**After (current code):**
```python
contact_ids_list = list(contact_ids)
existing_ids = set(
    CRM.objects.filter(
        pipeline_id=pipeline_id, contact_id__in=contact_ids_list  # flat IN clause
    ).values_list("contact_id", flat=True)
)
new_contact_ids = [cid for cid in contact_ids_list if cid not in existing_ids]
new_contacts = list(Contact.objects.filter(id__in=new_contact_ids))  # flat IN clause
```

This doesn't fix the issue — the `bulk-add-from-batch` endpoint (which works fine) already used flat lists.

### Fix 2: Removed Dead Code

Removed ~30 lines of unreachable code after `return Response` in the `source_pipeline` branch (lines 690-720). The dead code referenced an undefined variable `source_deals` and would crash with `NameError` if ever reached.

### Fix 3: React 18 Progress Bar Batching

**Problem:** When an error occurred, `setIsProcessing(false)` was called in the modal's catch block, hiding the progress bar. React 18's automatic batching could combine the last `setProgress` and `setIsProcessing(false)` into a single render, making the progress appear to jump from 0 to hidden.

**Fix:** Added `processingError` state — keeps progress bar visible (turns red) when error occurs, instead of hiding it:
```javascript
const [processingError, setProcessingError] = useState(null);
// On error:
setProcessingError('Failed to add contacts. Please try again.');
// Previously: setIsProcessing(false);
```

### Fix 4: Reduced Chunk Size from 1500 → 500

Changed `CHUNK_SIZE` in `ImportsTab.jsx:67` from 1500 to 500, and the progress bar threshold in `AddToCRMModal.jsx:211` from 1500 to 500.

The Lead Nurture flow uses chunk size 100 and works fine. But even at 500, the Add to CRM still fails on chunk 2+.

### Fix 5: Initial Progress Value

Changed `onProgress({ phase: 'Adding to CRM...', current: 1, total })` → `current: 0` to avoid misleading initial progress readout.

---

## Suspected Root Cause

The error is `AxiosError: Network Error` — the HTTP request **fails at the TCP level**, meaning Django never receives it. Likely causes:

### Hypothesis A: Django Auto-Reloader Restart (Windows)

`python manage.py runserver` uses a **polling file watcher** on Windows (checks file mtimes every ~1 second). The first chunk takes significant time (500 contacts × 3 model operations). During this window:

1. Something touches a `.py` file (editor autosave, antivirus, `.pyc` compilation, git status)
2. The auto-reloader detects the change and schedules a restart
3. The first request's response makes it out before the restart
4. The second request arrives during server restart → connection refused → "Network Error"

**Test:** Run with `python manage.py runserver --noreload` to disable auto-reloading. If this fixes it, the hypothesis is confirmed.

### Hypothesis B: Database Connection Pool Exhaustion

Neon Postgres free tier has strict connection limits. If connections aren't released between chunks, the second request can't acquire a connection.

### Hypothesis C: Memory/Socket Exhaustion

The else branch creates 500 Contact objects, 500 CRM objects, and 500-1000 ContactLog objects in memory per chunk. Combined with JSON serialization of the response, this could temporarily exhaust resources on a constrained dev server.

### Hypothesis D: Request Queue / Worker Saturation

`manage.py runserver` is single-threaded by default on some configurations. If the first request blocks the worker for too long, the second request can't be accepted.

---

## Key Differences from Working Flows

| Aspect | Lead Nurture (works) | Add to CRM (fails) |
|--------|---------------------|-------------------|
| Branch | `if source_pipeline:` (UPDATE) | `else:` (bulk_create) |
| Operations per chunk | 2 queries (UPDATE + bulk_create logs) | 5 queries (SELECT + SELECT + bulk_create + UPDATE + bulk_create logs) |
| Chunk size | 100 | 500 (was 1500) |
| DB impact per chunk | Light (UPDATE existing rows) | Heavy (INSERT 500 CRM + 500-1000 ContactLog rows) |

---

## Files Referenced

| File | Lines | Purpose |
|------|-------|---------|
| `crm_backend/crm/views.py` | 625-809 | `bulk-add-contacts` endpoint |
| `crm_backend/crm/models.py` | 86-124 | CRM model definition |
| `crm_backend/contacts/models.py` | 34-93 | Contact model (UUID PK) |
| `crm_backend/contacts/models.py` | 96-119 | ContactLog model |
| `crm_backend/contacts/views.py` | 37-56 | `delete-chunk` endpoint (works) |
| `crm_backend/core/models.py` | 1-12 | Main abstract model (UUID PK) |
| `crm_backend/core/pagination.py` | 1-6 | Pagination config (max 50000) |
| `crm_frontend/.../ImportsTab.jsx` | 65-96 | `handleAddToCRM` chunking logic |
| `crm_frontend/.../AddToCRMModal.jsx` | 44-57, 209-261 | Modal with progress bar + error state |
| `crm_frontend/.../LeadNurtureModal.jsx` | 260-302 | Working reference (chunk size 100, source_pipeline) |
