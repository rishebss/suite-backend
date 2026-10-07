# CRM Payment Architecture — Per Pipeline

## Overview
Pipeline-scoped payment rules (`RecurringPaymentSchedule`) with a per-deal payment ledger (`Payment`). The frontend hides/presets rule values, the backend validates and drives contact status badges (`Lead → Payment Pending → Paid/Due`), and role-based scoping limits what staff can see or fetch.

Reading the system in three layers:
1. **Rule** — one active rule per pipeline defines *what* may be paid, *how much*, *by when*.
2. **Ledger** — every recorded `Payment` against a deal.
3. **Views** — CRM deal dialog (record a payment) and the Payments module (browse + drill into drawers).

## Models

### `payments/models.py`
- **Payment** `contact FK*`, `crm FK?`, `recorded_by?`, `amount`, `payment_for`, `payment_method (Any/UPI/Bank Transfer/Cash/Card/Net Banking)`, `invoice?`, `remarks?`
- **RecurringPaymentSchedule** `pipeline FK*`, `contact?` (null = pipeline-wide), `crm?`, `amount`, `payment_for`, `payment_method`, `cycle_period_days 1-365`, `cycle_count 1-60`, `completed_cycles`, `start_date`, `next_due_date`, `due_date?` (optional deadline), `status (active/paused/completed/cancelled)`, `remarks`
  - Partial unique constraint `unique_active_pipeline_rule` on `pipeline` where `status=active AND contact IS NULL`
  - `save()` seeds `next_due_date = start_date` when unset

### `contacts/models.py`
- **Contact.status** `Lead, Prospect, Customer, Inactive, Retarget, Imports, Payment Pending, Paid, Due`
  - BE `Payment Pending` → FE `₹ Pending` purple, `Due` red, `Paid` green (`FaRupeeSign`)

### `crm/models.py`
- **CRM** `pipeline FK`, `contact FK`, `stage`, `assigned_user` — the deal. Payment rules are looked up via `crm.pipeline`; **staff scoping is via `crm.assigned_user`** (deals are assigned, not contacts).

## Backend

### Serializers `payments/serializers.py`
- `PaymentSerializer.validate` — when an active rule exists for `crm.pipeline`, enforces:
  - `payment_for == rule.payment_for`
  - `amount == rule.amount`
  - `payment_method == rule.payment_method` unless the rule method is `Any`
  - `invoice` is required
  - `cycle_count` limit; one-time duplicate → 400
  - recurring early-payment gate (`last.created_at + cycle_period_days > today` → 400)
- `RecurringScheduleSerializer` — `due_date`, `total_amount (amount*cycle_count)`, validates `cycle_period_days 1-365`, `cycle_count 1-60`, `pipeline` required.
- `contact_details` on both serializers uses `crm.serializers.ContactBriefSerializer`, **not** `contacts.serializers.ContactSerializer`. The full serializer's `pipelines` field runs a query per row, which made the payments list and the contact drawer issue one extra query per payment (measured on 21 payments: 23 queries / 3.9 s → 2 queries / 0.3 s).

### Views `payments/views.py`

**`PaymentViewSet`**
- Filters: `contact`, `crm`, `pipeline` (CSV), `recorded_by` (CSV), `payment_method` (CSV), `page_size`
- Search: `search` alone → OR across `contact.name`, `payment_for`, `invoice`, `payment_method`, `crm.pipeline.name`
  - `search` + `search_field` → scoped to one field:
    | `search_field` | lookup |
    |---|---|
    | `contact` | `contact__name__icontains` |
    | `payment_for` | `payment_for__icontains` |
    | `invoice` | `invoice__icontains` |
    | `method` | `payment_method__icontains` |
    | `pipeline` | `crm__pipeline__name__icontains` |
    Unknown values fall back to the OR search.
- `perform_create` — `recorded_by=request.user`, `ContactLog "Payment Recorded"`, then `_sync_pending_status(crm)` (wrapped in a swallowing `try/except`).

**`RecurringScheduleViewSet`**
- Filters: `pipeline`, `contact`
- `perform_create` / `perform_update` — atomically cancel other active pipeline-wide rules on the pipeline *before* saving (the DB constraint would otherwise reject it), then bulk `ContactLog "Payment Rule Applied"` for every deal in the pipeline and a bulk contact-status update.

**`_sync_pending_status(crm)`** — per-deal status machine:
- **single**: `count>0` → `Paid`; `today>=due_date & count==0` → `Due`; otherwise reset `Paid/Due/Payment Pending` → `Lead`
- **recurring**: `first_due = due_date or start_date`, `curr_due = first_due+(count-1)*cycle`, `next_due = first_due+count*cycle`
  - `count>=cycle_count` → `Paid`
  - `count==0`: `today<first_due` → `Payment Pending` else `Due`
  - `0<count<cycle`: `today<=curr_due` → `Paid`, `today<next_due` → `Payment Pending`, else `Due`
