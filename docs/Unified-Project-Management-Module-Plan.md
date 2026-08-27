# Unified Project & Work Management Module
## End-to-End Requirement, Research, Workflow & Implementation Plan
**Prepared for:** Hertex — Hertex Business Suite
**Module codename:** *HertexFlow* (working name — rename as desired)
**Version:** 1.0 | **Date:** July 22, 2026

---

## 1. Executive Summary

This document defines a **unified work-management module** — a single platform that behaves like Jira for software teams, like a CRM/SPM tool for sales targets, and like Asana/Monday/ClickUp for every other business department (marketing, HR, operations, support) — all on **one data model, one permission system, and one reporting layer**.

The core idea borrowed from every leading tool researched (Jira, Linear, ClickUp, Asana, Monday.com, and sales performance platforms like Everstage/QuotaPath) is the same: **a flexible "container → work item → workflow" hierarchy**, specialized per department through **configurable issue types, custom fields, and workflows**, not through separate products. This is exactly how ClickUp and Monday.com achieve "one tool for everything," while Jira and Linear stay deliberately opinionated for engineering-only use.

**Recommended approach:** Build one core engine (Workspaces → Projects → Work Items → Workflows) and layer **department "modes"** on top:
- **Dev Mode** — Jira/Linear-style Scrum & Kanban, sprints, epics, story points, backlog, burndown.
- **Sales Mode** — pipeline/deal tracking, per-employee/team targets & quota attainment, leaderboards, commission-ready data.
- **Ops/Generic Mode** — tickets, tasks, milestones, approvals — for HR, marketing, support, finance, admin.

---

## 2. Research: What the Best Tools Do Well

| Tool | Best-in-class strength | Weakness to avoid | Relevance to us |
|---|---|---|---|
| **Jira** | Deepest agile engine: backlog, sprints, epics, story points, burndown/velocity, workflow engine | Steep learning curve, heavy config overhead | Blueprint for our **Dev Mode** |
| **Linear** | Extremely fast, opinionated workflow (Triage → Backlog → Cycle → Done), keyboard-first | Too rigid for non-eng teams | Model for **default workflow states** and speed/UX bar |
| **ClickUp** | One workspace for everything — docs, sprints, custom fields, dashboards, AI | Overwhelming setup, 2–4 week onboarding curve reported by users | Proof that a single unified engine <cite index="5-1">can reduce switching friction through importers and shared structure</cite>, but we must avoid its complexity trap |
| **Asana** | Clean task hierarchy, timelines, goal/OKR alignment, portfolios | <cite index="1-1">Less adaptable for CRM-style or cross-department operational workflows</cite> | Model for **Milestones, Portfolios, and OKR view** |
| **Monday.com** | Visual "Work OS" boards, executive dashboards, <cite index="3-1">strong automation and view flexibility</cite> | Automation-run limits at scale | Model for **dashboard/reporting layer** and non-technical adoption |
| **Everstage / QuotaPath / Qobra (Sales Performance Mgmt)** | <cite index="10-1">Cascading targets from company → team → rep, top-down and bottom-up quota modeling, real-time attainment dashboards</cite> | Usually a bolt-on, disconnected from delivery/project data | Blueprint for our **Sales Mode / Target Engine** |
| **Zendesk / Jira Service Management (ticketing)** | SLA timers, queues, auto-routing, customer-facing portal | Siloed from delivery board | Blueprint for our **Ticketing sub-module**, unified with tasks |

**Cross-cutting insight from 2026 comparisons:** <cite index="2-1">Most tool migrations happen because of poor adoption, not missing features</cite> — meaning **simplicity of the default experience** matters more than feature count. We should launch with strong, opinionated defaults (like Linear) and let power users unlock ClickUp-style configurability later, rather than exposing every setting on day one.

---

## 3. Goals & Non-Goals

**Goals**
1. One system of record for all work: dev tickets, sales targets, marketing tasks, HR requests, support tickets.
2. Native Agile support (Scrum + Kanban) for engineering.
3. Native sales target/quota management tied to real pipeline activity, per employee/team/region.
4. Configurable per-department workflows without needing separate tools.
5. Unified reporting: one dashboard where leadership sees engineering velocity, sales attainment, and ops SLAs side by side.
6. Role-based access so each department only sees relevant configuration complexity.

