# Requirements Document

## Introduction

This document specifies requirements for completing the Dograh Admin/User Panel system. The current implementation is 30% complete with core infrastructure in place. This spec covers the remaining 70% of features needed for production launch.

**Background:** Dograh is a voice AI platform for building conversational agents with telephony support. The admin/user panel transformation enables the platform owner (admin) to manage all AI provider keys centrally, while users only select providers/models without entering credentials. This shifts Dograh from a BYOK-only model to a managed platform similar to Vapi and Retell.

**Current State:**
- ✅ Core admin key infrastructure (encryption, storage, injection service)
- ✅ Basic admin routes (4/15): analytics, users, orgs, providers  
- ✅ Basic admin UI (5/25 pages): dashboard, users, orgs, runs, providers
- ✅ User model config updated (API key fields removed)
- ✅ 1 database table created (global_settings)

**Scope:** This specification covers:
- 11 admin backend route files
- 20 admin frontend pages
- 9 new database tables + column additions
- 22 user panel enhancements
- 4 supporting services (audit, notifications, credit management, email templates)

**Out of Scope:**
- Mobile apps
- Real-time call monitoring (join/listen/barge)
- Advanced RBAC (future phase)
- Third-party integrations beyond Stripe/SMTP

---

## Requirements

### 2.1 Admin - Call Moderation System

**US-ADMIN-001: View All Platform Calls**

As an admin, I need to see all calls across all users/orgs so I can monitor platform usage and detect issues.

**Acceptance Criteria:**
- Display paginated table of all calls (existing CallModel/WorkflowRunModel records)
- Columns: timestamp, caller/callee, user/org owner, status, duration, workflow, disposition
- Filters: status, direction (inbound/outbound), date range, user/org, phone number
- Search: run ID, user email, org name, phone number
- Inline recording player (play without leaving page)
- Actions per row: View Detail, Ban User, Flag Call, Delete
- CSV export with all visible columns
- Real-time updates (30s polling or SSE)
- Route: GET `/admin/calls`

**Business Rules:**
- Only accessible to is_superuser=True users
- Must handle 100k+ call records efficiently (pagination required)
- Recordings load from existing MinIO storage
- Delete requires confirmation dialog showing call details

---

**US-ADMIN-002: Call Detail & Moderation Actions**

As an admin, I need detailed call information with moderation tools so I can take action on problematic calls.

**Acceptance Criteria:**
- Full call detail page with tabs: Overview, Transcript, Events, Owner Info
- Transcript viewer: speaker-separated segments with timestamps
- Recording player with waveform visualization
- AI-generated summary, sentiment analysis, classification
- Call events timeline: transfers, tool calls, errors
- Owner information: user/org details with links
- Moderation sidebar with actions:
  - Ban User (with reason modal, updates users.status='banned')
  - Flag Call (severity dropdown, creates violation record)
  - Admin Notes (free text, saved to call metadata)
- Action history: previous admin actions on this call
- Route: GET `/admin/calls/{run_id}`

**Business Rules:**
- Banned users cannot make new calls (enforced in workflow execution)
- Flagging creates violation record for moderation queue
- Admin notes append-only (never delete, show timestamp + admin name)
- Actions logged to admin_audit_logs table

---

**US-ADMIN-003: Moderation Queue for Violations**

As an admin, I need a queue of flagged/violating calls so I can review and action them efficiently.

**Acceptance Criteria:**
- Table of calls with violations or flags
- Columns: call time, user/org, violation reason, severity, status, flagged by
- Filters: severity (low/medium/high/critical), status (pending/reviewed/actioned/dismissed)
- Per-row actions: View Call Detail, Ban User, Dismiss, Add Note
- Bulk actions: Dismiss Selected, Mark Reviewed
- Status badges with color coding
- Route: GET `/admin/calls/violations`

**Business Rules:**
- Violations auto-created when calls contain banned words (speech analysis)
- Status workflow: pending → reviewed → actioned/dismissed
- Dismissed violations hidden from queue but logged
- Severity inherits from banned_words.severity

