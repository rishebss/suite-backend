# 🏢 Complete HR Module — ERP System Requirements
### Enterprise-Grade Human Resource Management System (HRMS)
**Version:** 1.0 | **Standard:** Best Practice / Compliance-Ready | **Target:** Indian & Global Enterprises

---

## 📌 Table of Contents

1. [Module Overview](#1-module-overview)
2. [Core HR — Employee Master](#2-core-hr--employee-master)
3. [Recruitment & Onboarding](#3-recruitment--onboarding)
4. [Attendance & Leave Management](#4-attendance--leave-management)
5. [Payroll Management](#5-payroll-management)
6. [Statutory Compliance (PF, ESI, PT, LWF, TDS)](#6-statutory-compliance)
7. [Performance Management System (PMS)](#7-performance-management-system-pms)
8. [Training & Development (L&D)](#8-training--development-ld)
9. [Employee Self-Service Portal (ESS)](#9-employee-self-service-portal-ess)
10. [Manager Self-Service Portal (MSS)](#10-manager-self-service-portal-mss)
11. [Exit Management & Full & Final Settlement](#11-exit-management--full--final-settlement)
12. [Reports, Analytics & Dashboards](#12-reports-analytics--dashboards)
13. [Integrations](#13-integrations)
14. [Security, Roles & Compliance](#14-security-roles--compliance)
15. [Best Practices & Implementation Standards](#15-best-practices--implementation-standards)
16. [Module Architecture Summary](#16-module-architecture-summary)

---

## 1. Module Overview

### 1.1 Purpose
The HR Module is a comprehensive sub-system within the ERP that manages the **entire employee lifecycle** — from recruitment to retirement — while ensuring full compliance with Indian statutory requirements (PF, ESI, PT, LWF, TDS) and global HR best practices.

### 1.2 Key Design Principles
- **Single Source of Truth** — One employee master drives all sub-modules
- **Compliance-First** — All statutory calculations are auto-updated when government rules change
- **Audit-Ready** — Every transaction is logged with user, timestamp, and change history
- **Employee-Centric UX** — Self-service reduces HR overhead by 60–70%
- **API-First Architecture** — Every function is accessible via REST API for integration
- **Mobile-Responsive** — Full access on Android, iOS, and web browsers

### 1.3 Modules at a Glance

| Module | Key Outcome |
|---|---|
| Core HR | Centralised employee database |
| Recruitment | End-to-end hiring pipeline |
| Attendance & Leave | Real-time workforce presence |
| Payroll | Accurate, compliant salary processing |
| Statutory Compliance | PF, ESI, PT, LWF, TDS automation |
| Performance | Goal setting, appraisals, 360° feedback |
| Training & Development | Skill gap → Learning → Certification |
| ESS / MSS Portals | Employee & manager self-service |
| Exit Management | Resignation to F&F settlement |
| Analytics | Real-time HR dashboards & reports |

---

## 2. Core HR — Employee Master

### 2.1 Employee Profile
- **Personal Information:** Full name, DOB, gender, nationality, marital status, blood group, photo upload
- **Contact Details:** Mobile, personal email, emergency contacts (min. 2)
- **Address:** Current & permanent address with PIN code validation
- **Identity Documents:** Aadhaar, PAN, Passport, Voter ID, Driving Licence — with number validation and document upload
- **Bank Details:** Account number, IFSC, bank name, branch — supports multiple accounts (primary + secondary)
- **Family Details:** Spouse, children, dependants for insurance & nomination purposes

### 2.2 Employment Information
- Employee ID (auto-generated, configurable format: `EMP-YYYY-XXXX`)
- Date of Joining, Probation Period, Confirmation Date
- Employment Type: Permanent / Contract / Trainee / Intern / Part-Time
- Department, Designation, Grade, Band, Cost Centre
- Reporting Manager (primary & secondary/dotted-line), HR Business Partner
- Work Location, Branch, Entity (multi-company support)
- Work Shift Assignment
- Notice Period (in days)

### 2.3 Document Management
- Offer Letter, Appointment Letter
- Educational Certificates (10th, 12th, UG, PG, Professional)
- Experience Certificates from previous employers
- Background Verification (BGV) documents
- Statutory documents (PF Nomination Form 2, ESI Declaration)
- Version control for all documents — never delete, only supersede

### 2.4 Employee Lifecycle Status
```
CANDIDATE → OFFERED → ONBOARDING → ACTIVE → ON_LEAVE → 
NOTICE_PERIOD → SEPARATED (Resigned/Terminated/Absconded/Retired)
```

### 2.5 Best Practices
- Mandatory fields enforced at each lifecycle stage
- Aadhaar/PAN/UAN deduplication check on creation
- Auto-generate statutory numbers after probation confirmation
- GDPR/DPDP-compliant data masking for sensitive fields
- Change history log on every employee record field

---

## 3. Recruitment & Onboarding

### 3.1 Requisition Management
- Department-wise Manpower Planning & Headcount Budget
- Job Requisition Form (JRF) — raised by hiring manager
- Multi-level approval workflow (HOD → HR → Finance → MD for senior roles)
- Link requisition to approved budget / cost centre

### 3.2 Job Posting
- Internal Job Portal (IJP) — internal first-posting policy
- External job boards: LinkedIn, Naukri, Indeed (via API integration)
- Company careers page — branded, mobile-friendly
- Referral Programme Portal — track referrals, pay referral bonuses

### 3.3 Applicant Tracking System (ATS)
- Centralised candidate database with resume parsing (AI-based)
- Duplicate candidate detection
- Configurable hiring pipeline stages:
  ```
  Applied → Screening → L1 Interview → L2 Interview → 
  Technical → HR Round → Offer → Accepted/Rejected
  ```
- Interview scheduling — calendar sync (Google/Outlook), automatic invites
- Interview feedback forms — structured scorecard per role
- Offer letter generation from templates with auto-populated data
- Offer management — negotiate, revise, and track offer status

### 3.4 Background Verification (BGV)
- Integration with BGV vendors (AuthBridge, SpringVerify, IDfy)
- Track status: Not Initiated / Initiated / In Progress / Clear / Discrepant
- Conditional joining clearance based on BGV result

### 3.5 Onboarding
- **Pre-Joining Tasks (before Day 1):**
  - Digital document collection portal
  - Welcome email with first-day instructions
  - System & access provisioning workflow (IT checklist)
  - Asset allocation pre-request
- **Day 1 Checklist:**
  - ID card generation
  - System & email account creation
  - Buddy / Mentor assignment
  - Induction schedule auto-generated
- **First 30/60/90 Day Plan:**
  - Task assignments to new employee + manager
  - Completion tracking with nudge notifications
  - Early feedback surveys (Day 30, Day 60)

### 3.6 Best Practices
- Time-to-hire and cost-per-hire KPIs tracked from day one
- Structured interview kits per job family to reduce bias
- AI resume screening with configurable minimum match score
- Offer-to-joining conversion rate reporting

---

## 4. Attendance & Leave Management

### 4.1 Attendance Capture Methods
- **Biometric Integration:** Fingerprint / Facial recognition devices via API (ZKTeco, eSSL, Mantra)
- **Web Check-in/Check-out:** Location-based (GPS) web and mobile
- **Mobile App:** GPS + selfie-based attendance
- **RFID / Smart Card**
- **Manual Override:** HR/Manager with approval and reason
- Late mark detection, half-day rules, overtime flag

### 4.2 Shift Management
- Shift master: General / Rotational / Night / Flexible / Remote
- Shift roster planning — weekly/monthly view for teams
- Shift swap requests between employees (with manager approval)
- Night shift allowance auto-trigger in payroll
- Auto-detect shift based on first punch time

### 4.3 Leave Management
- **Leave Types (fully configurable):**
  - Casual Leave (CL)
  - Sick Leave (SL)
  - Earned Leave / Privilege Leave (EL/PL)
  - Maternity Leave (26 weeks as per Maternity Benefit Act 1961)
  - Paternity Leave
  - Bereavement Leave
  - Compensatory Off (Comp-Off)
  - Optional Holiday (floating leaves)
  - Leave Without Pay (LWP)
  - Marriage Leave, Study Leave, Special Leave
- **Leave Policy Engine:**
  - Accrual rules (monthly / quarterly / annual)
  - Carry-forward rules (max balance cap)
  - Encashment rules (max days, applicable leave types)
  - Lapse rules (year-end)
  - Negative balance allowed flag per leave type
  - Minimum balance before applying
- **Leave Workflow:**
  - Employee applies → Manager approves → HR notified
  - Auto-rejection if exceeds available balance
  - Cancellation requests (pre-start and post-start)
  - Backdated leave application with reason
- **Holiday Calendar:**
  - National Holidays, State-specific Holidays, Company Holidays
  - Location-wise holiday calendar (multi-state support)
  - Optional Holidays (employee choice from a pool)

### 4.4 Attendance Regularisation
- Employee submits regularisation request with reason
- Manager approval with comment
- HR override capability
- Audit trail of all regularisations

### 4.5 Overtime Management
- OT eligibility by designation / grade / category
- OT calculation rules (1.5x or 2x as per Factories Act)
- OT approval workflow before or after occurrence
- Auto-push approved OT hours to payroll

### 4.6 Best Practices
- Real-time attendance dashboard visible to managers
- Absenteeism alerts when threshold crossed (e.g., >3 consecutive absent days)
- Integration with access control (door locks) via same biometric device
- Attendance anomaly detection (e.g., buddy punching alerts)

---

## 5. Payroll Management

### 5.1 Salary Structure
- Fully configurable salary components:

| Component | Type | Taxable | Notes |
|---|---|---|---|
| Basic | Fixed | Yes | % of CTC |
| HRA | Fixed | Partially | 50%/40% of Basic |
| Conveyance Allowance | Fixed | No | Up to ₹1,600/month exempt |
| Medical Allowance | Fixed | No | ₹15,000/year exempt |
| Special Allowance | Fixed | Yes | Variable residual |
| LTA | Periodic | No | 2 trips in 4-year block |
| Performance Bonus | Variable | Yes | Linked to PMS rating |
| Night Shift Allowance | Variable | Yes | Auto from shift data |
| Overtime Pay | Variable | Yes | From attendance |
| Gratuity | Retiral | No | Provisioned monthly |
| Employer PF | Retiral | No | 12% of Basic |

- Grade-wise salary band mapping
- CTC, Gross, Net pay calculations with full breakup
- Multiple salary structures per company entity / grade

### 5.2 Payroll Processing Cycle
```
Step 1: Lock attendance & leave data
Step 2: Import variable inputs (OT, incentives, advances, arrears)
Step 3: Statutory deduction calculation (PF, ESI, PT, TDS)
Step 4: Net pay calculation
Step 5: Exception report review & corrections
Step 6: Authorisation / Payroll Approval (multi-level)
Step 7: Bank file generation (NEFT/RTGS format)
Step 8: Payslip generation & distribution
Step 9: Challan & returns filing data export
Step 10: Journal entry push to GL (accounting integration)
```

### 5.3 Salary Revision
- Increment workflow: HR initiates → Manager recommends → HOD approves → MD/CEO approves
- Bulk revision upload via Excel template
- Effective date management (mid-month or first of month)
- Arrears auto-calculation for backdated revisions
- Increment letter auto-generation

### 5.4 Advances & Loans
- Salary advance requests (ESS) with manager + HR approval
- Loan types: Personal Loan, Vehicle Loan, Housing Loan, Emergency Loan
- EMI repayment schedule — auto-deducted from salary
- Outstanding loan balance visible in ESS
- Interest-free vs interest-bearing loans (configurable)

### 5.5 Reimbursements
- Medical, Travel, Mobile, Internet, Conveyance reimbursements
- Bill upload + approval workflow
- Expense limits per grade/designation
- Monthly/quarterly processing option
- Integration with expense management if separate module

### 5.6 Payslip
- Password-protected PDF payslip (password = PAN or DOB)
- Email delivery + ESS portal access
- Downloadable salary certificate with company letterhead
- Form 16 generation at year-end

### 5.7 Best Practices
- Parallel payroll run (test mode before live) for validation
- Bank mandate verification before first salary transfer
- Salary freeze capability per employee for notices/disputes
- Variance report: previous month vs current month by component

---

## 6. Statutory Compliance

### 6.1 Provident Fund (PF)

**Governed by:** Employees' Provident Funds & Miscellaneous Provisions Act, 1952

| Parameter | Value |
|---|---|
| Employee Contribution | 12% of Basic + DA |
| Employer Contribution (EPF) | 3.67% of Basic + DA |
| Employer Contribution (EPS) | 8.33% of Basic + DA (max ₹1,250/month) |
| EDLI Contribution | 0.50% of Basic + DA (max ₹75/month) |
| Admin Charges | 0.50% (EPF) + 0.01% (EDLI) |
| Wage Ceiling | ₹15,000/month (statutory); higher for those above ceiling with option |
| VPF | Voluntary contribution above 12% (employee only) |

**Features:**
- UAN generation and seeding (Aadhaar, PAN, Bank linking via EPFO API)
- Monthly ECR (Electronic Challan cum Return) generation — PF portal format
- PF challan auto-calculation and export
- Form 2 — Nomination
- Form 10C — EPS withdrawal
- Form 10D — Pension claim
- Form 19 — PF full withdrawal
- Form 31 — PF advance
- Transfer claim support (Form 13)
- PF passbook download/view via EPFO API
- International Workers (IW) — separate contribution tracking

### 6.2 Employee State Insurance (ESI)

**Governed by:** Employees' State Insurance Act, 1948

| Parameter | Value |
|---|---|
| Employee Contribution | 0.75% of Gross Salary |
| Employer Contribution | 3.25% of Gross Salary |
| Wage Ceiling | ₹21,000/month gross |
| Exemption | Employees earning > ₹21,000/month gross |

**Features:**
- IP (Insured Person) number generation
- ESI challan monthly generation
- ESIC portal-format return file export
- Contribution period tracking (April–September, October–March)
- ESI card generation support
- Auto-exclusion when salary crosses threshold
- Re-inclusion when salary falls below threshold

### 6.3 Professional Tax (PT)

**State-wise slab configuration (India):**

| State | Frequency | Max Annual Tax |
|---|---|---|
| Maharashtra | Monthly | ₹2,500 |
| Karnataka | Monthly | ₹2,400 |
| West Bengal | Monthly | ₹2,400 |
| Tamil Nadu | Half-yearly | ₹1,095 |
| Andhra Pradesh | Monthly | ₹2,400 |
| Telangana | Monthly | ₹2,400 |
| Gujarat | Monthly | ₹2,400 |

- Multi-state PT slab management
- Auto-deduction from salary based on work state
- Monthly/Half-yearly challan generation per state
- PT enrollment certificate tracking per employee

### 6.4 Labour Welfare Fund (LWF)

- State-wise LWF slab configuration
- Periodic deduction (June & December for most states)
- Auto-challan generation
- Form A return filing data export

### 6.5 Tax Deducted at Source (TDS) — Salary (Section 192)

- Employee tax regime selection: **Old vs New Regime** (per Budget 2023)
- Investment declaration (Form 12BB):
  - Section 80C (PPF, ELSS, LIC, tuition fees, home loan principal)
  - Section 80D (health insurance premium)
  - Section 80G (donations)
  - HRA exemption calculation (Sec 10(13A))
  - LTA exemption (Sec 10(5))
  - Home loan interest (Sec 24b)
- Provisional tax working at start of year
- Monthly TDS deduction from salary
- Actual proof of investment submission (Nov–Feb) — document upload
- **Form 16 generation (Part A + Part B)** at year-end
- **Form 24Q** quarterly TDS return data export
- Challan 281 generation
- Lower deduction certificate (Form 15G/15H) handling

### 6.6 Gratuity

**Governed by:** Payment of Gratuity Act, 1972

```
Gratuity = (Last drawn Basic + DA) × 15/26 × No. of completed years of service
```

- Eligibility check (minimum 5 years of service)
- Auto-provision in payroll each month
- Gratuity ledger per employee
- Gratuity trust management (for trust-funded companies)
- Auto-calculation at time of exit

### 6.7 Bonus

**Governed by:** Payment of Bonus Act, 1965

- Eligibility: Employees drawing up to ₹21,000/month
- Minimum bonus: 8.33% of salary (or ₹100 whichever is higher)
- Maximum bonus: 20% of salary
- Allocable surplus calculation
- Bonus payout with payroll integration

### 6.8 Compliance Calendar & Alerts

| Compliance | Frequency | Due Date |
|---|---|---|
| PF ECR Upload | Monthly | 25th of following month |
| PF Challan Payment | Monthly | 15th of following month |
| ESI Challan Payment | Monthly | 15th of following month |
| ESI Half-Yearly Return | Half-Yearly | 42 days after end of contribution period |
| Form 24Q | Quarterly | 31st of month after quarter end |
| PT Payment | Monthly/Half-Yearly | State-specific |
| LWF | Half-Yearly | June 30 / December 31 |
| Form 16 Issue | Annual | 15th June |
| Annual PF Return | Annual | 30th April |

- Auto-email/in-app alerts 7 days, 3 days, and 1 day before due date
- Compliance dashboard showing upcoming dues and past filings
- Download-ready challan files and return files per period

---

## 7. Performance Management System (PMS)

### 7.1 Goal Setting & OKRs
- Company-level goals cascade down to department → individual
- OKR framework: Objective + Key Results with measurable metrics
- SMART goal templates per department
- Goal library — pre-built goals by job function
- Mid-year goal revision with approval workflow
- Goal weightage assignment (total = 100%)

### 7.2 Appraisal Cycle
- Configurable cycles: Annual / Half-Yearly / Quarterly
- Appraisal stages:
  ```
  Goal Setting → Mid-Year Review → Self Appraisal → 
  Manager Appraisal → Calibration → Rating Finalisation → 
  Appraisal Discussion → Increment/Promotion Decision
  ```
- Appraisal form designer (drag-and-drop questions, rating scales)
- Rating scales: 5-point / 9-point / custom

### 7.3 360° Feedback
- Peer feedback, subordinate feedback, upward feedback
- Configurable anonymity settings
- Survey templates per level/function
- Aggregate feedback report excluding outlier scores

### 7.4 Calibration
- Bell curve / forced ranking configuration
- Manager calibration sessions with team comparison view
- Rating override capability (with justification, audit-logged)
- Calibration finalisation lock

### 7.5 Promotion & Increment Linking
- PMS rating → auto-compute increment % (configurable matrix)
- Promotion recommendations from manager, HR approval
- Increment letter and promotion letter auto-generation

### 7.6 Performance Improvement Plan (PIP)
- HR creates PIP for below-par performers
- 30/60/90 day PIP milestones
- Manager check-in logs
- PIP outcome: Improved / Extended / Terminated
- Full audit trail for legal compliance

### 7.7 Best Practices
- No-surprise principle: continuous feedback nudges throughout year
- Calibration manager training module within L&D integration
- Prevent rating inflation via analytics showing manager distribution history

---

## 8. Training & Development (L&D)

### 8.1 Training Need Identification (TNI)
- Skill gap analysis from appraisal outcome
- Employee self-nomination for trainings
- Manager-recommended trainings
- Mandatory training calendar (compliance, safety, induction)

### 8.2 Training Calendar & Scheduling
- Training master: Internal / External / Online
- Venue, trainer, batch size, cost per participant
- Calendar view with team availability check
- Nomination workflow: Employee → Manager → HR → Training Team

### 8.3 Learning Management System (LMS) Integration
- Native LMS module or API integration with:
  - Cornerstone OnDemand, Udemy for Business, LinkedIn Learning, Coursera
  - Internal content upload (videos, PDFs, SCORM packages)
- Course completion tracking (% progress)
- Assessment and certification within LMS

### 8.4 Training Effectiveness
- Pre-training and post-training assessment scores
- Learning effectiveness score (Kirkpatrick Level 1 & 2)
- Skill matrix update after training completion
- Certificate generation and record in employee profile

### 8.5 Training Cost Management
- Budget allocation per department
- Actuals vs budget tracking
- ROI calculation (cost vs productivity improvement)
- External training vendor empanelment

---

## 9. Employee Self-Service Portal (ESS)

### 9.1 Dashboard
- Attendance today (check-in status, hours worked)
- Leave balance summary
- Upcoming holidays
- Pending tasks / action items
- Announcements & company news feed
- My team view (for managers)

### 9.2 Attendance
- Web check-in / check-out (GPS)
- View monthly attendance calendar
- Regularisation request submission
- Comp-off request

### 9.3 Leave
- Apply, cancel, and track leave requests
- View leave history and balances
- Team leave calendar (who is away)
- Holiday list download

### 9.4 Payroll
- View and download payslips (all months)
- Download salary certificate / CTC letter
- Loan & advance outstanding view
- Tax projection and TDS details
- Investment declaration submission (Form 12BB)
- Upload proof of investment documents

### 9.5 Profile
- View and update personal information (with HR approval workflow for critical changes)
- Update bank account details (with verification)
- Update nominee details for PF/Gratuity
- Upload/update documents

### 9.6 Helpdesk / Tickets
- Raise HR tickets: Payroll query, Certificate request, IT access request, Policy clarification
- Track ticket status and resolution time
- Knowledge base for FAQ (self-serve)

### 9.7 Performance
- View goals, self-appraisal form access
- View appraisal history
- Feedback given and received

### 9.8 Requests
- Asset request (laptop, sim card, etc.)
- Travel & expense claim submission
- Separation initiation (resignation)

---

## 10. Manager Self-Service Portal (MSS)

### 10.1 Team Overview
- Real-time attendance status of team
- Leave requests pending approval
- Upcoming team birthdays / work anniversaries

### 10.2 Approval Workflows
- Leave approvals (approve / reject / refer)
- Attendance regularisation approvals
- OT approvals
- Expense claim approvals
- Training nominations

### 10.3 Performance Management
- Assign and track team goals
- Submit manager appraisal ratings
- View 360° feedback reports

### 10.4 Reports
- Team attendance report
- Team leave utilisation
- Manpower in team (headcount, open positions)
- Team salary cost summary

### 10.5 Escalations
- Escalate unresolved HR queries on behalf of team
- Track resolution

---

## 11. Exit Management & Full & Final Settlement

### 11.1 Resignation Process
- Employee submits resignation via ESS
- System auto-calculates last working day based on notice period
- Manager acknowledges and accepts / requests notice period buyout
- Exit clearance checklists triggered to all departments

### 11.2 Exit Clearance
- IT: Laptop, mobile, SIM, access cards — handover
- Admin: ID card, keys, locker
- Finance: Pending advances, loans outstanding
- Projects: KT (Knowledge Transfer) completion
- Library: Books, equipment
- All departments sign-off digitally

### 11.3 Exit Interview
- Structured exit interview questionnaire
- Anonymous or attributed (employee choice)
- Exit interview by HR / skip-level manager
- Reason for leaving category tagging (compensation / growth / culture / relocation / personal)
- Aggregate analysis for attrition trend reporting

### 11.4 Full & Final Settlement (F&F) Calculation

| Component | Rule |
|---|---|
| Salary for last month | Actuals based on attendance |
| Leave Encashment | Earned leave balance × per-day salary |
| Gratuity | If eligible (5+ years), as per Act |
| Bonus Proration | Proportionate if applicable |
| Notice Period Recovery | Deduct if notice period not served |
| Loan Recovery | Outstanding balance |
| Other Deductions | Assets not returned, etc. |

- Auto-generate F&F statement
- HR review and approval
- Finance approval and payment
- PF withdrawal/transfer assistance
- Form 16 for exit month TDS
- Experience letter and relieving letter auto-generation

### 11.5 Alumni Portal
- Ex-employee access to payslips, Form 16, relieving letter for 3 years post-exit
- Rehire tracking and flagging

---

## 12. Reports, Analytics & Dashboards

### 12.1 Real-Time HR Dashboard (CEO/CHRO View)
- Total headcount, new joinings this month, attritions this month
- Attrition rate (monthly, quarterly, YTD)
- Headcount by department / location / grade
- Payroll cost trend (monthly)
- Compliance status (PF, ESI, PT all-green / alert)
- Open positions vs filled ratio

### 12.2 Attendance & Leave Reports
- Daily / Monthly attendance register
- Late arrivals and early departures report
- Absenteeism report
- Leave utilisation by employee / department
- Comp-off balance report
- Holiday calendar summary

### 12.3 Payroll Reports
- Salary register (detailed and summary)
- Department-wise payroll cost
- CTC vs Gross vs Net comparison
- Increment history report
- Bonus payout report
- Arrears report

### 12.4 Statutory Reports
- PF ECR file (EPFO format)
- ESI return file (ESIC format)
- Form 24Q (TDS quarterly return)
- Form 12BA (perquisite statement)
- Form 16 (Part A + Part B)
- PT challan data per state
- LWF challan data per state
- Annual PF return (Form 3A, 6A)

### 12.5 Recruitment Analytics
- Time to fill (days) per position
- Source of hire analysis (LinkedIn / Naukri / Referral / Walk-in)
- Offer acceptance rate
- Cost per hire
- Recruiter performance (positions closed, avg TAT)
- Requisition ageing report

### 12.6 Attrition Analysis
- Attrition by department, grade, tenure band, location
- Voluntary vs involuntary attrition split
- Exit reason analysis
- Regrettable attrition (high-performer leavers)
- Attrition predictor (ML model: flight risk scoring — optional Phase 2)

### 12.7 Compliance Calendar Report
- All upcoming statutory due dates
- Filed vs pending status
- Penalty risk dashboard

---

## 13. Integrations

### 13.1 Government / Statutory Portals

| System | Integration Type | Purpose |
|---|---|---|
| EPFO Unified Portal | API / File Upload | ECR upload, UAN generation, KYC seeding |
| ESIC Portal | API / File Upload | Monthly return, IP registration |
| TRACES (TDS Portal) | File Upload | Form 24Q, Form 16 data |
| Income Tax Portal | API (26AS fetch) | TDS verification |
| MCA Portal | N/A | Company registration reference |
| DigiLocker | API | Aadhaar/PAN verification |
| UIDAI API | API | Aadhaar OTP-based verification |
| NSDL / KARVY | API | PAN verification |

### 13.2 Banking Integrations

| Bank | Integration | Purpose |
|---|---|---|
| ICICI / HDFC / SBI / Axis | SFTP / API | Salary disbursement (bulk NEFT/RTGS) |
| All Scheduled Banks | IFSC Validator API | Bank account validation before first transfer |
| NPCI (UPI / NACH) | API | Recurring deductions / advance repayments |

### 13.3 ERP Internal Integrations

| Module | Integration | Data Flow |
|---|---|---|
| Finance / Accounting (GL) | Real-time API | Payroll journal entries → GL |
| Fixed Assets | API | Asset allocation per employee |
| Projects | API | Employee cost allocation to project codes |
| Procurement | API | Vendor invoices for training / BGV |
| CRM | API | Incentive data for sales team payroll |

### 13.4 Biometric / Access Control

| Device Brand | Protocol |
|---|---|
| ZKTeco | SDK + REST API |
| eSSL | SDK + REST API |
| Mantra | SDK |
| HID / Suprema | Wiegand / REST |
| Hikvision (Facial) | REST API |

- Push/pull model: Device pushes punch logs every 5 minutes
- Fallback: Manual upload of punch data (CSV format)

### 13.5 Third-Party HR Tools

| Tool | Purpose | Integration |
|---|---|---|
| LinkedIn Talent | Job posting + candidate sync | OAuth + API |
| Naukri | Job posting + candidate sync | API |
| Indeed | Job posting | API |
| AuthBridge / SpringVerify | BGV | REST API |
| DocuSign / Adobe Sign | Digital signatures | REST API |
| Zoom / Google Meet | Interview scheduling | Calendar API |
| Slack / MS Teams | HR notifications, ticket alerts | Webhook / Bot |
| Darwinbox / Keka | Migration / data sync (if replacing) | Data migration scripts |
| SAP / Oracle HCM | Data exchange for legacy systems | Middleware / ESB |
| Cornerstone / Udemy | LMS for training | SCORM / REST API |
| Zoho People | HR data sync | REST API |

### 13.6 Notification Channels
- Email (SMTP / SendGrid / AWS SES)
- SMS (Twilio / MSG91 / Exotel)
- WhatsApp Business API (for leave approval, payslip delivery)
- In-app push notifications (mobile app)
- Slack / MS Teams bots

---

## 14. Security, Roles & Compliance

### 14.1 Role-Based Access Control (RBAC)

| Role | Access Level |
|---|---|
| Super Admin (IT) | Full system, audit logs, role management |
| HR Admin | All HR data, payroll processing, compliance |
| Payroll Executive | Payroll + statutory only |
| HR Business Partner | Assigned business unit data only |
| Recruitment Team | ATS + onboarding only |
| HOD / Department Manager | Own department data, approvals |
| Team Manager | Own team data, approvals |
| Employee | Own data + ESS features |
| Finance (Read-Only) | Payroll cost reports, GL entries |
| Auditor (Read-Only) | Full read, no write, watermarked exports |

### 14.2 Data Security
- AES-256 encryption at rest for sensitive fields (Aadhaar, PAN, bank accounts)
- TLS 1.3 for all data in transit
- IP-based access restriction for payroll processing screens
- MFA (Multi-Factor Authentication) mandatory for HR Admin, Payroll, Super Admin
- Session timeout: 30 minutes idle
- Failed login lockout after 5 attempts

### 14.3 Audit Logs
- Every create / update / delete logged with user ID, timestamp, IP, old value, new value
- Logs immutable (append-only)
- Audit log export for ISO 27001, SOC 2 audits
- Payroll audit trail: who ran, who approved, what changed

### 14.4 Data Privacy Compliance
- **DPDP Act 2023 (India):** Consent management, data minimisation, right to erasure (post-exit)
- **GDPR (for global entities):** DPA agreements with vendors, privacy by design
- Data retention policy: Employee data — active period + 7 years post-exit
- Data masking for non-production environments

### 14.5 Compliance Framework
- ISO 27001 — Information Security Management
- SOC 2 Type II — Security, Availability, Confidentiality
- CMMI HR Processes — Capability Maturity Model Integration

---

## 15. Best Practices & Implementation Standards

### 15.1 Technology Best Practices
- **API-First:** Every feature exposed as REST API (versioned, documented via Swagger/OpenAPI)
- **Microservices:** Each HR sub-module independently deployable
- **Event-Driven:** Payroll, attendance, compliance events published to message queue (Kafka/RabbitMQ)
- **CQRS Pattern:** Separate read/write models for high-performance reporting
- **Database:** Separate transactional DB (PostgreSQL) and reporting DB (ClickHouse/Redshift)
- **File Storage:** Document management via S3-compatible object storage with CDN
- **Caching:** Redis for attendance data, session management
- **Mobile:** Progressive Web App (PWA) + Native apps (React Native)

### 15.2 HR Process Best Practices

**Payroll:**
- Always run a parallel/shadow payroll for first 3 months before going live
- Lock attendance 2 days before payroll cut-off
- Maker-checker for all payroll modifications
- Never process payroll without a 4-eye review

**Compliance:**
- Maintain a compliance calendar with escalations to CEO/CFO for overdue items
- Retain all challan receipts and acknowledgement numbers in system
- Annual statutory audit by a CA/CS before filing

**Performance:**
- Launch PMS at start of fiscal year — never mid-year for first cycle
- Train managers on giving feedback (internal L&D module)
- Calibrate ratings across managers before finalising

**Onboarding:**
- Use a Day-1 readiness checklist so new hires are productive from day one
- Buddy programme increases 90-day retention by 30%
- Measure onboarding NPS (survey at Day 30 and Day 90)

**Attrition:**
- Stay interviews (not just exit interviews) for high-performers
- Predictive attrition model flags risk 60–90 days before resignation
- Counter-offer policy documented and enforced consistently

### 15.3 Implementation Roadmap

| Phase | Timeline | Scope |
|---|---|---|
| Phase 1 — Foundation | Month 1–2 | Employee Master, Attendance, Leave, Basic Payroll |
| Phase 2 — Compliance | Month 3–4 | PF, ESI, PT, TDS, LWF — full statutory automation |
| Phase 3 — Self-Service | Month 4–5 | ESS Portal, MSS Portal, Mobile App |
| Phase 4 — Talent | Month 5–7 | Recruitment (ATS), Onboarding, Performance |
| Phase 5 — Analytics | Month 7–8 | Dashboards, Attrition Analysis, Predictive Reports |
| Phase 6 — Integrations | Month 8–10 | Biometric, Banking, GL, LinkedIn, BGV vendors |
| Phase 7 — Advanced | Month 10–12 | LMS, AI Features, Chatbot, Flight Risk Model |

### 15.4 Change Management
- Designate an HR Champion in each business unit
- Super-user training (40 hours) before go-live
- End-user training — role-specific (8 hours)
- Parallel run for 2 payroll cycles before decommissioning old system
- Dedicated L1 support helpdesk for 90 days post-go-live

---

## 16. Module Architecture Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                      HR MODULE — ERP                            │
├─────────────────────────────────────────────────────────────────┤
│  Employee Master  │  Recruitment  │  Onboarding                 │
├──────────────────────────────────────────────────────────────── │
│  Attendance & Leave  │  Shift Management  │  Overtime           │
├─────────────────────────────────────────────────────────────────│
│  Payroll Engine  │  Salary Structure  │  Loans & Advances       │
├─────────────────────────────────────────────────────────────────│
│  PF  │  ESI  │  PT  │  LWF  │  TDS (192)  │  Gratuity  │ Bonus │
├─────────────────────────────────────────────────────────────────│
│  Performance Mgmt  │  360° Feedback  │  PIP  │  Calibration     │
├─────────────────────────────────────────────────────────────────│
│  Training & LMS  │  Skill Matrix  │  TNI                        │
├─────────────────────────────────────────────────────────────────│
│  ESS Portal  │  MSS Portal  │  Mobile App                       │
├─────────────────────────────────────────────────────────────────│
│  Exit Management  │  F&F Settlement  │  Alumni Portal           │
├─────────────────────────────────────────────────────────────────│
│  Reports  │  Dashboards  │  Analytics  │  Compliance Calendar   │
├─────────────────────────────────────────────────────────────────│
│  Integrations: EPFO │ ESIC │ TRACES │ Banks │ Biometric │ ERP   │
└─────────────────────────────────────────────────────────────────┘
```

### 16.1 Total Feature Count

| Module | Approx. Features |
|---|---|
| Core HR | 35+ |
| Recruitment & Onboarding | 40+ |
| Attendance & Leave | 45+ |
| Payroll | 50+ |
| Statutory Compliance | 60+ |
| Performance Management | 30+ |
| Training & L&D | 25+ |
| ESS / MSS Portals | 40+ |
| Exit & F&F | 25+ |
| Reports & Analytics | 50+ |
| Integrations | 30+ |
| Security & Compliance | 20+ |
| **Total** | **450+ Features** |

---

## Appendix A — Statutory Forms Checklist

| Form | Act | Purpose | Frequency |
|---|---|---|---|
| Form 2 | EPF | PF Nomination | On joining |
| Form 11 | EPF | Declaration (new employee) | On joining |
| ECR | EPF | Monthly return | Monthly |
| Form 3A | EPF | Annual member-wise return | Annual |
| Form 6A | EPF | Annual consolidated return | Annual |
| Form 1 | ESI | Employer registration | One-time |
| Form 1A | ESI | Family declaration | On joining |
| Half-Yearly Return | ESI | Contribution return | Half-yearly |
| Form 12BB | IT | Investment declaration | Annual |
| Form 24Q | IT | TDS return | Quarterly |
| Form 16 | IT | TDS certificate to employee | Annual |
| Form A | LWF | LWF return | Annual/Half-yearly |
| Bonus Register | Bonus Act | Bonus calculation register | Annual |
| Attendance Register | Factories Act | Daily attendance | Daily (maintained) |
| Wage Register | Minimum Wages | Salary payment register | Monthly |

---

## Appendix B — Key Compliance Acts (India)

- Employees' Provident Funds & Miscellaneous Provisions Act, 1952
- Employees' State Insurance Act, 1948
- Payment of Gratuity Act, 1972
- Payment of Bonus Act, 1965
- Maternity Benefit Act, 1961 (amended 2017)
- Factories Act, 1948
- Shops & Establishments Act (state-specific)
- Minimum Wages Act, 1948
- Payment of Wages Act, 1936
- Contract Labour (Regulation & Abolition) Act, 1970
- Equal Remuneration Act, 1976
- Sexual Harassment of Women at Workplace (Prevention, Prohibition & Redressal) Act, 2013 (POSH)
- Digital Personal Data Protection Act, 2023 (DPDP)
- Industrial Relations Code, 2020 (Labour Codes — upcoming)
- Code on Wages, 2019 (Labour Codes)
- Social Security Code, 2020 (Labour Codes)
- Occupational Safety, Health & Working Conditions Code, 2020

---

*Document Prepared by:* HR Module Design Team  
*Standard:* Enterprise ERP Best Practice  
*Review Cycle:* Quarterly  
*Last Updated:* May 2026