- No resolved status → reset `Paid/Due/Payment Pending` → `Lead`

### Visibility & Roles (enforced in the API, not just the UI)

`payments/views.py` defines:
```python
def _restricted_to_own_deals(user):
    return (user.is_authenticated and user.role == "Staff" and not user.is_superuser)
```
- **Superadmin / Admin / `is_superuser`** → unrestricted (everything below).
- **Staff**:
  - `PaymentViewSet` → `qs.filter(crm__assigned_user=request.user)` — only payments on deals assigned to them.
  - `RecurringScheduleViewSet` → `qs.filter(pipeline__departments__in=request.user.departments.all()).distinct()` — mirrors `PipelineViewSet` department scoping.
- Consequence: a payment with `crm = NULL` has no assignee, so **staff never see it**.
- `CRMViewSet` (`crm/views.py`) exposes `?contact=` so deal lists can be scoped the same way (it already filters `assigned_user=user` for staff).

### CRM `crm/views.py` `CRMViewSet` — no payment status logic; status is read via `contact_details.status` in `CRMSerializer` (`ContactBriefSerializer`).

### Migrations
- `contacts 0011,0012` add `Payment Pending/Paid/Due`
- `payments 0007` add `due_date` + method choices
- `payments 0008` data cleanup (cancel duplicate active rules, keep newest) + `unique_active_pipeline_rule`

## Frontend

### Payments module `suite-frontend/src/modules/payments/`

**`pages/PaymentsPage.jsx`** — two tabs:
- **Logs** → `PaymentTable` (server-paginated ledger, 20/page, pipeline/method/user filters)
- **Rules** → `ScheduleTable` (rule cards; clicking one opens `PaymentActionsModal` in view/edit mode)

**`components/PaymentSearchModal.jsx`** — opens from the search button:
- Field selector dropdown (Contact / Payment For / Invoice / Method / Pipeline) → sends `search` + `search_field`
- **Owns its own search state** — searching here does **not** filter the payments table; it only builds the result list
- Each result row is clickable → opens the drawer for the currently selected field

**`components/PaymentTable.jsx`** — the ledger grid. The **Contact / Deal cell is clickable** and opens `ContactPaymentDetailDrawer` for that payment's contact (`onContactClick` → parent drawer state).

### Detail drawers (5 entry points, 3 components + shared shell)

`PaymentDrawerShell` (shared) — right-side panel following the calendar `UpdatesSidebar` pattern: `w-[min(420px,90vw)]`, backdrop `z-[1040]`, panel `z-[1050]`, `fadeIn` / `slideInRight`, coloured header icon chip, body `overflow-y-auto custom-scrollbar`, optional footer summary line, `EmptyState` (dashed border), Esc + backdrop close.
Also exports `PaymentRow`, `SectionLabel`, `EmptyState`; `paymentDrawerUtils.js` holds `fmtINR`, `STATUS_STYLES`, `STAGE_DOT`. No bold text is used in the drawers.

`PaymentRow` — **collapsible** record row:
- collapsed → amount (left) · date (right) · chevron
- expanded → Contact, Pipeline, Payment For, Invoice, Method

| Selected search field | Drawer | Shows |
|---|---|---|
| Contact | `ContactPaymentDetailDrawer` | status + source badges, identity rows (Email, Phone, **Total Amount**), **Payment Records** list in a bordered scroll container (`min-h-[260px] max-h-[340px]`) |
| Pipeline | `PipelinePaymentDetailDrawer` | pipeline type/assignment badges, Collected / Payments / Deals stats, active Payment Rule, stages, **Payments Recorded** list |
| Invoice / Payment For / Method | `PaymentFieldDetailDrawer` | single match → **Payment Details only** (Contact, Pipeline, Payment For, Invoice, Method, Date, Amount); multiple matches → summary rows + **Payment Records** list |

### `PaymentActionsModal.jsx` (`crm/components`, `pipeline_type=clients` only via `Actions.jsx`)
- Toggle `Recurring` OFF → single: `Amount, Method, Title, Due Date?` → POST `cycle_count 1, due_date|null, remarks + [one-time pipeline rule]`
- ON → `Cycle days 1-365, Count 2-60, Start, Due date?`
- Prefills the existing active rule via `GET /payments/schedules/?pipeline`, shows `amount × count`, view/edit/delete modes, 900ms success close.