**Non-Goals (v1)**
- Full accounting/invoicing (integrate with existing finance tools instead).
- Full HRIS/payroll (integrate, don't rebuild).
- Deep marketing automation (email campaigns) — only task/approval tracking for marketing work.

---

## 4. Core Domain Model (applies to every department)

```
Organization
 └─ Workspace (e.g., "Aspects Enterprise", "Hertex Internal")
     └─ Project / Space (e.g., "Smart Klub App", "Q3 Sales – North Region", "Client Support")
         ├─ Team (group of members + roles)
         ├─ Module/Component (e.g., "Backend", "Onboarding Flow", "Enterprise Accounts")
         ├─ Sprint / Cycle (time-boxed, dev-mode only, but reusable for any team as "iteration")
         ├─ Milestone (date-based, department-agnostic — e.g., "App Store Launch", "Q3 Target Close")
         ├─ Work Item (the universal unit — see §4.1)
         └─ Target (department-specific goal object — see §6.2 Sales)
```

### 4.1 The Universal "Work Item"

Every ticket, task, story, bug, deal, or request in the system is one underlying entity — a **Work Item** — differentiated by an `issue_type`:

| Field | Description |
|---|---|
| `id`, `key` | e.g., `SK-142` (Smart Klub), `SLS-88` (Sales) |
| `issue_type` | Epic, Story, Task, Bug, Sub-task, Ticket, Deal, Request, Approval |
| `title`, `description` | Rich text, attachments, mentions |
| `status` | Maps to a configurable **workflow** (see §7) |
| `priority` | Lowest → Highest, or department-specific (e.g., SLA-based for support) |
| `assignee`, `reporter`, `watchers` | |
| `project_id`, `sprint_id`/`cycle_id` (nullable), `epic_id` (nullable) | |
| `story_points` / `estimate` | Dev mode |
| `deal_value`, `target_id`, `stage` | Sales mode only |
| `due_date`, `start_date` | |
| `custom_fields` | JSON — department-configurable |
| `labels/tags` | |
| `linked_items` | blocks / is blocked by / relates to / duplicates |
| `sla_clock` | Ticketing mode — first response/resolution timers |
| `activity_log` | comments, status changes, audit trail |

**Why one entity, not five tables:** this is exactly how ClickUp and Monday achieve cross-department flexibility — a shared item table with configurable fields/workflows per project type, instead of hardcoded "issue" vs "deal" vs "ticket" schemas. It lets a Sales "Deal" and a Dev "Bug" share the same comments, notifications, automation, and reporting engine.

---

## 5. Ticketing System (support / internal requests, shared across all departments)

This is the "help-desk" layer any department can turn on for a project (IT support, HR requests, client tickets for Aspects Enterprise, App bug reports from Smart Klub users).

**Requirements**
- Multi-channel intake: web form/portal, email-to-ticket, in-app widget, API.
- Queues with auto-assignment rules (round robin, load-based, skill-based).
- SLA policies: first-response time, resolution time, business-hours calendars, escalation on breach.
- Ticket → Task conversion (a support ticket can spawn a dev Task/Bug linked back to it, so the requester gets status updates automatically).
- Customer-facing portal with ticket status tracking (for Aspects Enterprise / Smart Klub end users).
- Canned responses / macros, satisfaction (CSAT) survey after close.
- Priority auto-suggestion from keywords/urgency.

---

## 6. Department Modes

### 6.1 Software Development Mode (Jira/Linear-style)

**Hierarchy:** Epic → Story/Task/Bug → Sub-task

**Must-have features**
- **Backlog** — prioritized, drag-to-reorder, per-project or per-team.
- **Sprints/Cycles** — start/end dates, sprint goal, capacity per member (based on hours or story points), sprint scope-change tracking.
- **Boards** — Kanban (continuous flow) and Scrum board (sprint-scoped), swimlanes by epic/assignee.
- **Estimation** — story points (Fibonacci) or time-based; team velocity computed automatically from last N sprints.
- **Burndown / Burnup charts**, **Velocity chart**, **Cumulative Flow Diagram**.
- **Epics & Roadmap/Timeline view** — Gantt-style, dependency arrows (mirrors Asana's Timeline, praised as best-in-class for dependency-heavy planning).
- **Releases/Versions** — tag which sprint/tickets ship in which app version (directly useful for Smart Klub release management).
- **Code integration** — link commits/PRs (GitHub) to tickets; auto-transition status on PR merge.
- **Definition of Done / workflow gates** — e.g., cannot move to "Done" without QA sign-off.
- **Bug triage queue** separate from feature backlog, with severity/priority matrix.

**Best practice adopted:** Linear's opinionated default workflow — *Backlog → Triage → In Progress → In Review → Done* — ships as the out-of-the-box default, with the option (ClickUp-style) to add custom statuses later. This avoids the configuration paralysis that slows ClickUp adoption.

### 6.2 Sales Mode (Target & Pipeline Management)

**Core objects**
- **Pipeline** — configurable stages (e.g., Lead → Qualified → Proposal → Negotiation → Won/Lost).
- **Deal (Work Item, issue_type = Deal)** — value, probability, expected close date, linked contact/account, linked Work Items (e.g., onboarding tasks once won).
- **Target/Quota** — the key requested feature:
  - Assigned **per employee**, per team, per region, per product line.
  - Cadence: monthly / quarterly / annual, with auto-prorated monthly breakdown from a quarterly number.
  - **Top-down** (leadership sets org target, cascades down) or **bottom-up** (reps forecast, rolls up) — support both, matching current SPM best practice.
  - Target types: Revenue, Deal count, New accounts, Activity (calls/demos), Renewal/retention.
- **Attainment tracking** — real-time % attainment vs. target, computed from Won deals in the period; visible to rep and manager without manual reporting.
- **Leaderboard** — team/individual ranking, opt-in gamification.
- **Forecast rollup** — weighted pipeline value (deal value × stage probability) rolled up to team/org forecast, updated live.
- **Commission-ready export** — attainment + deal data structured so it can feed a payroll/commission tool later (even if full commission engine is out of scope for v1).

**Best practice adopted:** cascading target hierarchy and live attainment dashboards (the pattern common to Everstage, QuotaPath, and monday CRM), rather than a static quota spreadsheet.

### 6.3 Generic / Operations Mode (HR, Marketing, Support, Admin, Finance-ops)

- **Task/Request boards** — simple Kanban with custom statuses per team (e.g., HR: Requested → Approved → In Progress → Closed).
- **Approval workflows** — multi-step sign-off (e.g., expense request, content approval) with approve/reject + comments.
- **Milestones** shared across departments so a company-wide launch (e.g., Smart Klub go-live) shows dev tickets, marketing tasks, and sales enablement tasks on one milestone timeline.
- **Recurring tasks** (weekly reports, monthly reconciliations).
- **Campaign/Project templates** reusable across departments.

### 6.4 Cross-Cutting: Goals / OKRs & Milestones

- Company → Department → Team → Individual objective tree (Asana-style goal alignment).
- Milestones are **department-agnostic** date markers a Work Item, Sprint, or Target can attach to — this is how "App Store Launch" can show engineering readiness, marketing readiness, and sales-enablement readiness on one page.

---

## 7. Configurable Workflow Engine

Every project picks (or customizes) a **workflow** = ordered statuses + allowed transitions + optional gates.

| Preset | Default statuses |
|---|---|
| Dev — Scrum | Backlog → Triage → To Do → In Progress → In Review → QA → Done |
| Dev — Kanban | To Do → In Progress → Blocked → Done |
| Support Ticket | New → Assigned → In Progress → Waiting on Customer → Resolved → Closed |
| Sales Deal | Lead → Qualified → Proposal Sent → Negotiation → Won / Lost |
| Ops Approval | Requested → Under Review → Approved / Rejected → Completed |

Transitions can trigger **automations** (see §8), require **mandatory fields** (e.g., "Lost reason" required to move Deal → Lost), or need specific **roles** to execute (e.g., only QA can move to Done).

---

## 8. Automation & Notifications

- Rule builder: **When** [trigger] **and** [condition] **then** [action] (mirrors Monday/ClickUp rule pattern).
  - Examples: "When ticket priority = Urgent → notify team lead + Slack/Email"; "When Deal moves to Won → auto-create onboarding checklist tasks"; "When Sprint ends with incomplete items → auto-move to next sprint + notify assignee."
- Multi-channel notifications: in-app, email, and optional Slack/Teams/WhatsApp integration.
- Digest mode (daily/weekly summary) to avoid Asana-style notification overload reported by users.

---

## 9. Dashboards & Reporting

| Audience | Views |
|---|---|
| Engineering Lead | Sprint burndown, velocity trend, cumulative flow, bug backlog aging |
| Sales Manager | Team attainment %, pipeline coverage ratio, forecast vs. target, leaderboard |
| Executive (cross-department) | Company OKR progress, milestone status across all departments, SLA compliance, revenue vs. target |
| Support Lead | SLA breach rate, ticket volume trend, CSAT score, first-response time |
| Individual employee | My tasks, my sprint commitment, my quota attainment, my open tickets |

All dashboards built on the same **Work Item + Target** data — no separate reporting database needed, avoiding the "disconnected spreadsheet" problem common in bolt-on sales quota tools.

---

## 10. Roles & Permissions

| Role | Scope |
|---|---|
| Org Admin | Full control: billing, workspace/project creation, org-wide settings |
| Workspace/Project Admin | Manage members, workflows, custom fields within their project |
| Team Lead / Manager | Assign work, set targets for their team, approve, view team reports |
| Member (Dev/Sales/Ops) | Create/update own work items, log time, comment |
| Client/Requester (portal) | Submit tickets, view own ticket status only — no access to internal boards |
| Viewer | Read-only, for stakeholders |

Permissions apply at **Organization → Workspace → Project → Work Item** levels, with field-level visibility for sensitive data (e.g., deal value visible to Sales + leadership only).

---

## 11. Sample End-to-End Workflows

### A. Software Bug Lifecycle
1. User reports a bug via Smart Klub in-app widget → auto-creates **Ticket**.
2. Support triages, links/converts to a **Bug** Work Item in the Dev project, original ticket stays open and "watches" the bug.
3. Bug enters Triage → prioritized into next Sprint backlog.
4. Dev moves it through board; PR merge auto-transitions to "In Review."
5. QA passes → "Done" → linked support ticket auto-updates to "Resolved," customer notified, CSAT survey sent.

### B. Sales Target Cycle
1. Sales Ops sets Q3 org revenue target → cascades to regional teams → cascades to individual reps (top-down), or reps submit self-forecast rolled up (bottom-up) — leadership reconciles.
2. Rep works Deals through pipeline stages; each stage change updates weighted forecast in real time.
3. Deal marked **Won** → attainment % updates instantly on rep + team + org dashboards → auto-generates onboarding Work Items for delivery/ops team.
4. Manager dashboard flags reps below 70% pipeline coverage mid-quarter for coaching (leading-indicator alert).

### C. Cross-Department Milestone (App Launch)
1. Milestone "Smart Klub Public Launch – Sep 2026" created at Workspace level.
2. Linked: Dev epics (must reach Done), Marketing tasks (assets ready), Sales enablement tasks (pitch deck, target set for launch quarter), Support (help docs published).
3. Milestone view shows % readiness per department; auto-flags at-risk items missing due dates.

---

## 12. Non-Functional Requirements

- **Multi-tenancy**: each client (e.g., Aspects Enterprise) isolated as its own Workspace/Org within Hertex Business Suite.
- **Scalability**: support 10k+ work items per project without board lag (index by project_id + status + sprint_id).
- **Security**: role-based access control, field-level permissions, audit log, SSO-ready (OAuth/SAML) for enterprise clients.
- **Performance**: board/list views load < 1s for up to 5,000 visible items with pagination/virtual scroll.
- **Extensibility**: custom fields, custom issue types, and a public REST/webhook API from day one so departments can integrate without core code changes.
- **Mobile**: responsive web minimum; native app deferred to Phase 3.
- **Offline resilience**: optimistic UI updates with sync-on-reconnect for mobile.

---

## 13. Recommended Tech Stack (build, not buy)

| Layer | Recommendation | Why |
|---|---|---|
| Frontend | React + TypeScript, component library with Kanban/Gantt (e.g., custom or dhtmlx/gantt-task-react), state via React Query | Matches modern PM tool UX patterns; fast iteration |
| Backend API | Node.js (NestJS) or Django REST — pick whichever matches Hertex's existing stack | Consistency with Hertex Business Suite |
| Database | PostgreSQL (relational core: orgs, projects, work items) + Redis (real-time board updates, caching) | JSON columns handle `custom_fields` flexibly; strong relational integrity for targets/attainment math |
| Search | Postgres full-text search initially → Elasticsearch/OpenSearch at scale | Ticket/issue search across thousands of items |
| Realtime | WebSockets (Socket.io) for live board/dashboard updates | Matches "live attainment" and live board requirement |
| Automation engine | Rule-based worker service (queue: BullMQ/Redis) | Decouple triggers from request path |
| File storage | S3-compatible object storage | Attachments, passport photos, etc., already a Hertex use case |
| Integrations | Webhooks + REST API first; GitHub/GitLab, Slack, Email (SMTP/IMAP), WhatsApp Business API (relevant for Indian SMB clients) | Matches Hertex's existing client base |

---

## 14. Implementation Roadmap

### Phase 0 — Discovery & Data Model Finalization (2 weeks)
- Finalize entity schema (Work Item, Project, Workflow, Target).
- Define default workflow presets per department.
- Wireframe core screens: Board, Backlog, Sprint, Sales Pipeline, Ticket Queue, Dashboard.

### Phase 1 — MVP Core Engine (6–8 weeks)
- Org/Workspace/Project/Team CRUD + auth/roles.
- Universal Work Item model + configurable workflow engine.
- Kanban board + list view + basic filters.
- Comments, attachments, activity log, notifications (in-app + email).
- Basic ticketing (queue, SLA timer, portal form).

### Phase 2 — Dev Mode (Agile) (4–6 weeks)
- Backlog, Sprints/Cycles, Epics, story points.
- Scrum board, burndown/velocity charts.
- GitHub PR/commit linking.
- Release/version tagging.

### Phase 3 — Sales Mode (4–6 weeks)
- Pipeline/stage builder, Deal object.
- Target/quota engine (top-down + bottom-up), per-employee/team assignment.
- Real-time attainment dashboard, leaderboard, forecast rollup.

### Phase 4 — Cross-Department Layer (3–4 weeks)
- Milestones spanning projects, OKR/Goal tree.
- Executive cross-department dashboard.
- Automation rule builder (v1: trigger-condition-action).

### Phase 5 — Hardening & Scale (ongoing)
- Custom fields UI, permission refinement, audit logs.
- Performance tuning, Elasticsearch migration if needed.
- Slack/Teams/WhatsApp integrations.
- Native mobile app (optional, based on adoption).

**Suggested total to production-ready MVP (Phases 0–3): ~16–20 weeks** with a small dedicated team (1 PM, 2–3 full-stack engineers, 1 designer, part-time QA).

---

## 15. Success Metrics (Post-Launch)

- % of teams actively using their department mode weekly (target >80% within 60 days of rollout).
- Average time-to-first-response on tickets (SLA compliance rate).
- Sprint predictability: committed vs. completed story points variance.
- Quota attainment visibility: % of reps checking dashboard weekly vs. relying on manual reports.
- Reduction in "status update" meetings/messages (proxy: fewer manual Slack status pings once dashboards are trusted).

---

## 16. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Feature bloat / ClickUp-style onboarding fatigue | Ship strong opinionated defaults per mode; hide advanced config behind "Admin settings" |
| Departments resist one unified tool ("we already use spreadsheets") | Pilot with one team per department, migrate data with importers, show dashboard value early |
| Sales target logic disconnected from real deal data | Compute attainment directly from Deal Work Items, not a separate manually-updated number |
| Scope creep into full CRM/HRIS | Explicitly integrate rather than rebuild finance/HR systems (see Non-Goals) |
| Performance degradation at scale | Design indexing/pagination from Phase 1, not retrofitted later |

---

## 17. Appendix — Source Comparison Notes

Research drawn from 2026 comparative reviews of Jira, Linear, ClickUp, Asana, Monday.com, and sales performance platforms (Everstage, QuotaPath, Qobra, CaptivateIQ). Key takeaways applied above:
- Unified multi-department tools (ClickUp, Monday) succeed by sharing one engine with configurable views/fields rather than separate products per team.
- Engineering-focused tools (Jira, Linear) win on deep agile mechanics (sprints, velocity, opinionated workflow) — these mechanics are what our Dev Mode must replicate.
- Sales performance tools consistently emphasize **cascading targets + real-time attainment visibility** over static quota spreadsheets — this is the differentiator for our Sales Mode.
- The most common reason teams abandon a PM tool is poor adoption/onboarding, not missing features — reinforcing the "opinionated defaults first, configurability later" approach recommended throughout this plan.

---

*End of document.*
