# CRM Payment Architecture — Per Pipeline

## Overview
Pipeline-scoped payment rules (`RecurringPaymentSchedule`) with per-deal payment ledger (`Payment`). Frontend enforces rule, backend validates and drives contact status badges (`Lead → Pending → Paid/Due`).

## Models

### `payments/models.py`
- **Payment** `contact?`, `crm?`, `amount`, `payment_for`, `payment_method (Any/UPI/Bank Transfer/Cash/Card/Net Banking)`, `remarks`, `invoice`, `recorded_by`
- **RecurringPaymentSchedule** `pipeline FK*`, `contact?` (null=pipeline-wide), `crm?`, `amount`, `payment_for`, `payment_method`, `cycle_period_days 1-365`, `cycle_count 1-60`, `completed_cycles`, `start_date`, `next_due_date`, `due_date?` (optional deadline), `status (active/paused/completed/cancelled)`, `remarks`

### `contacts/models.py`
- **Contact.status** `Lead, Prospect, Customer, Inactive, Retarget, Imports, Payment Pending, Paid, Due`
  - BE `Payment Pending` maps to FE `₹ Pending` purple, `Due` red, `Paid` green (`FaRupeeSign`)

### `crm/models.py`
- **CRM** `pipeline FK`, `contact FK`, `stage`, `assigned_user` — deal. Payment rule looked up via `crm.pipeline`.

## Backend

### Serializers `payments/serializers.py`
- `PaymentSerializer` validate: if active rule for `crm.pipeline` exists, enforce `payment_for==rule.payment_for`, `amount==rule.amount`, `payment_method==rule.payment_method` unless `Any`, `invoice` required, `cycle_count` limit, recurring `next_due` check (`last.created_at+cycle > today` → 400), one-time duplicate 400.
- `RecurringScheduleSerializer` fields include `due_date`, `total_amount(amount*cycle_count)`, validate `cycle 1-365`, `count 1-60`, `pipeline` required.

### Views `payments/views.py`
- `PaymentViewSet` `?contact &crm &pipeline` filter. `perform_create` creates `ContactLog Payment Recorded` + `_sync_pending_status(crm)`.
- `RecurringScheduleViewSet` `?pipeline &contact`. `perform_create` bulk `ContactLog Payment Rule Applied` for all `CRM` in pipeline; then bulk contact status update:
  - single + `today>=due_date`: unpaid → `Due`, paid → `Paid`
  - recurring: `today<first_due` → `Pending` for all; else `Due` (`_sync` handles per-deal after).
- `_sync_pending_status(crm)` per-deal status machine:
  - **single** `count>0`→`Paid`, `today>=due_date & count==0`→`Due` else `Lead` (resets `Paid/Due/Pending`→`Lead` if before due & no due)
  - **recurring** `first_due = due_date or start_date`, `curr_due = first_due+(count-1)*cycle`, `next_due = first_due+count*cycle`:
    - `count>=cycle_count`→`Paid`
    - `count==0`: `today<first_due`→`Pending` else `Due`
    - `0<count<cycle`: `today<=curr_due`→`Paid`, `today<next_due`→`Pending`, else `Due`
  - `no new_status` → reset `Paid/Due/Pending`→`Lead`

### CRM `crm/views.py` `CRMViewSet` — no payment status logic; status read via `contact_details.status` in `CRMSerializer` (`ContactBriefSerializer`).

### Migrations
- `contacts 0011,0012` add `Payment Pending/Paid/Due`
- `payments 0007` add `due_date`

## Frontend

### `PaymentActionsModal.jsx` (`pipeline_type=clients` only via `Actions.jsx`)
- Toggle `Recurring` OFF → single: `Amount, Method, Title, Due Date?` → POST `cycle 1, due_date|null, start today, remarks+[one-time]`
- ON → `Cycle days 1-365, Count 2-60, Start date, Due date?` → POST `due_date|null`
- Prefills existing active rule `GET /schedules/?pipeline`, shows `Total amount*cycle`, success/error, `Cancel/Save` (900ms close).

### `DealDetailsDialog.jsx`
- `GET /payments/schedules/?pipeline` → `pipelineRule`, `GET /payments/?crm` → ledger.
- `rulePayments = payments.filter(payment_for==rule.payment_for)`, `isRecurring`, `ruleCompleted`, `nextDueDate=last+cycle`, `ruleDisabled` (completed / before nextDue / already paid single)
- If rule: locked card `₹ amount · method · cycle` + `invoice` input → `POST /payments/` with fixed `amount/payment_for/method`, else generic form `amount/payment_for/method/remarks/invoice` hidden note `Generic record form hidden — active pipeline rule`.
- Ledger sub-tab `Pay/Ledger`, `totalPaymentsSum` as deal value.

### `KanbanCard.jsx` + `DealDetailsDialog.jsx` `STATUS_STYLES`
- `Pending/Payment Pending` purple + `FaRupeeSign`, `Due` red + `FaRupeeSign`, `Paid` emerald + `FaRupeeSign`, else blue `Lead`.

### `CRM.jsx` / `KanbanView` — `transformDeal` maps `contact_details.status` to card.

## API
- `GET/POST /api/payments/` `?crm &pipeline &contact`
- `GET/POST /api/payments/schedules/` `?pipeline &contact`
- `GET /api/crm/pipeline/?pipeline=id` → deals with `contact_details.status`
- `GET /api/contacts/logs/?crm&contact` audit

## Status Lifecycle
```
Lead ──(rule created, today<due)──→ Pending (recurring unpaid before due)
Pending ──(today>=due & unpaid)──→ Due (red) ──(pay)──→ Paid (green) ──(cycle end)──→ Pending (next cycle)
Single: Lead --pay--> Paid (immediate); Lead --due+unpaid--> Due
```
After due, paid-before-or-after → `Paid` green; overdue unpaid → `Due` red till paid.

## Enforcement
- UI hide generic form; server `PaymentSerializer.validate` blocks mismatched amount/for/method, cycle limit, early next-due, duplicate one-time.

## Gaps / TODO
- No cron for `next_due_date` auto-advance/completion; status only syncs on `schedule create` or `payment create`. Future due → pending flip only on next interaction.
- ~~Multiple active rules per pipeline~~ **RESOLVED**: single active pipeline-wide rule enforced at 3 layers — DB partial unique constraint `unique_active_pipeline_rule` (payments 0008), auto-cancel of prior rules in `perform_create/perform_update` (atomic, runs before save), and data migration that cancelled duplicates (kept newest per pipeline).
- `due_date` null → Lead (single) / uses `start_date` fallback (recurring).
- `PaymentViewSet` supports `?recorded_by=` filter (used by Payments page user filter).

## Files
`suite-backend/payments/{models,serializers,views,migrations}`, `suite-backend/contacts/models`, `suite-frontend/src/modules/crm/components/{PaymentActionsModal,DealDetailsDialog,KanbanCard,Actions}`
