# Calendar Architecture

## Overview

The calendar module manages 4 types of calendar entries: **Tasks**, **Events**, **Follow-ups**, and **Meetings**. All types share a single database model (`CalendarTodo`) with type-specific behavior driven by the `todo_type` field.

---

## Data Model (`CalendarTodo`)

### Fields

| Field | Type | Used By | Purpose |
|-------|------|---------|---------|
| `id` | UUID (PK) | All | Auto-generated unique ID |
| `user` | FK→User | All | Creator of the entry |
| `todo_type` | CharField(20) | All | `task`, `event`, `followup`, `meeting` |
| `title` | CharField(255) | All | Display title |
| `description` | TextField | All | Detailed notes |
| `priority` | CharField(10) | Task | `low`, `medium`, `high` |
| `start` | DateTimeField | All | Deadline (task), date/time (event/followup/meeting) |
| `end` | DateTimeField | Event | End of event range (optional) |
| `contact` | FK→Contact | Follow-up | Linked contact |
| `status` | CharField(20) | All | Type-specific status values |
| `hold_reason` | TextField | Task | Why task was put on hold |
| `extension_request` | TextField | Task | Text requesting deadline extension |
| `completion_remarks` | TextField | Task, Follow-up | Notes on completion |
| `followup_cancellation` | TextField | Follow-up | Reason for cancellation |
| `followup_failed` | TextField | Follow-up | Reason follow-up failed |
| `location` | CharField(255) | Meeting | Venue or meeting link |
| `assigned_to` | FK→User | Task, Follow-up | Assignee |
| `created_at` | DateTime | All | Auto-set on creation |
| `updated_at` | DateTime | All | Auto-updated |

### MeetingAttendee (separate model)

Many-to-many relationship between meetings and users.

---

## Type-Specific Workflows

### 1. Task (`todo_type: "task"`)

**Statuses:** `assigned`, `progress`, `completed`, `canceled`, `on_hold`, `overdue`, `approved`

**Creation:**
- Required: Task Name, Deadline
- Optional: Description, Priority, Assign To
- Status defaults to auto-calculated by `save()` and `to_representation()`

**Auto-status (written on save + overridden on read):**
- `overdue` is NOT available in the status dropdown — it's auto-set only (same pattern as `failed` for follow-ups)
- If `start < now` and status NOT in `(completed, on_hold, approved, canceled)` → auto-set to `overdue`
- If `status == "overdue"` and `start > now` → auto-revert to `assigned`

**Status update cleanup (serializer `update`):**
- Leaving `on_hold` → `hold_reason` cleared
- Leaving `overdue` → `extension_request` cleared
- Leaving `completed` → `completion_remarks` cleared
- Changing `start` when `extension_request` exists → `extension_request` cleared

**UI (UpdateTaskModal):**
- Permission tiers:
  - `isAdmin && isCreator`: Full edit (title, description, priority, assigned_to, deadline)
  - `isCreator` (non-admin): Can edit deadline + status
  - Assignee (non-creator, non-admin): Can edit status only
  - Others: Read-only
- Mini PATCH flows: hold reason, extension request, completion remarks are sent as separate PATCH calls before the main form save

---

### 2. Event (`todo_type: "event"`)

**Statuses:** `upcoming`, `live`, `cancelled`, `ended`

**Creation (AddEventModal → Event tab):**
- Required: Event Name, Description, Event Date
- Optional: Status, Single Day toggle, End Date
- Save button disabled until title, start date, and description are filled

**Single Day toggle:**
- When ON: `end` is auto-set to `23:59:59` of the event date; End Date input is disabled
- When OFF: User can manually set an End Date for multi-day events
- Toggling ON resets start time to `00:00` (local time, no UTC conversion)
- Toggle is a switch component (not checkbox) placed inline with label

**Auto-status (written on save + overridden on read):**
- `cancelled` is never auto-overridden
- With `end` date:
  - `end < now` → `ended`
  - `start <= now <= end` and status is NOT manually `ended` → `live`
  - `start > now` → `upcoming`
- Without `end` date:
  - `start < now` and status is NOT manually `ended` → `ended`
  - else → `upcoming`