---

### 2.2 Admin - Content Moderation

**US-ADMIN-004: Manage Banned Words**

As an admin, I need to configure banned words/phrases so the system can auto-flag violating calls.

**Acceptance Criteria:**
- CRUD table for banned words
- Columns: phrase, severity (low/medium/high/critical), enabled, created_at
- Actions: Create, Edit, Delete, Enable/Disable
- Import CSV (phrase, severity columns)
- Export CSV
- Search/filter by severity, enabled status
- Route: GET/POST/PATCH/DELETE `/admin/content/banned-words`

**Business Rules:**
- Phrases case-insensitive match in transcripts
- Severity determines violation priority
- Disabled words don't trigger violations
- Existing calls not retroactively flagged
- Integration point: call pipeline checks transcript against active banned words

---

### 2.3 Admin - Workflows Management

**US-ADMIN-005: View All Workflows**

As an admin, I need to see all workflows across the platform so I can monitor usage and take action.

**Acceptance Criteria:**
- Table of all WorkflowModel records
- Columns: name, owner (user/org), status (idle/running/failed), total runs, created, last modified
- Filters: owner, status, date range
- Search: workflow name, owner email
- Actions per row: View (link to editor), Disable, Delete
- Disable toggle updates workflows.is_active = false
- Route: GET `/admin/workflows`

**Business Rules:**
- Disabled workflows cannot be executed (enforced in workflow execution service)
- Delete requires confirmation showing run count
- View opens workflow in editor (read-only for admin)

---

### 2.4 Admin - Billing System

**US-ADMIN-006: Manage Credit Packages**

As an admin, I need to create credit packages so users can purchase credits at different price points.

**Acceptance Criteria:**
- CRUD for credit_packages table
- Fields: name, credits amount, price USD, badge text, features JSON, enabled, display_order
- Create/Edit modal with fields
- Drag-to-reorder for display_order
- Preview how package appears on user billing page
- Enabled toggle (hide from users without deleting)
- Route: GET/POST/PATCH/DELETE `/admin/billing/packages`

**Business Rules:**
- Badge examples: "Popular", "Save 20%", "Best Value"
- Features JSON array displayed as bullet points on user UI
- Disabled packages not shown to users
- Existing packages can't be deleted if referenced in transactions
- Price changes don't affect past purchases

---

**US-ADMIN-007: Manage Subscription Plans**

As an admin, I need to define subscription plans so users have different tier limits.

**Acceptance Criteria:**
- CRUD for plans table
- Fields: key, display_name, max_workflows, max_phone_numbers, max_concurrent_calls, included_credits_monthly, allow_custom_models, support_tier, enabled, display_order
- Create/Edit modal
- Plan keys: free, pro, enterprise, custom
- Enabled toggle
- Route: GET/POST/PATCH/DELETE `/admin/billing/plans`

**Business Rules:**
- Plan limits enforced in workflow creation, phone number purchase, call initiation
- included_credits_monthly auto-added on billing cycle (future feature, store now)
- allow_custom_models determines if user can configure BYOK
- Free plan always exists (default for new users)

---

**US-ADMIN-008: View Transactions Ledger**

As an admin, I need to see all credit transactions so I can track revenue and usage.

**Acceptance Criteria:**
- Table of transactions
- Columns: timestamp, user/org, type (purchase/usage_debit/manual_adjust/refund), credits delta, amount USD, reference
- Filters: user/org, type, date range, amount min/max
- CSV export
- Per-row: view reference (link to invoice or call)
- Route: GET `/admin/billing/transactions`

**Business Rules:**
- Purchase type: user bought credits
- Usage debit: credits deducted after call
- Manual adjust: admin added/removed credits
- Refund: admin reversed purchase
- Negative credits allowed (debt tracking)

---

**US-ADMIN-009: Bulk Credit Backfill**

As an admin, I need to bulk-add credits so I can grant bonuses or fix issues.