### `DealDetailsDialog.jsx`
- `GET /payments/schedules/?pipeline` → `pipelineRule`, `GET /payments/?crm` → ledger
- `rulePayments = payments.filter(payment_for == rule.payment_for)`, `isRecurring`, `ruleCompleted`, `nextDueDate = last + cycle`, `ruleDisabled` (completed / before next due / single already paid)
- With a rule: locked card `₹ amount · method · cycle` + invoice input → `POST /payments/` with fixed `amount/payment_for/method`; the generic form is hidden
- Ledger sub-tab `Pay/Ledger`, `totalPaymentsSum` used as the deal value

### Status badges
`KanbanCard.jsx` + `DealDetailsDialog.jsx` `STATUS_STYLES`: `Payment Pending` purple + `FaRupeeSign`, `Due` red + `FaRupeeSign`, `Paid` emerald + `FaRupeeSign`, else blue `Lead`. `CRM.jsx` / `transformDeal` maps `contact_details.status` onto cards.

## API
- `GET/POST /api/payments/` — `?contact &crm &pipeline &recorded_by &payment_method &search &search_field &page_size &with_total` (scoped for staff)
  - `with_total=1` adds `total_amount` (SUM over the whole filtered set, not just the page) to the paginated response — used by the drawers so their collected figures stay exact while records page 20 at a time. Costs one extra query, so it is opt-in and only requested for page 1.
- `GET/POST /api/payments/schedules/` — `?pipeline &contact` (scoped for staff)
- `GET /api/crm/pipeline/` — `?contact` (new) + existing stage/pipeline/assigned_user filters (staff-scoped)
- `GET /api/crm/pipelines/{id}/` — pipeline detail (staff-scoped by department)
- `GET /api/contacts/{id}/`, `GET /api/contacts/logs/?crm&contact` — audit

## Status Lifecycle
```
Lead ──(rule created, today<due)──→ Payment Pending (recurring unpaid before due)
Payment Pending ──(today>=due & unpaid)──→ Due (red) ──(pay)──→ Paid (green) ──(cycle end)──→ Payment Pending
Single: Lead --pay--> Paid (immediate); Lead --due+unpaid--> Due
```
After due, paid-before-or-after → `Paid`; overdue unpaid → `Due` until paid.

## Enforcement
- UI hides the generic form and pre-fills rule values; the server `PaymentSerializer.validate` is the real gate (mismatched amount/for/method, cycle limit, early next-due, duplicate one-time, missing invoice).
- Single active pipeline-wide rule is enforced in 3 layers — DB partial unique constraint (payments 0008), atomic auto-cancel in `perform_create/perform_update`, and the 0008 data migration that cancelled duplicates.
- Row visibility is enforced in `get_queryset`, so staff cannot fetch other users' payments or rules by calling the API directly.

## Gaps / TODO
- **No tests** — `payments/tests.py` is an empty stub; the rule engine and `_sync_pending_status` are unverified by automated tests. `admin.py` is also empty (models unregistered).
- **No cron** — `next_due_date` / `completed_cycles` are never advanced and rules never auto-transition to `completed`. Status only re-syncs on `schedule create` or `payment create`.
- **Two different "next due" clocks** — the serializer gate uses `last.created_at + cycle_period_days`, while `_sync_pending_status` uses `rule.due_date or start_date + n*cycle`. They can disagree.
- **Silent failures** — `perform_create` wraps status sync, and the pipeline-wide status bulk-update, in `except Exception: pass`, so badges can silently drift from reality.
- **`PaymentActionsModal` ignores the recurring Start date** — the payload always sends `start_date = today`, discarding the picked `startDate`.
- **Rules list is not paginated** — `fetchSchedules()` is rendered directly into `ScheduleTable`, so only the first page (default 100) is shown.
- **Staff writes are not guarded** — reads are scoped, but a staff user can still POST a payment against another user's deal.
- **Contact profile endpoint unscoped** — `ContactViewSet` has no department/assignment scoping; staff reach it through a visible payment and the nested deals/payments are scoped.
- `due_date` null → `Lead` (single) / falls back to `start_date` (recurring).
- Seeded dev data can exceed the one-time rule (rule-compliant payments created via the API; extra records inserted directly with ORM).

## Files
`suite-backend/payments/{models,serializers,views,urls,admin,tests,migrations}`, `suite-backend/crm/views.py`, `suite-backend/contacts/models.py`,
`suite-frontend/src/modules/payments/{pages/PaymentsPage.jsx,components/{PaymentTable,ScheduleTable,PaymentSearchModal,PaymentDrawerShell,ContactPaymentDetailDrawer,PipelinePaymentDetailDrawer,PaymentFieldDetailDrawer}.jsx, components/paymentDrawerUtils.js, services/paymentsService.js}`,
`suite-frontend/src/modules/crm/components/{PaymentActionsModal,DealDetailsDialog,KanbanCard,Actions}.jsx`