- Admin/creator manually setting status to `ended` is preserved (won't revert to `live`)

**Visibility:**
- ALL events are visible to ALL authenticated users in the calendar
- Backend query: `Q(todo_type="event")` is added to every user's base queryset

**Range overlap (multi-day events):**
- Events appear on ALL days between `start` and `end` (inclusive)
- Calendar grid dots: `eachDayOfInterval` in frontend
- EventsPanel/day queries: backend uses `Q(start__lt=end, end__isnull=False, end__gte=start)` for events
- This only applies to `todo_type="event"` — other types use start-only matching

**UI (UpdateEventModal):**
- Creator and Admin/Superadmin can edit all fields + delete
- Others: read-only (fields disabled, no banner message)
- Delete button: visible to both creator and admins
- Header: "Event Update" for editors, "Event" for read-only
- Status dropdown: `upcoming` and `cancelled` disabled when status is `live` or `ended`

---

### 3. Follow-up (`todo_type: "followup"`)

**Statuses:** `follow_up`, `failed`, `complete`, `cancelled`

**Creation (AddEventModal → Follow-up tab):**
- Required: Title, Pipeline, Assign To, Contact, Follow-Up Date
- Optional: Notes, Status
- Status defaults to `follow_up`
- Contact dropdown disabled until Pipeline and Assign To are selected
- Contacts load server-side filtered by CRM deals assigned to the assigned user (`?assigned_user=ID` or `?search=term`)
- Admin/Superadmin users see all contacts regardless of CRM assignment

**Auto-status (written on save + overridden on read):**
- If `start < now` and status is `follow_up` → auto-set to `failed`
- `failed` is NOT available in the status dropdown — it's auto-set only

**Status update cleanup (serializer `update`):**
- Leaving `cancelled` → `followup_cancellation` cleared
- Leaving `failed` → `followup_failed` cleared
- Leaving `complete` → `completion_remarks` cleared

**UI (UpdateFollowUpModal):**
- **Creator view (canEdit):** Full edit form with all fields. Save button requires title, pipeline, assigned to, contact, and date to be filled.
- **Poster view (!canEdit):** Non-creators see a read-only poster layout:
  - Color strip at top (amber=follow_up, red=failed, green=complete, grey=cancelled)
  - Header with title + status badge
  - Banner: "Read-only" (red) for others, "You can update the status" (blue) for assignee
  - Notes section with scrollable description (min 60px, max 200px)
  - Contact details card: shows name, phone, email, pipeline in a single card (phone/email enriched from CRM pipeline endpoint)
  - Assigned To and Status as input-style fields with labels outside
  - Follow-Up Date as full-width card
  - Reason fields (cancellation, completion, failed) appear directly below Status dropdown when changed
  - Footer: "Created by" info, Close button, Save button (only if canEditStatus)
- Permission tiers:
  - `isCreator`: Full edit (title, notes, contact, assign_to, date)
  - `isAssignee`: Can edit status + mini PATCH flows only
  - Others: Read-only with banner
- Status field disabled for assignee when status is `failed` (auto-set only)
- Non-admin creator: Assign To disabled, auto-set to logged-in user
- Admin creator: Assign To editable with dropdown
- Assignee-only mini PATCH flows (same pattern as tasks):
  - **Cancelled**: requires cancellation reason (`followup_cancellation`)
  - **Failed**: requires failed reason (`followup_failed`)
  - **Complete**: requires completion remarks (`completion_remarks`)
  - Creator sees these fields as read-only
- Contact dropdown: loads server-side filtered by assigned user's CRM deals; admin/superadmin users see all contacts
- Contact details (phone, email) enriched from CRM pipeline endpoint after contacts list loads

**Card (FollowUpCard):**
- Shows status badge (pink=follow_up, red=failed, green=complete, grey=cancelled)
- `failed` status: card background turns red (same as overdue tasks)

---

### 4. Meeting (`todo_type: "meeting"`)

**Statuses:** `upcoming`, `live`, `ended`, `cancelled`

**Creation (AddEventModal → Meetings tab):**
- Required: Title, Date, Start Time, End Time
- Optional: Agenda, Location/Link, Status, Attendees (multi-select from users)
- Title and Status in a 2-column grid at the top
- Date/Start Time/End Time in a 3-column grid
- Attendees stored via `MeetingAttendee` model

**Auto-status (written on save + overridden on read):**
- Same logic as events via `compute_event_status()`:
  - `cancelled` is never auto-overridden
  - `end < now` → `ended`
  - `start <= now <= end` → `live`
  - `start > now` → `upcoming`

**UI (UpdateMeetingModal):**
- Title and Status side by side in a 2-column grid
- Status dropdown has 4 color-coded options (same as events)
- Only creator can edit; others see read-only

**Card (MeetingCard):**
- Single badge with status-specific text + color:
  - `upcoming` → blue "Meeting" badge
  - `live` → green "Live" badge
  - `ended` → muted "Ended" badge
  - `cancelled` → red "Cancelled" badge
- Card background is always the same (no green tint for live)

---

### Status Constants

Each todo type has a dedicated `STATUS_CHOICES` constant on the `CalendarTodo` model:

| Constant | Type | Values |
|----------|------|--------|
| `FOLLOWUP_STATUS_CHOICES` | Follow-up | `follow_up`, `failed`, `complete`, `cancelled` |
| `MEETING_STATUS_CHOICES` | Meeting | `upcoming`, `live`, `ended`, `cancelled` |
| `EVENT_STATUS_CHOICES` | Event | `upcoming`, `live`, `ended`, `cancelled` |
| `TASK_STATUS_CHOICES` | Task | `assigned`, `progress`, `completed`, `canceled`, `on_hold`, `overdue`, `approved` |

All serializer validation references these constants via `[s[0] for s in CalendarTodo.<TYPE>_STATUS_CHOICES]`.

The frontend mirrors these in `constants.js` with `*_STATUS_OPTIONS` (for dropdowns), `*_STATUS_STYLES` (for badge CSS), and helper functions (`get*StatusTextColor`, `get*StatusDropdownItemStyle`, `get*StatusDotColor`).

## Backend Architecture

### Views (`CalendarTodoViewSet`)

- **Permissions:** `IsAuthenticated` (all endpoints require login)
- **Queryset filtering by user role:**
  - **Admin/Superadmin:** All todos (full visibility across all users)
  - **Other roles:** Assigned to user, attendee of meeting, `OR` all events
- **Date filtering:**
  - When both `start` and `end` query params provided:
    - Events with range overlap are included (spanning multi-day events)
    - Other types: only items whose `start` falls within the range
- **Pagination:** CustomPageNumberPagination, page_size=100

### Serializers

- **`CalendarTodoSerializer`** handles all 4 types
- **Validation:**
  - Task: deadline required, valid task status values
  - Event: description required, date required, valid event status values, end must be after start
  - Follow-up: date required, valid follow-up status values (`follow_up`, `failed`, `complete`, `cancelled`)
  - Meeting: date required
  - End time must be after start time (all types)
- **Read-only fields:** `id`, `user`, `created_at`, `updated_at`
- **`to_representation`** overrides status at read time for tasks (overdue detection), events (upcoming/live/ended detection), and follow-ups (auto-failed when past-due)

### URLs

- `api/calendar/todos/` — list/create
- `api/calendar/todos/{id}/` — retrieve/update/delete
- Registered via DRF DefaultRouter

---

## Frontend Architecture

### Component Tree

```
CalendarPage (route)
└── CalendarComponent
    ├── EventsPanel (left sidebar)
    │   ├── AddEventModal (4 tabs: Tasks, Event, Follow-up, Meetings)
    │   │   ├── TaskTabForm
    │   │   ├── EventTabForm
    │   │   ├── FollowUpTabForm
    │   │   ├── MeetingTabForm
    │   │   └── FormDropdowns (shared dropdown portals)
    │   ├── UpdateTaskModal (creator form + assignee poster view)
    │   ├── UpdateEventModal (creator form + read-only poster view)
    │   ├── UpdateFollowUpModal (creator form + assignee poster view)
    │   └── UpdateMeetingModal (creator form + read-only poster view)
    │   └── Card components: TaskCard, EventCard, FollowUpCard, MeetingCard
    └── Month grid (right side)
        ├── Day cells with colored dots
        └── Month navigation
```

### Data Flow

- **Month grid:** Fetches all todos for visible month → groups by date (`eventsByDate`) → shows colored dots per day
  - `eventsByDate` uses `eachDayOfInterval` for multi-day events
  - Dot colors: blue (task), emerald (event), amber (follow-up), purple (meeting)
- **EventsPanel:** Fetches all todos for the selected day independently (not from parent's cache)
- **Refresh:** Both components have `refreshTrigger`/`fetchKey` state that increments on event creation/update/deletion

### Key UX Patterns

- Modal portals rendered via `createPortal` to `document.body`
- Dropdown menus positioned using `getBoundingClientRect` + fixed positioning
- Color-coded status badges on cards and dropdown options
- **AddEventModal split into components:** Each tab (Task, Event, Follow-up, Meeting) is a separate component receiving `data` + `onChange` props; shared dropdown portals in `FormDropdowns` component
- **Poster views:** Update modals show two layouts based on role:
  - Creator: full edit form
  - Non-creator: poster view with read-only info cards, status dropdown (if assignee), and reason fields inline
- Mini PATCH flows for task and follow-up sub-actions (hold reason, extension request, completion remarks, cancellation reason, failed reason)
- **Assignee-only mini PATCH flows**: Non-creator assignees submit sub-actions as separate PATCH calls; creator sees them read-only
- **Reason fields inline:** In creator and poster views, reason fields (cancellation, completion, failed) appear directly below the Status dropdown — not at the bottom of the form
- **Contact details card:** Poster view shows a single card with contact name, phone, email, and pipeline (enriched from CRM pipeline endpoint)
- **Contact-assignee linkage**: In follow-up creation/editing, contacts load server-side filtered by the assigned user's CRM deals; admin/superadmin users see all contacts
- **Non-admin creator Assign To restriction**: Non-admin creators cannot change the assignee — it's auto-set to themselves and disabled
- Debounced server-side search for contact dropdowns (400ms delay)
- **Description scroll:** Notes field in poster view has min-height (60px) and max-height (200px) with overflow scroll

### Permission Model Reference

**Task (UpdateTaskModal):**
| Role | Full Edit | Deadline | Status | Hold/Extend/Complete |
|------|-----------|----------|--------|---------------------|
| Creator | ✓ | ✓ | ✓ | ✓ (mini PATCH) |
| Assignee | — | — | ✓ | ✓ (mini PATCH) |
| Admin (not creator/assignee) | — (read-only) | — | — | — |
| Others | — (read-only) | — | — | — |

**Follow-up (UpdateFollowUpModal):**
| Role | View | Full Edit | Status | Cancel/Fail/Complete Reason | Save Requirements |
|------|------|-----------|--------|-----------------------------|-------------------|
| Creator | Edit form | ✓ | ✓ | ✓ (inline below status) | title, pipeline, assign_to, contact, date |
| Assignee | Poster view | — | ✓ (not when failed) | ✓ (mini PATCH, inline below status) | status + reason field |
| Admin (not creator/assignee) | Poster view (read-only) | — (read-only) | — | — | — |
| Others | Poster view (read-only with banner) | — (read-only) | — | — | — |

---

## Known Issues / Vulnerabilities

### 1. No External Calendar Sync
The `calendar_event_id` field on the HR `InterviewSchedule` model is a placeholder — there is no integration code with Google Calendar, Outlook, or iCal anywhere in the codebase. Users must manually duplicate entries between the CRM calendar and their work calendar. There are no mobile notifications for CRM calendar entries.

**Impact:** Double-entry, missed meetings, stale data across systems.

### 2. No API-Level Tests
Only 17 model-level tests exist (status computation logic in `event_calendar/tests.py`). There are zero tests for:
- ViewSet permission enforcement (role-based queryset filtering)
- Serializer validation (missing required fields, invalid status values)
- Date range filtering (multi-day event overlap queries)
- Endpoint behavior (can a user PATCH a task they shouldn't have access to?)

**Impact:** Silent regressions — a change to the viewset or serializer could break permission boundaries without detection.

### 3. No Shared API Layer
All frontend components make raw `axios` calls with hardcoded endpoint strings (e.g., `/api/calendar/todos/`). There is no centralized API client, no request/response typing, no shared error handling, and no retry logic. The endpoint string is duplicated across 8+ files.

**Impact:** Fragile to backend changes (endpoint versioning requires find-and-replace), no TypeScript safety on API shapes, duplicated fetch logic makes bugs harder to track.

### 4. Separate HR Compliance Calendar
`ComplianceCalendarEntry` in `hr/models.py` is a completely independent model with its own ViewSet, serializer, and migrations. It shares no UI, query logic, or data with the main `CalendarTodo` module.

**Impact:** Feature fragmentation — users must check two separate places for time-sensitive items. No unified calendar view exists.

### 5. Dual-Status (Stored vs Computed)
`CalendarTodo.status` is a persisted DB field, but `to_representation()` overrides it at read time. For example:
- A task with `status="assigned"` in the DB gets returned as `"overdue"` via the API if `start < now`
- The DB and API can disagree on the current status
- Direct DB queries (admin, reporting, analytics) see stale statuses — e.g., `CalendarTodo.objects.filter(status='overdue')` would miss tasks that became overdue since their last save

The `save()` method also computes and overwrites the status, making the same logic run twice (once at write time, once at read time).

**Impact:** Data inconsistency between what's stored and what's served. Not a UI bug — the UI always shows the correct computed status. Only affects direct DB access for reporting or analytics.