**Acceptance Criteria:**
- Two modes: By Plan, By CSV
- By Plan: select plan(s), enter credits, note; preview user count, apply
- By CSV: upload (email, credits columns), preview with error highlighting (invalid emails), apply
- Confirmation dialog before apply
- Creates transaction records with type='manual_adjust'
- Shows success summary after apply
- Route: POST `/admin/billing/backfill`

**Business Rules:**
- Creates one transaction per user
- Admin note required (audit trail)
- Auto-logs to admin_audit_logs
- CSV errors: invalid email, user not found, negative credits

---

### 2.5 Admin - Platform Settings

**US-ADMIN-010: Configure General Platform Settings**

As an admin, I need 18+ global settings so I can control platform behavior.

**Acceptance Criteria:**
- Form with 18 settings (saved to global_settings table as key-value pairs)
- Settings:
  1. app_name (string)
  2. default_plan (dropdown: free/pro/enterprise)
  3. default_credits_new_user (number)
  4. enable_signup (boolean toggle)
  5. maintenance_mode (boolean toggle + banner text)
  6. support_email (email)
  7. support_url (URL)
  8. price_per_second_default (decimal)
  9. min_credit_purchase (number)
  10. invoice_prefix (string)
  11. invoice_starting_number (number)
  12. system_timezone (dropdown)
  13. referral_bonus_credits (number)
  14. low_credit_threshold (number)
  15. enable_telephony_providers (multi-select)
  16. credit_burn_rate_multiplier (decimal)
  17. custom_html_head (textarea)
  18. custom_html_body (textarea)
- Save All button
- Reset to Defaults button
- Route: GET/PATCH `/admin/settings/general`

**Business Rules:**
- maintenance_mode=true shows banner on user pages + returns 503 on API (except admin routes)
- enable_signup=false hides signup form
- price_per_second_default used when org has no custom pricing
- low_credit_threshold triggers email notification
- custom_html allows analytics scripts injection

---

**US-ADMIN-011: Configure Branding**

As an admin, I need to customize branding so the platform matches my brand.

**Acceptance Criteria:**
- Upload fields: Logo (light mode), Logo (dark mode), Favicon
- Primary color picker (hex)
- Welcome greeting text (shown on login/dashboard)
- Footer links editor (add/edit/delete): Label, URL, Open in new tab
- Preview panel showing changes
- Save button uploads to MinIO + saves URLs to global_settings
- Route: GET/PATCH `/admin/settings/branding` + POST `/admin/settings/branding/upload`

**Business Rules:**
- Logo max size 2MB, formats: PNG, SVG, JPEG
- Favicon max size 512KB, format: ICO, PNG
- Primary color generates CSS variables for buttons, links, highlights
- Changes reflect immediately after save (BrandingProvider reads from global_settings)

---

**US-ADMIN-012: Configure SMTP & Email Templates**

As an admin, I need SMTP config and email templates so the platform sends branded emails.

**Acceptance Criteria:**
- SMTP Config section:
  - Host, Port, Security (none/SSL/TLS), Username, Password, From Name, From Email
  - Test Email button (enter recipient, sends test)
  - Save SMTP Config button
- Email Templates section:
  - List of template keys: welcome_email, password_reset, credit_purchase_receipt, credit_low_alert, invoice_generated
  - Per template: Subject field, HTML body WYSIWYG editor
  - Variable legend sidebar ({{user_name}}, {{credits}}, {{invoice_url}}, etc.)
  - Preview button (renders with sample data)
  - Test Send button (enter email, sends rendered template)
  - Save Template button
- Route: GET/PATCH `/admin/settings/email`

**Business Rules:**
- SMTP credentials encrypted in global_settings
- Templates stored as HTML with Jinja2-style variables
- Missing variables in template show warnings
- Test email uses real SMTP config
- Templates fallback to system defaults if not customized

---

**US-ADMIN-013: Configure Model Allowlist & Pricing**

As an admin, I need to control which models users see and override pricing.

**Acceptance Criteria:**
- Table of all models from registry.py (grouped by provider + service type)
- Columns: Provider, Service Type (LLM/TTS/STT), Model, Visibility (show/hidden), Premium Only, Price Override
- Filters: provider, service type, visibility, premium
- Per-row actions: Hide/Show toggle, Mark Premium toggle, Edit Pricing (modal)
- Pricing modal: price per 1k tokens (LLM), price per minute (TTS/STT)
- Save All button
- Route: GET/PATCH `/admin/settings/models`

**Business Rules:**
- Hidden models not shown in user model picker even if provider key exists
- Premium only models require user plan.allow_custom_models=true
- Price overrides used in credit burn calculation (duration * price_override)
- Defaults from registry.py if no override set

---

**US-ADMIN-014: Configure Languages**

As an admin, I need to enable/disable languages so users see only supported locales.

**Acceptance Criteria:**
- Table of 20+ languages
- Columns: Flag icon, Language name, Enabled toggle, Default (radio)
- Enable/Disable per language
- Set Default Language (radio buttons)
- Save button
- Route: GET/PATCH `/admin/settings/languages`

**Business Rules:**
- Default language used for new users
- Disabled languages not shown in user locale picker
- At least one language must be enabled
- English cannot be disabled

---

### 2.6 Admin - Supporting Features

**US-ADMIN-015: Monitor Batch Jobs**

As an admin, I need to see running batch jobs so I can track campaign progress and cancel stuck jobs.

**Acceptance Criteria:**
- Table of running jobs
- Columns: job ID, type (campaign/KB_indexing/import), owner, status, progress %, last update, error message
- Filters: type, status, owner
- Auto-refresh every 10s
- Actions per row: View Detail (link to campaign/KB), Cancel Job
- Route: GET `/admin/jobs`

**Business Rules:**
- Jobs tracked via existing ARQ queue system
- Campaign jobs link to campaign detail page
- Cancel job sets status=cancelled in queue
- Completed jobs removed from list after 1 hour

---

**US-ADMIN-016: Broadcast Notifications**

As an admin, I need to send platform-wide notifications so I can announce updates/maintenance.

**Acceptance Criteria:**
- Create Notification form:
  - Title, Message (markdown), Icon picker (9 options), Link URL
  - Display Style (bell only / top banner / both)
  - Priority (1-10), Dismissible toggle, Expiry date/time
  - Preview panel
  - Send button
- History table below form:
  - Past notifications, sent date, # users viewed, expires at
  - Actions: Resend, Delete
- Route: POST/GET `/admin/notifications`

**Business Rules:**
- Creates notification record + notification_deliveries for all active users
- Bell-only: shows in notification dropdown
- Top banner: dismissible banner across top of all pages
- Expiry auto-hides notification
- Viewed tracked per user in notification_deliveries

---

**US-ADMIN-017: View Admin Audit Log**

As an admin, I need an immutable audit log so I can track who changed what.

**Acceptance Criteria:**
- Read-only table of admin_audit_logs
- Columns: timestamp, admin user, action type, target type, target ID, IP, summary
- Filters: admin user, action type, date range, target type
- Search: summary text, target ID
- CSV export
- No edit/delete actions (immutable)
- Route: GET `/admin/audit-log`

**Business Rules:**
- Middleware auto-logs all POST/PATCH/DELETE to /admin/* routes
- Summary auto-generated: "User {id} banned by admin {id}", "Credits adjusted: user {id} +500"
- IP captured from request
- Never delete records (compliance)

---

### 2.7 User Panel - Dashboard & Core

**US-USER-001: Enhanced Dashboard with KPIs**

As a user, I need a rich dashboard so I see my activity at a glance.

**Acceptance Criteria:**
- Personalized greeting (Good morning/afternoon/evening {name})
- 12 KPI cards: Total Calls, This Week vs Last Week %, Inbound, Outbound, Campaign Success Rate %, Appointments Booked, Forms Submitted, Total Contacts, KB Articles, Workflows Count, Credits Balance, Current Plan
- Weekly area chart: incoming vs outgoing calls (7 days)
- Lead status donut chart: Hot/Warm/Cold/Lost counts
- Sentiment donut chart: Positive/Neutral/Negative
- Recent calls table (5 rows with recording player)
- Recent contacts table (5 rows)
- Quick action buttons: New Workflow, New Campaign, Buy Credits
- Route: GET `/overview`

**Business Rules:**
- KPIs query user's org data only
- Trends compare current 7 days vs previous 7 days
- Charts update on page load (no real-time)
- Credits balance prominent (always visible)

---

**US-USER-002: Campaigns Management**

As a user, I need to create and manage campaigns so I can make outbound call batches.

**Acceptance Criteria:**
- List page with grid/list toggle
- Campaign cards show: name, status, progress bar, % success, scheduled date
- Tabs: Active / Draft / Completed / Trashed
- Create Campaign dialog: name, contact list (CSV/paste/add), workflow, scheduled date
- Actions: Edit, Clone, Delete, Start, Pause, Resume, Stop
- Detail page: summary stats, contacts table (status/recording/transcript per contact), retry failed button, export results CSV
- Routes: GET/POST/PATCH/DELETE `/campaigns`, GET `/campaigns/{id}`

**Business Rules:**
- Draft campaigns not started yet
- Scheduled campaigns start at scheduled_date
- Running campaigns show live progress
- Completed campaigns read-only except notes
- Trashed campaigns soft-deleted (can restore)
- Contacts pulled from contacts table or uploaded

---

**US-USER-003: CRM with Kanban View**

As a user, I need a CRM so I can track and manage leads.

**Acceptance Criteria:**
- Kanban board with customizable stages (Hot/Warm/Cold/Appointment Booked/Closed)
- List view toggle (table format)
- Lead cards: name, phone, AI category, score 0-100, source, sentiment badge
- Lead detail drawer: transcript, recording, notes, activity timeline, custom fields, tags
- Bulk actions: change stage, add tags, delete, export CSV
- Import CSV / Export CSV buttons
- Stage editor: add/edit/delete/reorder stages
- CRM Analytics tab: leads-by-stage bar, by source, by date, conversion funnel, average score, sentiment breakdown
- Routes: GET/POST/PATCH/DELETE `/contacts`, GET/PATCH `/contacts/stages`

**Business Rules:**
- Contacts per org only
- Drag-drop to change stages
- Score auto-calculated from call analysis (future, manual for now)
- Source: manual/campaign/inbound call/import
- Custom fields JSON (flexible schema)

---

**US-USER-004: Call History**

As a user, I need to see my call history so I can review past conversations.

**Acceptance Criteria:**
- Table: dialed number/caller, status, direction, duration, disposition, agent (workflow), recording icon, date
- Filters: status, direction, date range, workflow
- Search: phone number, call ID
- Export CSV
- Detail page: recording player with waveform, transcript (speaker-separated), AI summary, sentiment, classification, workflow link, editable notes
- Routes: GET `/calls`, GET `/calls/{id}`

**Business Rules:**
- Shows user's org calls only
- Recordings load from MinIO
- Notes saved to call metadata
- No moderation tools (user view)

---

**US-USER-005: Deep Analytics**

As a user, I need deep analytics so I can measure performance.

**Acceptance Criteria:**
- Date range selector: 30/90/365 days
- Charts:
  - Calls per day area chart
  - Avg duration line chart
  - Inbound vs outbound stacked bar
  - Lead conversion funnel
  - Workflow performance rank table
  - Campaign performance rank table
  - Cost breakdown by model/day bar
  - Savings vs human agents estimate card
- Export data CSV button
- Route: GET `/analytics`

**Business Rules:**
- All data scoped to user's org
- Cost calculated from transactions (usage_debit)
- Savings estimate: (total minutes * $0.50 per minute) - actual credits spent

---

**US-USER-006: Enhanced Billing**

As a user, I need a comprehensive billing page so I can manage credits and subscriptions.

**Acceptance Criteria:**
- Tabs: Overview, Buy Credits, Transactions, Invoices
- Overview tab: current plan badge, quota progress bars (workflows/numbers/minutes used vs limit), payment methods, billing info edit button
- Buy Credits tab: credit packages grid (from admin config), click opens Stripe/payment modal, receipt email after purchase, transaction record created
- Transactions tab: list of purchases + debits, PDF download per transaction
- Invoices tab: list, PDF download
- Route: GET `/billing`

**Business Rules:**
- Quota bars show used/max from plan
- Credit packages pull from credit_packages table (enabled=true only)
- Payment via Stripe (existing integration)
- Transaction created with type=purchase
- Invoice auto-generated and emailed

---

### 2.8 User Panel - Settings

**US-USER-007: User Profile Settings**

As a user, I need profile settings so I can manage my account.

**Acceptance Criteria:**
- Avatar upload, First name, Last name, Display name, Email (verified badge), Phone, Timezone, Language
- Change Password section: old password, new password, confirm
- Delete Account button (2-step confirmation with warning)
- Save button
- Route: GET/PATCH `/settings/profile`

**Business Rules:**
- Email change requires verification
- Password requires old password validation
- Delete account soft-deletes user + transfers orgs to remaining owner

---

**US-USER-008: Team Management**

As a user, I need team management so I can invite org members.

**Acceptance Criteria:**
- Table: name, email, role (Owner/Admin/Agent/Viewer), joined date
- Pending invites section: email, role, sent date, Resend/Cancel buttons
- Invite Member button: modal with email + role dropdown
- Actions per row: Change Role, Remove Member
- Route: GET/POST/PATCH/DELETE `/settings/team`

**Business Rules:**
- Uses organization_users_association table
- Owner cannot be removed (transfer ownership first)
- Roles enforce permission levels (future: implement RBAC)

---

### 2.9 Supporting Services

**REQUIREMENT-SVC-001: Admin Audit Middleware**

System must auto-log all admin actions for compliance.

**Technical Requirements:**
- Starlette middleware: `middleware/admin_audit.py`
- Intercept all POST/PATCH/DELETE requests to `/admin/*`
- Extract: admin user ID, action type (create/update/delete), target type + ID, request IP, auto-generate summary
- Write to admin_audit_logs table
- Non-blocking (async insert)

---

**REQUIREMENT-SVC-002: Notification Broadcast Service**

System must deliver notifications to all users efficiently.

**Technical Requirements:**
- Service: `services/notification_service.py`
- Function: `broadcast_notification(title, message, icon, link, display_type, priority, dismissible, expires_at)`
- Creates notification record
- Creates notification_deliveries for all active users (status='active')
- Returns notification ID
- Non-blocking (ARQ background task)

---

## 3. Database Schema Requirements

### 3.1 New Tables

**Table: admin_audit_logs**
```sql
CREATE TABLE admin_audit_logs (
  id SERIAL PRIMARY KEY,
  admin_user_id INTEGER NOT NULL REFERENCES users(id),
  action_type VARCHAR(50) NOT NULL,
  target_type VARCHAR(50) NOT NULL,
  target_id INTEGER,
  ip_address VARCHAR(45),
  summary_json JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_audit_admin ON admin_audit_logs(admin_user_id);
CREATE INDEX idx_audit_created ON admin_audit_logs(created_at DESC);
```

**Table: credit_packages**
```sql
CREATE TABLE credit_packages (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  credits INTEGER NOT NULL,
  price_usd DECIMAL(10,2) NOT NULL,
  badge VARCHAR(50),
  features_json JSONB,
  enabled BOOLEAN DEFAULT TRUE,
  display_order INTEGER DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Table: plans**
```sql
CREATE TABLE plans (
  id SERIAL PRIMARY KEY,
  key VARCHAR(50) UNIQUE NOT NULL,
  display_name VARCHAR(100) NOT NULL,
  max_workflows INTEGER,
  max_phone_numbers INTEGER,
  max_concurrent_calls INTEGER,
  included_credits_monthly INTEGER DEFAULT 0,
  allow_custom_models BOOLEAN DEFAULT FALSE,
  support_tier VARCHAR(50),
  enabled BOOLEAN DEFAULT TRUE,
  display_order INTEGER DEFAULT 0
);
```

**Table: transactions**
```sql
CREATE TABLE transactions (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  org_id INTEGER REFERENCES organizations(id),
  type VARCHAR(50) NOT NULL,
  credits_delta INTEGER NOT NULL,
  currency_amount_usd DECIMAL(10,2),
  reference_type VARCHAR(50),
  reference_id INTEGER,
  admin_note TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_transactions_user ON transactions(user_id);
CREATE INDEX idx_transactions_org ON transactions(org_id);
CREATE INDEX idx_transactions_created ON transactions(created_at DESC);
```

**Table: banned_words**
```sql
CREATE TABLE banned_words (
  id SERIAL PRIMARY KEY,
  phrase VARCHAR(200) NOT NULL,
  severity VARCHAR(20) NOT NULL,
  enabled BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_banned_enabled ON banned_words(enabled);
```

**Table: violations**
```sql
CREATE TABLE violations (
  id SERIAL PRIMARY KEY,
  call_id INTEGER REFERENCES workflow_runs(id),
  user_id INTEGER REFERENCES users(id),
  detected_phrase VARCHAR(200),
  severity VARCHAR(20),
  status VARCHAR(50) DEFAULT 'pending',
  reviewed_by INTEGER REFERENCES users(id),
  reviewed_at TIMESTAMP WITH TIME ZONE,
  action_taken VARCHAR(100),
  notes_json JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_violations_status ON violations(status);
CREATE INDEX idx_violations_call ON violations(call_id);
```

**Table: lead_stages**
```sql
CREATE TABLE lead_stages (
  id SERIAL PRIMARY KEY,
  org_id INTEGER REFERENCES organizations(id),
  name VARCHAR(100) NOT NULL,
  color VARCHAR(7),
  display_order INTEGER DEFAULT 0,
  is_default BOOLEAN DEFAULT FALSE,
  is_custom BOOLEAN DEFAULT TRUE
);
CREATE INDEX idx_stages_org ON lead_stages(org_id);
```

**Table: notifications**
```sql
CREATE TABLE notifications (
  id SERIAL PRIMARY KEY,
  title VARCHAR(200) NOT NULL,
  message TEXT NOT NULL,
  icon VARCHAR(50),
  link VARCHAR(500),
  display_type VARCHAR(50),
  priority INTEGER DEFAULT 5,
  dismissible BOOLEAN DEFAULT TRUE,
  expires_at TIMESTAMP WITH TIME ZONE,
  created_by INTEGER REFERENCES users(id),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Table: notification_deliveries**
```sql
CREATE TABLE notification_deliveries (
  id SERIAL PRIMARY KEY,
  notification_id INTEGER REFERENCES notifications(id) ON DELETE CASCADE,
  user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
  viewed_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_delivery_user ON notification_deliveries(user_id);
CREATE INDEX idx_delivery_notif ON notification_deliveries(notification_id);
```

### 3.2 Column Additions

**Table: workflows**
```sql
ALTER TABLE workflows ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
```

**Table: organizations**
```sql
ALTER TABLE organizations ADD COLUMN status VARCHAR(20) DEFAULT 'active';
```

**Table: users**
```sql
ALTER TABLE users ADD COLUMN status VARCHAR(20) DEFAULT 'active';
ALTER TABLE users ADD COLUMN plan_type VARCHAR(50) DEFAULT 'free';
ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE users ADD COLUMN last_login_ip VARCHAR(45);
```

---

## 4. Non-Functional Requirements

### 4.1 Performance
- Admin dashboard loads in < 2s with 100k users
- Call list pagination handles 1M+ records
- Audit log queries optimized with indexes
- Real-time updates use SSE or 30s polling

### 4.2 Security
- Admin routes enforce is_superuser + admin@admin.com
- SMTP credentials encrypted in global_settings
- Admin audit log immutable (append-only)
- User banning enforced in workflow execution layer
- CSRF protection on all state-changing endpoints

### 4.3 Scalability
- Notification broadcast uses background jobs (ARQ)
- Credit backfill processes in batches (100 users at a time)
- Call recordings lazy-load (not in table query)

### 4.4 Usability
- Admin UI responsive (desktop + tablet)
- Inline recording players (no page navigation)
- Confirmation dialogs on destructive actions
- Loading states on all async operations
- Toast notifications on success/error

---

## 5. Integration Points

### 5.1 Existing Systems
- **GlobalSettingsClient:** Used for all admin settings storage
- **MinIO Storage:** Recording uploads, logo/favicon uploads
- **ARQ Queue:** Background jobs (campaigns, notifications, backfill)
- **Stripe:** Credit package purchases
- **Email Service:** SMTP for templates (welcome, receipts, alerts)
- **Workflow Execution:** Enforces user.status=banned, workflows.is_active checks

### 5.2 New Service Dependencies
- **Admin Audit Middleware:** Logs to admin_audit_logs
- **Notification Service:** Creates notifications + deliveries
- **Credit Service:** Deducts credits after calls, adds on purchase

---

## 6. Edge Cases & Error Handling

### 6.1 Billing
- Negative credit balance allowed (debt tracking)
- Purchase fails if Stripe errors → show error, don't create transaction
- Manual adjust requires admin note (validation)
- Backfill CSV with invalid emails → show errors, don't apply

### 6.2 Moderation
- Ban user mid-call → call continues, future calls blocked
- Delete call with violations → violations remain (orphaned, show call deleted)
- Banned word disabled → existing violations not dismissed

### 6.3 Settings
- Maintenance mode → show banner + 503 on API (admin routes exempt)
- SMTP test email fails → show error, don't save config
- Logo upload > 2MB → validation error
- Delete default plan → validation error (must have default)

### 6.4 Notifications
- Expired notifications auto-hidden
- Deleted notification → deliveries cascade delete
- Broadcast to 10k users → background job (don't block)

---

## 7. Testing Requirements

### 7.1 Unit Tests
- Admin audit middleware logs correctly
- Credit calculation logic (price_per_second * duration)
- Banned word matching (case-insensitive)
- Notification expiry logic

### 7.2 Integration Tests
- Admin bans user → user cannot create workflow runs
- Credit purchase → transaction created + balance updated
- Bulk backfill → all users receive credits + audit log entry
- Email template rendering with variables

### 7.3 End-to-End Tests
- Admin login → view calls → ban user → verify user blocked
- User creates campaign → admin views in jobs monitor
- User buys credits → transaction shows in admin ledger

---

## Glossary

- **Admin:** Platform owner with is_superuser=True and email=admin@admin.com
- **BYOK:** Bring Your Own Key - users can optionally configure their own AI provider keys
- **Credit:** Virtual currency users purchase to pay for platform usage
- **Disposition:** Call outcome classification (e.g., appointment booked, interested, not interested)
- **Moderation Queue:** List of flagged calls requiring admin review
- **Plan:** Subscription tier defining user limits (free, pro, enterprise)
- **Transaction:** Record of credit addition or deduction
- **Violation:** Call that triggered content moderation rules (banned words)
- **Workflow:** Voice AI agent configuration (synonym: agent)

---

## Acceptance Criteria Summary

✅ This requirements document is complete when:
- All 25+ user stories defined with acceptance criteria
- Business rules specified for each requirement
- Database schema defined for 9 tables + 4 column additions
- Non-functional requirements documented (performance, security, scalability, usability)
- Integration points with existing systems specified
- Edge cases and error handling covered
- Testing requirements defined
- Glossary provided for domain terms

**Status:** ✅ COMPLETE - Ready for design phase

**Next Step:** Create design.md with API contracts, database migrations, component architecture, and implementation tasks.
