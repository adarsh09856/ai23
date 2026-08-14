# Dograh / KodeWaves - Revised Admin & User Panel Implementation Plan

> **Architectural Principle: DO NOT copy AgentLabs / caiagent pool/engine/plugin architecture.**
> Dograh already has a **fully working native telephony + STT/TTS/LLM provider registry system** in `api/services/configuration/registry.py` (30+ providers). Build on top of that.

---

## Table of Contents

1. [PART 0: What to REMOVE from the old plan (AgentLabs anti-patterns)](#part-0-what-to-remove-from-the-old-plan)
2. [PART 1: Core Concept - Admin-Managed Provider Keys](#part-1-core-concept---admin-managed-provider-keys)
3. [PART 2: Admin Panel - Revised Feature Matrix (26 modules)](#part-2-admin-panel-revised-feature-matrix-26-modules)
4. [PART 3: User Panel - Revised Feature Matrix (22 modules)](#part-3-user-panel-revised-feature-matrix-22-modules)
5. [PART 4: Backend New Files (18 route files)](#part-4-backend-new-files)
6. [PART 5: Frontend New Files (Estimate ~90 pages/components)](#part-5-frontend-new-files)
7. [PART 6: Execution Phases (7 phases)](#part-6-execution-phases)

---

## PART 0: What to REMOVE from the old plan (AgentLabs anti-patterns)

These features are **cancelled / explicitly rejected** because they assume a caiagent-style engine pool architecture that Dograh doesn't use:

| Cancelled Feature | Reason |
|-------------------|--------|
| **02. Voice AI Engine Status** (Plivo/Twilio engine cards) | Dograh telephony already uses provider registry via `TelephonyConfigurationModel`; no separate "engine". Reuse the native telephony page health. |
| **19. KYC Settings** (Twilio KYC, Plivo KYC) | Not applicable to Dograh's architecture; user/provider-owned. |
| **20. Service Connection Tests** (per-key Test Twilio/11Labs/OAI buttons) | Dograh configuration has `last_validated_at`; validation is already done by BYOK save endpoint; no separate "connection test" UI pattern needed â€” reuse validation. |
| **21. Telephony: Twilio Credentials (global admin)** | Telephony is already org-scoped via `telephony_configurations` table with pluggable providers (Twilio/Plivo/Telnyx/Vonage/Vobiz/ARI/Cloudonix) in `services/telephony/providers/*`. Admin provides global pool via the existing system â€” do NOT create a parallel credentials store. |
| **23. AI: ElevenLabs Pool** (key rotation UI) | Dograh **already supports rotating API keys natively**: `BaseServiceConfiguration.api_key: str \| list[str]` in `registry.py` L132, with `random.choice` on access (L149). Just reuse the existing list-input field already present in `ServiceConfigurationForm`. |
| **24. AI: OpenAI Pool** (key rotation UI) | Same reason â€” Dograh native API key list + random choice already built into registry. |
| **26. Google OAuth (admin master settings)** | Auth provider; handled by local auth. Skip for now; separate epic. |
| **32. REST API Keys (admin)** | Separate future work; users already have org-scoped `api_keys` table. Admin has superuser JWT so no immediate need. |
| **33. Plugin Installer** (drag-drop .zip, migrations, enable/disable) | Dograh has a git monorepo + alembic migrations; no plugin infrastructure required. Monolithic codebase is intentional for this architecture. |
| **34. System** (server info, auto-restart, disk/memory bars) | Infrastructure dashboard is DevOps concern, not app UI. Runbooks / monitoring dashboard not in application scope. |
| **35. System Update** (check/update/rollback UI) | Deploy with Docker/CI; application-level update UI is fragile and creates security risk. |
| **36. Phone Numbers (System Pool)** (admin "own" numbers) | Phone numbers already org-scoped via `telephony_phone_numbers` table. System-owned numbers are stored + assigned in the same table with `organization_id = NULL` + assigned status. Reuse existing telephony routes `api/routes/telephony.py`. |
| **37. Add System Number** (buy from Twilio/Plivo via admin) | Same - reuse org telephony routes; add admin scope "assign/unassign org" button on top of existing number records. |
| **User U13. SIP Gateways** page | Dograh telephony registry already has `ARI` and generic providers via `services/telephony/providers/*`; SIP routing is provider-level config, not a separate user-facing page. Remove standalone SIP UI. |
| **User U14. Incoming Connections** page | Same - inbound routing is already configured on `TelephonyPhoneNumberModel.inbound_workflow_id` column (L279-283 models.py). Don't create a parallel concept; surface as an "Inbound Route" column in the existing Phone Numbers page. |
| **Admin 45. Team Login (sub-admin RBAC)** | Superuser role (`is_superuser = True` on `UserModel`) is sufficient for v1. Sub-admin granular RBAC is future-phase 8. |
| **Admin 46. Webhooks Setup (global)** | User/org-level webhooks handled first. Global webhooks are post-launch. |
| **MPS proxy / Dograh Service Keys (mps_sk_...)** | We are building an admin-managed key platform. Admin holds all provider keys. MPS (`services.dograh.com`) and Dograh Service Keys are not used. Remove: `mps_service_key_client.py` MPS calls, `mps_sk_` service key section from Developer page, `DOGRAH_MPS_SECRET_KEY` + `MPS_API_URL` env vars, MPS quota checks from `quota_service.py`. Replace with local credit balance deduction. |
| **BYOK key input for users (ServiceConfigurationForm API key fields)** | Users are not entering their own provider keys. Remove API key input fields from user-facing `/model-configurations`. Users see provider+model picker only. Admin enters all keys in the admin panel. |

Also explicitly **reject the caiagent plugin manager / pool manager / engine architecture / key rotation widget designs entirely**. Dograh's native provider registry + BYOK list key is the canonical mechanism.

---

## PART 1: Core Concept - Admin-Managed Provider Keys

### Architecture: Platform Owner (Admin) Holds All AI Keys

This is your own platform deployed on your VPS. You are the platform owner (dmin@admin.com).
You add AI provider keys in the admin panel. Users choose a model and use it — they never touch
any API keys. This is completely separate from app.dograh.com or any external proxy.

---

### How It Works

`
Admin (admin@admin.com)
  -> superadmin panel -> Provider Keys settings
  -> enters: OpenAI key, Grok key, Google Gemini key, Deepgram key,
             ElevenLabs key, Sarvam key, Smallest.ai key, etc.
  -> keys stored in global_settings (new table) per provider

User (your customer)
  -> Models page (/model-configurations)
  -> sees: list of providers/models admin has enabled
  -> selects: e.g. "Google Gemini - gemini-2.0-flash" for LLM
              "Deepgram - aura-2" for TTS
              "Deepgram - nova-3" for STT
  -> NO api key input shown to users at all
  -> workflow runs using admin's stored key for that provider
  -> user billed in platform credits per call/minute
`

**Users see models. Admin owns keys. Billing is yours.**

---

### What to REMOVE from the OSS codebase

The Dograh OSS codebase was built for users to enter their own keys (BYOK) and uses
an external MPS proxy (services.dograh.com) for a "Dograh Managed" option.
Since we are building a platform where admin holds all keys, the following must be removed:

| Remove | Reason |
|--------|--------|
| **Dograh Service Keys (mps_sk_...)** in Developer page | Not needed. Users don't manage model keys at all. Remove the "Dograh Service Keys" card from /api-keys page. |
| **MPS client** (pi/services/mps_service_key_client.py) | Remove all calls to services.dograh.com. Admin keys are stored locally. |
| **MPS quota checks** (pi/services/quota_service.py - mps parts) | Replace MPS credit checks with local credit balance check from organization_usage / global_settings. |
| **DOGRAH_MPS_SECRET_KEY + MPS_API_URL env vars** | Not used anymore. Remove from constants.py. |
| **BYOK key input in Models page** (AIModelConfigurationV2Editor.tsx) | Users should not see API key input fields. Replace with model picker only. |
| **ServiceConfigurationForm API key input fields** | Hide/remove for user-facing config. Keys are admin-only. |
| **provider: dograh special-case in registry** | Admin's keys for each provider are stored under the real provider name (openai, deepgram, etc), not "dograh". |
| **Stack Auth impersonation** (already listed in PART 0) | Already scheduled for removal. |

---

### 1.1 New Data Model: Admin Provider Keys

`python
# NEW table: global_settings (key-value store)
# Admin stores platform-level provider keys here via the admin panel.
#
# Examples of keys stored:
#   platform_provider_key:openai         -> {"api_key": "sk-proj-...", "enabled": true}
#   platform_provider_key:google         -> {"api_key": "AIza...", "enabled": true}
#   platform_provider_key:grok           -> {"api_key": "xai-...", "enabled": true}
#   platform_provider_key:deepgram       -> {"api_key": "...", "enabled": true, "default_tts": true, "default_stt": true}
#   platform_provider_key:elevenlabs     -> {"api_key": "...", "enabled": true}
#   platform_provider_key:sarvam         -> {"api_key": "...", "enabled": true}
#   platform_provider_key:groq           -> {"api_key": "gsk_...", "enabled": true}
#   platform_provider_key:smallest_ai    -> {"api_key": "...", "enabled": true}
#   platform_provider_key:assemblyai     -> {"api_key": "...", "enabled": true}
#   platform_provider_key:azure_openai   -> {"api_key": "...", "endpoint": "https://...", "enabled": true}
#
# Multi-key rotation (admin can add multiple keys per provider):
#   platform_provider_key:openai -> {"api_key": ["sk-proj-abc", "sk-proj-def"], "enabled": true}
#   At runtime: random.choice(api_key list) — same as existing registry behavior.
#
# Per-provider model visibility (which models users can see):
#   platform_provider_models:openai -> {"enabled_models": ["gpt-4o", "gpt-4o-mini"], "default_model": "gpt-4o-mini"}
#   platform_provider_models:google -> {"enabled_models": ["gemini-2.0-flash", "gemini-1.5-pro"], "default_model": "gemini-2.0-flash"}
#
# Global defaults (what new users get pre-selected):
#   platform_default_llm  -> "google"
#   platform_default_tts  -> "deepgram"
#   platform_default_stt  -> "deepgram"
`

---

### 1.2 Config Resolution — Admin Keys Injected at Runtime

When a workflow runs, the config resolution layer injects the admin's stored key:

`python
# api/services/configuration/resolve.py  (NEW logic)
#
# Current flow (BYOK):
#   workflow runs -> reads org's own api_key from organization_configurations
#
# New flow (Admin-managed keys):
#   workflow runs -> reads provider name from org config (e.g. provider="google", model="gemini-2.0-flash")
#              -> looks up admin's platform_provider_key:google from global_settings
#              -> injects api_key at runtime before calling the provider
#              -> user org config stores ONLY: {provider, model} — no api_key field
#
# Fallback: if org has their own api_key stored (from old BYOK config), use it.
#           This allows org-level overrides if admin ever wants to offer that.
`

---

### 1.3 User Config UX — Model Picker, No Key Input

Users see a clean model selection UI, not a credentials form:

`
/model-configurations page

  LLM:
    Provider: [ Google (Gemini) v ]   Model: [ gemini-2.0-flash v ]

  TTS (Text-to-Speech):
    Provider: [ Deepgram v ]          Model: [ aura-2-thalia-en v ]    Voice: [ ... ]

  STT (Speech-to-Text):
    Provider: [ Deepgram v ]          Model: [ nova-3 v ]

  Realtime (optional):
    Provider: [ OpenAI Realtime v ]   Model: [ gpt-4o-realtime-preview v ]

  [ Save Configuration ]
`

- Provider dropdown shows **only providers admin has enabled** (has a key for).
- Model dropdown shows **only models admin has enabled** for that provider.
- No API key fields visible to users.
- If admin has no key for a provider, it doesn't appear in the dropdown.
- Default pre-selection uses admin-configured platform defaults.

---

### 1.4 Admin Provider Keys UI — /superadmin/settings/providers

The admin panel gets a dedicated provider keys management page:

`
/superadmin/settings/providers

  Tabs: LLM | TTS | STT | Embeddings | Realtime

  LLM Tab:
  ┌────────────────────────────────────────────────────────────┐
  │ Provider        │ API Key(s)           │ Models  │ Default │ Status  │
  ├────────────────────────────────────────────────────────────┤
  │ OpenAI          │ sk-proj-****abc [+]  │ 4 of 12 │ [ ]     │ [x] On  │
  │ Google Gemini   │ AIza****xyz [+]      │ 3 of 8  │ [x]     │ [x] On  │
  │ Grok (xAI)      │ xai-****def [+]      │ 2 of 5  │ [ ]     │ [x] On  │
  │ Groq            │ gsk_****ghi [+]      │ 5 of 9  │ [ ]     │ [ ] Off │
  │ Sarvam          │ ****jkl [+]          │ 2 of 3  │ [ ]     │ [x] On  │
  │ Smallest.ai     │ ****mno [+]          │ 1 of 4  │ [ ]     │ [ ] Off │
  │ AWS Bedrock     │ (not configured)     │ —       │ [ ]     │ [ ] Off │
  └────────────────────────────────────────────────────────────┘
  [ + Add Provider ]

  Clicking a row expands:
    - API Key input(s) with [+ Add Key] for rotation (saved masked, never shown again)
    - Test Connection button -> validates key live
    - Model checklist (which models users can see)
    - Set as Default LLM toggle
    - Enable/Disable toggle
`

Same pattern repeated for TTS, STT, Embeddings, Realtime tabs.

---

### 1.5 Developer Page (/api-keys) — Remove Service Keys Section

The "Dograh Service Keys" (mps_sk_...) section must be **removed** from the Developer page.
Users only need **API Keys** (dog_...) for programmatic access to Dograh's REST API.

Updated Developer page has one section only:
- **API Keys** — create/list/revoke org-scoped keys for calling Dograh's REST API

---

### 1.6 Billing — Platform Credits, Not External

Users pay you (the platform owner) in credits. Per call/minute, credits are deducted
from their balance. You set the pricing. This is separate from any external billing.

`
Admin sets in /superadmin/settings/general:
  Price per second (default): 0.001 credits
  Provider-specific pricing overrides:
    GPT-4o: 0.005 credits/sec
    Gemini Flash: 0.002 credits/sec
    Deepgram TTS: 0.001 credits/sec

Users buy credits from /billing (credit packages admin configures in D1).
Per call deduction is calculated from: duration_seconds * price_per_second_for_provider.
`

---

### 1.7 Telephony Provider Reuse Pattern

For telephony config (Twilio/Plivo/etc.), DO NOT create a parallel global_telephony_keys table.

---

## PART 2: Admin Panel - Revised Feature Matrix (26 modules)

### Section A: Foundation & Impersonation Removal

| # | Module | Route | Description | Priority |
|---|--------|-------|-------------|----------|
| A1 | Rip Stack Auth impersonation flow | N/A (delete code) | **DELETE**: `/app/impersonate/route.ts` and `/app/impersonate/route.test.ts`. **DELETE**: Provider ID + Email impersonation forms in `/superadmin/page.tsx`. **DELETE**: `impersonateAsSuperadmin()` util function (lib/utils.ts L109-214). **DELETE**: `/api/superuser/impersonate` endpoint in routes/superuser.py + ImpersonateRequest/Response schemas. Simplify `services/auth/depends.py` to Local Provider only paths. | BLOCKER |
| A2 | Admin route guard | `/admin/*` middleware/layout | Admin routes must be restricted to the reserved platform admin account `admin@admin.com` with `is_superuser = True`. Redirect everyone else to `/overview`. Backend equivalent: make `get_superuser` enforce the same reserved-email rule so the API cannot be reached by other users. | BLOCKER |
| A3 | Admin Shell Layout | `/admin/layout.tsx` | New layout file. Separate `AdminSidebar` component (reuse shadcn/ui Sidebar). Admin header with global search input, notification bell, user avatar + Switch to User Panel button. Footer. | HIGH |
| A4 | Admin Home Dashboard | `/admin/page.tsx` | 10 KPI metric cards. Cards: Total Users, New Signups today, Active now (in calls), Total Organizations, Running Workflows, Total Calls Today, Total Runs This Month, Total Credits Consumed today, Revenue Estimate (monthly), Avg Call Duration. + weekly area chart calls-over-time + pie chart users-by-plan. Live-updating 30s. No engine status cards! | HIGH |
| A5 | Admin Sidebar Nav | Component | Grouped sections: **Overview** (Dashboard), **Users & Orgs** (Users, Organizations), **Content & Calls** (All Calls, Moderation Queue, All Workflows, Global CRM Contacts), **Billing** (Credit Packages, Plans, Transactions), **Platform** (AI Provider Catalog, General Settings, Branding, SMTP & Email, Language & i18n, Batch Jobs Monitor, Broadcast Notifications, Audit Log). | HIGH |

### Section B: Users & Orgs

| # | Module | Route | Description | Priority |
|---|--------|-------|-------------|----------|
| B1 | Users Management | `/admin/users` | Paginated table. Filter: Role (user/admin/superuser), Status (Active/Banned), Plan, Join date, Search email/name. Per-row dropdown: **Edit Profile**, Activate/Deactivate, **Adjust Credits** (+/- modal), Send Password Reset, **Login As** (native JWT mint, short-lived, write session cookie directly - NO impersonation Stack call), Delete. CSV export. Create User modal (Email, temp pwd, Name, Role, Plan, Initial credits, Welcome email toggle). | HIGH |
| B2 | User Detail | `/admin/users/[id]` | Tabs: Overview (profile, join date, last login, IP), Organizations (member of which orgs, role in each), Workflows (owned count, drill link), Calls (recent calls table with recording), Credit Ledger (add/deduct line items with admin note), Activity Timeline (every login, workflow create, purchase). | HIGH |
| B3 | Organizations | `/admin/organizations` | All orgs table. Name, Owner link, #Members, #Workflows, #Phone Numbers, Credit Balance (dograh_tokens concept already on deprecated quota_type but we keep balance), Monthly Spend (calculated), Status. Row actions: Add Credits, Set Custom Price/Second, Activate/Deactivate, Impersonate Owner, Delete. | HIGH |
| B4 | Organization Detail | `/admin/organizations/[id]` | Summary, Members list (invite/change role/remove), Billing & Usage 30-day bar chart, AI Config (current provider/model state and validation status), Workflows table (drill links), API Keys list, Phone Numbers assigned list (with reassign buttons). | MEDIUM |

### Section C: Content & Calls Moderation

| # | Module | Route | Description | Priority |
|---|--------|-------|-------------|----------|
| C1 | All Calls (Runs) | `/admin/calls` | **Replace** existing `/superadmin/runs` with new enhanced page under `/admin`. Search: run ID, user name/org name/phone number dialed. Filter: Status, Direction (Inbound/Outbound), Date range, Owner (user/org). Table columns: Time, Caller/Callee, User/Org, Status, Duration, Workflow link, Recording player (inline play), Disposition (lead classification). Row actions: View Full, Ban User, Flag, Delete. | HIGH |
| C2 | Call Detail & Moderation | `/admin/calls/[id]` | Transcript viewer (speaker-separated segments), Recording with waveform, AI Summary, Sentiment, Classification, Call Events timeline (transfer/tool-calls etc), Owner user/org info. Moderation sidebar: Ban User (modal + reason), Flag call, Admin notes (save). **NO "Join/Listen/Barge" live feature here** â€” separate. | HIGH |
| C3 | Moderation Queue (Violations) | `/admin/calls/violations` | Flagged + banned-word-violating calls list. Severity badge, Violation reason, Review Status (Pending/Reviewed/Actioned/Dismissed). Bulk actions (dismiss all, action selected). Per call Ban/Flag/dismiss. Row links to Call Detail. | MEDIUM |
| C4 | Banned Words | `/admin/content/banned-words` | Simple CRUD table. Phrase, Severity (low/medium/high/critical), Enabled. Import CSV, export CSV. Ingestion into call pipeline filter is existing speech pattern logic. | MEDIUM |
| C5 | All Workflows | `/admin/workflows` | Every workflow/agent across all orgs. Table: Name, Owner (User/Org), Status (Idle/Running/Failed), #Total Runs, Created, Last Modified. Row actions: View (open workflow editor link), Disable (toggle is_active - add workflow-level is_active field if missing), Delete (confirm with run count warning). | MEDIUM |
| C6 | Global CRM Contacts | `/admin/contacts` | All contacts across every org's contact/campaign tables. Filter by owner org/user, source, status, date. Name, Phone, Email, Status, Source, Owner link. No inline edit (read-only aggregate view). CSV export only. | MEDIUM |

### Section D: Billing

| # | Module | Route | Description | Priority |
|---|--------|-------|-------------|----------|
| D1 | Credit Packages CRUD | `/admin/billing/packages` | Packages table. Display name, Credits amount, Price USD, Badge (Popular / Save X%), Features JSON list, Enabled, Order. Create/edit modal. Public pricing page consumes this list. | MEDIUM |
| D2 | Subscription Plans CRUD | `/admin/billing/plans` | Plans table: Free, Pro, Enterprise, Custom. Per-plan fields: Max Workflows allowed, Max Phone Numbers allowed, Max Concurrent Calls cap, Credits included per month, Allowed provider tiers / premium models, Support tier (None/Standard/Priority). Enabled toggle + Display order. | MEDIUM |
| D3 | Transactions Ledger | `/admin/billing/transactions` | Full credit ledger. Type column (Purchase / Usage Debit / Manual Adjust / Refund). Filters: User/Org, Type, Date range, Amount min/max. Download CSV. Per-row: Reference (invoice ID or run ID). | MEDIUM |
| D4 | Credit Backfill (Bulk) | `/admin/billing/backfill` | Two modes: 1) Bulk assign by plan â€” select plan(s) + credits + note, preview count, apply. 2) CSV upload â€” user email + credits columns, preview errors (invalid emails), apply with confirm dialog. Audit log entry created automatically. | LOW |

### Section E: Platform Settings

| # | Module | Route | Description | Priority |
|---|--------|-------|-------------|----------|
| E1 | Admin Provider Keys & Model Catalog | `/superadmin/settings/providers` | **THE CORE feature**. Admin enters actual API keys for all AI providers (OpenAI, Grok/xAI, Google Gemini, Groq, Deepgram, ElevenLabs, Sarvam, Smallest.ai, AssemblyAI, Azure OpenAI, AWS Bedrock, etc.). 5 Tabs: LLM / TTS / STT / Embeddings / Realtime. Per provider: API key input(s) with masking + Test Connection button, model checklist (which models users can see), Set as Default toggle, Enable/Disable. Multi-key rotation supported (list of keys, random.choice at runtime). Keys stored in `global_settings` table. Users never see these keys — they only see the provider/model names in their Models page. | **HIGHEST** |
| E2 | General Platform Settings | `/admin/settings/general` | 18 Configs saved to key-value admin settings store (use existing `OrganizationConfigurationModel` pattern but `global_settings` singleton): App Name, Default Plan (new signups), Default Credits for new user, Enable Signup toggle (close registrations), Maintenance Mode (show banner + 503 API), Support Email, Support URL, Price per Second (default org pricing), Min Credit Purchase, Invoice Prefix, Invoice Starting Number, System Timezone, Referral bonus credits, Low credit threshold (warn at < X), Enable/disable telephony providers globally, Credit burn rate (multiplier), Custom HTML for <head> analytics injection, Custom HTML for <body> script injection. | HIGH |
| E3 | Branding | `/admin/settings/branding` | Uploads (via existing storage/minio pattern): Logo (light), Logo (dark), Favicon. Primary color picker (generates CSS var override). Welcome greeting text. Footer links JSON array (Label/URL/target_blank). Admin saved to global settings. Dograh's BrandingProvider in ui then applies these globally via CSS vars + header logo swap. | MEDIUM |
| E4 | SMTP & Email Templates | `/admin/settings/email` | SMTP card: Host, Port, Security (SSL/TLS/none), Username, Password, From Name, From Email. Send Test Email button â€” user enters address. Email Templates section: List of template keys (welcome_email, password_reset, credit_purchase_receipt, credit_low_alert, invoice_generated). Each template key opens editor with Subject + HTML body WYSIWYG. Variables legend on side ({{user_name}}, {{credits}}, etc). Test template send. | MEDIUM |
| E5 | LLM Model Allowlist & Pricing Override | `/admin/settings/models` | Display-only table of all providers/models (reuses registry.py's MODEL lists). Admin can mark a model as "Hidden" (not shown to users even if provider key exists), or "Premium only". Per-model pricing override (price per 1k tokens, per minute voice) that is used in credit burn calculation instead of defaults. Dograh already uses these registry constants so we apply override at resolve time. | MEDIUM |
| E6 | Language & i18n | `/admin/settings/languages` | 20+ language checkboxes (English, Spanish, Hindi, Portuguese, French, German, Arabic, etc). Default language dropdown. Each row: Enabled, Flag icon, Language name. UI reads from this to build locale selector. | LOW |
| E7 | Batch Jobs Monitor | `/admin/jobs` | Currently running batch jobs (campaigns, KB indexing, import). Table: Job name, Type, Owner, Status, Progress %, Last update, Error. Auto-refresh 10s. Cancel running job button. Links to campaign detail for campaign jobs. | MEDIUM |
| E8 | Broadcast Notifications | `/admin/notifications` | Create in-app announcement: Title, Message, Icon (bell/alert/info/success/warning/megaphone/sparkles/gift/party picker), Link URL, Display Style (bell-only / top banner / both), Priority 1-10, Dismissible switch, Expiry date. Preview panel. Send â€” pushes to notification_bell + top banner component. History list below (sent items, # users viewed, etc). | MEDIUM |
| E9 | Admin Audit Log | `/admin/audit-log` | Immutable read-only table. Timestamp, Admin (who), Action type, Target ID + Type, IP, Summary (e.g. "User 123 banned by admin 1", "Key 'Default OpenAI' edited"). Filters: Admin name, Action, Date. Export CSV. Backend middleware `middleware/admin_audit.py` records every PATCH/POST/DELETE to /admin routes. | LOW |

---

## PART 3: User Panel - Revised Feature Matrix (22 modules)

### Dograh-architecture aligned. No caiagent SIP/Incoming pages; no Plivo settings separate page.

### Section F: User Dashboard Core

| # | Module | Route | Dograh-native implementation | Priority |
|---|--------|-------|-------------------------------|----------|
| F1 | User Home Dashboard (Overhaul) | `/overview` | Replace existing static page with: Personalized greeting (Good morning/afternoon/evening), 12 KPI cards: Total Calls, This Week vs Last Week trend %, Inbound, Outbound, Campaign success rate %, Appointments Booked, Forms Submitted, Total Contacts, KB Articles, Workflows Count, Credits Balance, Current Plan. Weekly area chart (Incoming vs Outgoing calls 7 days). Lead Status Donut chart (Hot/Warm/Cold/Lost). Sentiment donut. Recent Calls table. Recent Contacts table. Quick Action buttons: New Workflow, New Campaign, Buy Credits. | HIGH |
| F2 | Sidebar Overhaul | Component | Grouped sections: **HOME** (Dashboard), **BUILD** (Campaigns, Agents (separate list view of workflows), Knowledge Base, Tools), **TELEPHONY** (All Contacts, Phone Numbers), **MONITOR** (Conversations (plugin-messaging), Calls, Analytics). Sidebar footer section: User Avatar, Name, Email, Credits display (always visible), Plan badge, Dropdown (Billing, Settings, Logout). Credit Widget always-on. | HIGH |
| F3 | Campaigns List + CRUD | `/campaigns` | Grid + List toggle. Campaign cards/rows. Status badge (In Progress / Pending / Scheduled / Completed / Failed). Progress bar (% of contacts called), % Success, Scheduled date. Tabs: Active / Draft / Completed / Trashed (soft-delete, restore). Create Campaign dialog (name, contact list, agent/workflow, scheduled date). Edit, Clone, Delete. Start/Pause/Resume/Stop controls. | HIGH |
| F4 | Campaign Detail | `/campaigns/[id]` | Summary, Running stats live-refresh, Contacts list (upload CSV, paste, single add). Per-contact outcome: status + recording + transcript + notes. Retry failed contacts button. Export campaign results CSV. | HIGH |
| F5 | Agents (Workflow list alias) | `/agents` | Workflows list page. Separate from workflow editor. Card/Table view. Search + filter. Version history dropdown per row. "New Agent" wizard (guided steps: select template, configure model with the user's own provider keys, connect phone number, test call, publish). | HIGH |
| F6 | CRM / All Contacts | `/contacts` | Full CRM: Kanban (stages) + list toggle. Columns/stages: Hot / Warm / Cold / Appointment Booked / Closed. Lead cards: Name, Phone, AI category, Score 0-100, Source, Sentiment. Per-lead detail drawer: Transcript, Recording playback, Notes, Activity timeline, Custom fields JSON, Tag editor. Bulk actions: change stage, add tags, delete, export. Import CSV / Export CSV. CRM Analytics sub-tabs: Leads-by-stage bar, By source, By date, Conversion rate funnel, Average score, Sentiment breakdown. | HIGH |
| F7 | Lead Stage Editor | `/contacts/stages` | Customize stages. Drag order, edit color, delete, mark default. Stage name. | MEDIUM |
| F8 | Phone Numbers (existing page + enhancement) | `/phone-numbers` | Existing `TelephonyPhoneNumberModel` table via routes/telephony.py. Enhance table: add "Inbound Route" column (shows assigned workflow name + link), Add "Default Caller ID" badge, Add "Buy Number" flow (reuse existing buy provider endpoint), Release, Assign workflow, Label edit. **NO separate SIP page, NO separate Incoming Connections page.** All on this one page using the existing telephony architecture. Inbound route column is the existing `inbound_workflow_id` field with a workflow name. | HIGH |

### Section G: Analytics, Calls, Billing

| # | Module | Route | Description | Priority |
|---|--------|-------|-------------|----------|
| G1 | Calls List (user view) | `/calls` | User's own calls only. Table: Dialed number / Caller, Status, Direction, Duration, Disposition, Agent (workflow) used, Recording icon, Date. Filter + Search + Date range. Export CSV. Detail link â†’ Call Detail user view. | HIGH |
| G2 | Call Detail (user view) | `/calls/[id]` | Recording player with waveform, Transcript speaker separated, AI Summary, Sentiment, Classification, Workflow link, Notes (editable by user). No moderation sidebar. | MEDIUM |
| G3 | Deep Analytics Page | `/analytics` | Replaces existing Reports page. 30/90/365 day selector. Charts: Calls per day area, Avg Duration line, Inbound vs Outbound stack, Lead conversion funnel, Workflow (Agent) performance rank table, Campaign performance rank table, Cost breakdown by model/day bar, Savings vs human agents estimate card. Export data CSV. | HIGH |
| G4 | Billing Page | `/billing` | Tabs: Overview, Buy Credits, Transactions, Invoices. Overview: Current Plan badge, Plan quota progress bars (workflows used, numbers used, minutes/credits remaining), Payment methods (stripe card on file), Billing info edit. Buy Credits: Credit packages grid (same packages admin configured), click â†’ Stripe/payment modal â†’ receipt â†’ auto add credits â†’ email invoice. Transactions: list of user's purchases + debits, PDF download. Invoices: list, PDF download. | HIGH |

### Section H: User Settings & Knowledge

| # | Module | Route | Description | Priority |
|---|--------|-------|-------------|----------|
| H1 | User Settings - Profile | `/settings/profile` | Avatar upload, First, Last, Display name, Email (verified badge), Phone, Timezone, Language. Change Password (old / new / confirm). Delete Account button with 2-step confirm warning. | HIGH |
| H2 | User Settings - Security | `/settings/security` | 2FA TOTP setup. Backup codes generator/list. Active sessions table (Device, OS, Browser, IP, Approx Location, Login time, Session timeout, "Log out" button per row). App Passwords if needed later. Future-only â€” start with 2FA + sessions. | MEDIUM |
| H3 | User Settings - Notifications | `/settings/notifications` | Per-channel toggles (Email / In-app). Events: Call Completed (per agent summary), Campaign Done, Low Credit (< threshold), Purchase Receipt, Appointment Booked, Weekly Digest, Product Announcements (marketing opt-in). | MEDIUM |
| H4 | User Settings - Team Members | `/settings/team` | Org team. Table: Name, Email, Role (Owner / Admin / Agent / Viewer), Joined. Pending invites section with Resend/Cancel. Invite member (email + role modal). Change role. Remove member. Uses existing `organization_users_association` table. | HIGH |
| H5 | User Settings - Billing | `/settings/billing` | Org billing details: Company Name, Address line 1/2, City, State/Province, ZIP/Postal, Country, VAT / Tax ID, Billing Email (receipts go here). Invoice prefix override per org. | MEDIUM |
| H6 | User Settings - API Keys | `/settings/api-keys` | Existing API keys CRUD (table: Name, Masked Key, Created, Last Used, Revoke). Enhanced: add "Permissions" (Read-only / Full access), Rate limit display, Created by user. Uses existing `api_keys` table. | MEDIUM |
| H7 | Knowledge Base (enhancements) | `/knowledge` (existing `kb/` route) | Existing. Minor polish: status badges (Processing/Ready/Error), Re-index button per source, Processed % progress, Delete confirm. | MEDIUM |
| H8 | AI Configuration Screen (OVERHAUL) | `/model-configurations` | **No API key inputs shown to users.** Clean model picker: LLM provider dropdown (shows only admin-enabled providers) → model dropdown (shows only admin-enabled models for that provider). Same for TTS, STT, Realtime. Pre-selected with admin-configured platform defaults. User saves their choice; admin keys are injected at runtime. No "Dograh Service Key" field, no BYOK credential form for users. | **HIGHEST** |
| H9 | Integrations | `/integrations` | Card grid. Google Calendar (book appointments), Google Sheets (lead sync), Slack (notifications), Notion, Zapier, Stripe (connect Payouts). Each: Connect button, Configured green badge, Disconnect. OAuth flow where applicable. Start with Google Calendar + Sheets as MVP. | MEDIUM |
| H10 | Voices Gallery | `/voices` | All TTS voices from enabled providers and the user's configured credentials. Search, Filter by language/gender/provider. Play preview button inline. Mark "Favorite" per org (saved to org config). Set "Default Voice" for new workflows. Upload cloned voice button (if provider supports â€” ElevenLabs, etc). | MEDIUM |
| H11 | Appointments | `/appointments` | List + Calendar grid views. Appointments: Customer name, Date/time, Zoom/Meet link, Source (campaign/workflow), Notes. Actions: Reschedule, Cancel, Mark Complete. Toggle "Sync with Google Calendar". | MEDIUM |
| H12 | Prompt Templates Library | `/prompts` | Shared + org-private prompt templates. Categorized (Sales, Support, Survey, Outreach). Table: Name, Category, Last modified. Create/Edit/Clone/Delete/Public toggle. Workflow editor Prompt node allows "Load from Template" button. | LOW |
| H13 | Widgets | `/widgets` | Widget builder: Website Floating Call Button, Scheduler widget, Feedback widget. Each: Style editor (colors, text, greeting), Embed code snippet (copy-to-clipboard), Usage stats (impressions/clicks). Share. | LOW |
| H14 | User Webhooks | `/settings/webhooks` | Per-org webhooks. Event subscriptions (call.completed / campaign.done / contact.created / workflow.failed). URL, Secret (auto-generated), Active toggle, SSL verify. Fire test event button. Log table (last 50 attempts). | MEDIUM |

---

## PART 4: Backend New Files

### Admin Routes

```
api/routes/admin/
â”œâ”€â”€ __init__.py                   (router mount, all subroutes + require_superuser dep)
â”œâ”€â”€ users.py                      GET/PATCH/DELETE/POST users; login-as (mint short session JWT cookie)
â”œâ”€â”€ organizations.py              GET org list + detail, set custom price per second, add credits, assign/unassign phone numbers, toggle active
â”œâ”€â”€ analytics.py                  GET dashboard KPIs, weekly charts, admin dashboard aggregation
â”œâ”€â”€ calls.py                      GET all calls (filters), call detail, ban user, flag, moderate; violations list review
â”œâ”€â”€ workflows.py                  GET all workflows, disable toggle, delete
â”œâ”€â”€ contacts.py                   GET global contacts aggregate + CSV export
â”œâ”€â”€ content.py                    Banned words CRUD
â”œâ”€â”€ credit_packages.py            CRUD credit packages
â”œâ”€â”€ plans.py                      CRUD plans
â”œâ”€â”€ transactions.py               Transactions list + CSV export + credit backfill bulk/apply CSV
â”œâ”€â”€ provider_policy.py            Provider/model catalog policy, visibility, defaults, pricing metadata; no shared provider secrets
â”œâ”€â”€ settings_general.py           18+ global platform settings key-value store: get_all, patch_key, maintenance mode, signup enable etc
â”œâ”€â”€ settings_branding.py          Upload logo/favicon + CSS var overrides via existing storage
â”œâ”€â”€ settings_email.py             SMTP save, test email send; email templates get/update, render test
â”œâ”€â”€ settings_models.py            Model allowlist hide/show + premium only + per-model pricing override
â”œâ”€â”€ settings_languages.py         i18n enabled languages + default get/set
â”œâ”€â”€ jobs.py                       Running batch jobs list + cancel action (reuse campaign queue state)
â”œâ”€â”€ notifications.py              Broadcast create + list history
â””â”€â”€ audit_log.py                  Audit log query + export
```

### Supporting Backend New Files

```
api/db/
â””â”€â”€ admin_client.py               Aggregated admin queries (calls counters, stats, joins users + orgs)

api/schemas/
â”œâ”€â”€ admin.py                      All admin Pydantic schemas (requests/responses)
â”œâ”€â”€ billing.py                    Plans/packages/transactions schemas
â”œâ”€â”€ provider_policy.py            Provider/model policy schemas; no provider API key payloads
â”œâ”€â”€ global_settings.py            KV store typed key enums

api/middleware/
â””â”€â”€ admin_audit.py                Starlette middleware: records every non-GET to /admin to audit_logs table

api/services/
â””â”€â”€ notification_service.py       Broadcast push to users via existing notification bell infrastructure
```

### DB Changes (New Tables via Alembic migrations)

1. `admin_audit_logs` â€” id, admin_user_id FK, action_type, target_type, target_id, ip_address, summary_json, created_at
2. `global_settings` â€” key (string, unique), value (JSON), updated_at (singleton per key; same pattern as org configs)
3. `credit_packages` â€” id, name, credits, price_usd, badge, features_json, enabled, display_order, created_at, updated_at
4. `plans` â€” id, key, display_name, max_workflows, max_phone_numbers, max_concurrent_calls, included_credits_monthly, allow_custom_models, support_tier, enabled, display_order
5. `transactions` â€” id, user_id FK null, org_id FK null, type enum (purchase/usage_debit/manual_adjust/refund), credits_delta, currency_amount_usd, reference_type, reference_id, admin_note, created_at
6. `banned_words` â€” id, phrase, severity enum, enabled, created_at
7. `violations` â€” id, call_id FK (recordings?), user_id FK, detected_phrase, severity, status enum, reviewed_by, reviewed_at, action_taken, notes_json, created_at
8. `lead_stages` â€” org_id FK or global, name, color, order, is_default, is_custom
9. `notifications` â€” id, title, message, icon, link, display_type enum, priority, dismissible, expires_at, created_by (admin) FK, created_at
10. `notification_deliveries` â€” id, notification_id FK, user_id FK, viewed_at

Add new columns to existing tables:
- `workflows` â†’ add `is_active` boolean default true (used by admin C5 disable toggle)
- `organizations` â†’ keep `price_per_second_usd` (already present L152 models.py) + add `status enum(active/disabled) default 'active'`
- `users` â†’ add `status enum(active/banned) default 'active'`, `plan_type string` (Free/Pro/Enterprise), `last_login_at`, `last_login_ip`
- In `telephony_phone_numbers` â†’ ensure system-owned numbers work (org_id nullable + assigned_to_org_id column to track loaned status)

---

## PART 5: Frontend New Files

### Admin Pages

```
ui/src/app/admin/
â”œâ”€â”€ layout.tsx                            Admin shell: sidebar + header + superuser guard
â”œâ”€â”€ page.tsx                              Admin dashboard (KPIs + charts)
â”œâ”€â”€ users/
â”‚   â”œâ”€â”€ page.tsx                          Users list: filter, table, CSV, create modal
â”‚   â””â”€â”€ [id]/page.tsx                     User detail: tabs (overview/orgs/workflows/calls/credits/activity)
â”œâ”€â”€ organizations/
â”‚   â”œâ”€â”€ page.tsx                          Orgs list
â”‚   â””â”€â”€ [id]/page.tsx                     Org detail: members/billing/AI config/workflows/phones
â”œâ”€â”€ calls/
â”‚   â”œâ”€â”€ page.tsx                          All calls: filter/search, inline player
â”‚   â”œâ”€â”€ [id]/page.tsx                     Call detail + moderation sidebar
â”‚   â””â”€â”€ violations/page.tsx               Moderation queue: flagged calls
â”œâ”€â”€ workflows/
â”‚   â””â”€â”€ page.tsx                          All workflows: disable/delete/view
â”œâ”€â”€ contacts/
â”‚   â””â”€â”€ page.tsx                          Global CRM aggregate read-only
â”œâ”€â”€ billing/
â”‚   â”œâ”€â”€ packages/page.tsx                 Credit packages CRUD
â”‚   â”œâ”€â”€ plans/page.tsx                    Plans CRUD
â”‚   â”œâ”€â”€ transactions/page.tsx             Ledger + CSV export
â”‚   â””â”€â”€ backfill/page.tsx                 Bulk CSV + by-plan credit backfill
â”œâ”€â”€ content/
â”‚   â””â”€â”€ banned-words/page.tsx             Banned words CRUD
â”œâ”€â”€ jobs/
â”‚   â””â”€â”€ page.tsx                          Running batch jobs (live refresh)
â”œâ”€â”€ notifications/
â”‚   â””â”€â”€ page.tsx                          Broadcast notification composer + history
â”œâ”€â”€ audit-log/
â”‚   â””â”€â”€ page.tsx                          Immutable admin audit log
â””â”€â”€ settings/
    â”œâ”€â”€ providers/page.tsx                Provider catalog, policy, defaults, visibility
    â”œâ”€â”€ general/page.tsx                  18+ platform settings
    â”œâ”€â”€ branding/page.tsx                 Logo/favicon/color/footer
    â”œâ”€â”€ email/page.tsx                    SMTP + template list + editor
    â”œâ”€â”€ models/page.tsx                   LLM allowlist + pricing overrides
    â””â”€â”€ languages/page.tsx                i18n enable/disable

ui/src/components/admin/
â”œâ”€â”€ AdminSidebar.tsx                      Navigation
â”œâ”€â”€ AdminHeader.tsx                       Search + notifications + user menu
â”œâ”€â”€ AdminMetricCard.tsx                   Reusable KPI card
â”œâ”€â”€ UserTable.tsx / OrgTable.tsx          Reusable data tables
â”œâ”€â”€ CallsTable.tsx / WorkflowsTable.tsx   Reusable tables
â”œâ”€â”€ RecordingPlayer.tsx                   Inline audio with waveform
â”œâ”€â”€ TranscriptViewer.tsx                  Speaker-separated transcript UI
â”œâ”€â”€ SettingsTabsShell.tsx                 Shared tabs pattern for settings pages
â”œâ”€â”€ ProviderPolicyForm.tsx                Reuses registry metadata + policy controls
â””â”€â”€ CreditBackfillWizard.tsx              Multi-step backfill UI
```

### User Pages (New or Overhauled)

```
ui/src/app/
â”œâ”€â”€ overview/
â”‚   â””â”€â”€ page.tsx                          OVERHAUL: Full dashboard KPIs/charts/quick-actions
â”œâ”€â”€ campaigns/
â”‚   â”œâ”€â”€ page.tsx                          NEW: Campaigns list + CRUD
â”‚   â””â”€â”€ [id]/page.tsx                     NEW: Campaign detail + contact outcomes
â”œâ”€â”€ agents/
â”‚   â””â”€â”€ page.tsx                          NEW: Agents/Workflows list + wizard launcher
â”œâ”€â”€ contacts/
â”‚   â”œâ”€â”€ page.tsx                          NEW: CRM list/Kanban + lead detail drawer
â”‚   â””â”€â”€ stages/page.tsx                   NEW: Stage editor
â”œâ”€â”€ calls/
â”‚   â”œâ”€â”€ page.tsx                          NEW: Personal call history list
â”‚   â””â”€â”€ [id]/page.tsx                     NEW: Personal call detail
â”œâ”€â”€ analytics/
â”‚   â””â”€â”€ page.tsx                          NEW: Deep analytics 30/90/365
â”œâ”€â”€ billing/
â”‚   â””â”€â”€ page.tsx                          OVERHAUL: Overview/Buy/Transactions/Invoices tabs
â”œâ”€â”€ appointments/
â”‚   â””â”€â”€ page.tsx                          NEW: Calendar/list appointments
â”œâ”€â”€ integrations/
â”‚   â””â”€â”€ page.tsx                          NEW: Integration cards
â”œâ”€â”€ voices/
â”‚   â””â”€â”€ page.tsx                          NEW: Voices gallery
â”œâ”€â”€ prompts/
â”‚   â””â”€â”€ page.tsx                          NEW: Prompt templates library
â”œâ”€â”€ widgets/
â”‚   â””â”€â”€ page.tsx                          NEW: Widget builder + embed codes
â””â”€â”€ settings/
    â”œâ”€â”€ profile/page.tsx                  NEW: Profile + password + delete
    â”œâ”€â”€ security/page.tsx                 NEW: 2FA + sessions
    â”œâ”€â”€ notifications/page.tsx            NEW: Preferences per-channel
    â”œâ”€â”€ team/page.tsx                     NEW: Invite/role org team
    â”œâ”€â”€ billing/page.tsx                  NEW: Company billing info
    â”œâ”€â”€ api-keys/page.tsx                 EXISTING: enhanced (permissions, created-by)
    â”œâ”€â”€ models/page.tsx                   NEW: Refined BYOK config screen
    â””â”€â”€ webhooks/page.tsx                 NEW: Per-org webhook CRUD + test fire

ui/src/components/user/
â”œâ”€â”€ SidebarFooter.tsx                     Credits + plan + user menu
â”œâ”€â”€ CampaignCard.tsx / CampaignTable.tsx  Campaign UI
â”œâ”€â”€ LeadBoard.tsx (Kanban) + LeadDrawer   CRM UI
â”œâ”€â”€ CreditPurchaseDialog.tsx              Buy credits modal
â””â”€â”€ (reuse existing charts/reports components)
```

---

## PART 6: Execution Phases

### Phase 0 - Foundation & Cleanup (1-2 days)
1. **Rip impersonation + Stack Auth** â€” delete files/functions listed in A1.
2. **Admin middleware guard** (A2) â€” `/admin/*` superuser-only both front/back.
3. **Admin Layout + Sidebar shell** (A3, A5) â€” empty `/admin` pages with tabs/shell scaffolding only.
4. **Login-as replacement** â€” native JWT mint in admin users route (no Stack).

### Phase 1 - Provider Catalog & BYOK UX (The Core Feature) (2-3 days)
5. **DB tables** via Alembic: `global_settings`, plus users.status / workflows.is_active / org.status new columns.
6. **Backend routes** `/admin/settings/providers/*` â€” provider policy, visibility, defaults, pricing metadata.
7. **Config resolve layer** enforce provider/model policy on top of the existing org/user BYOK configuration.
8. **Admin UI** `/admin/settings/providers` (E1) â€” 5 service tabs, visibility, defaults, pricing policy.
9. **User UI overhaul** `/settings/models` (H8) â€” improve BYOK setup UX, validation, masking, and provider guidance.

### Phase 2 - Admin Dashboard + User/Org Admin (3-4 days)
10. **Admin Dashboard** (A4) â€” 10 KPI cards + weekly charts + backend `/admin/analytics.py` aggregation.
11. **Users Management** (B1) â€” table, filters, create, edit, status, login-as, CSV.
12. **User Detail** (B2) â€” tabs.
13. **Organizations** (B3) + Org Detail (B4).
14. **Global Settings General** (E2) â€” 18 platform settings key-value.

### Phase 3 - Billing & Transactions (2 days)
15. DB: credit_packages, plans, transactions tables.
16. Backend: `admin/credit_packages.py`, `admin/plans.py`, `admin/transactions.py`, `admin/billing/backfill.py`.
17. Admin: packages/plans/transactions/backfill pages (D1-D4).
18. User: Billing page overhaul (G4) + CreditPurchaseDialog using packages admin created.

### Phase 4 - Calls Moderation + Content (2-3 days)
19. Move/upgrade `/superadmin/runs` to `/admin/calls` (C1) with inline recording player, filters.
20. Call detail + moderation sidebar (C2), Violations queue (C3), Banned words (C4).
21. All Workflows list (C5), All Contacts aggregate (C6).

### Phase 5 - User Panel Core (3-4 days)
22. **Dashboard Overhaul** (F1) â€” KPIs + charts + quick actions.
23. Sidebar Overhaul (F2) â€” sections, credit widget always-on.
24. **Campaigns** (F3) list + CRUD + (F4) Campaign detail.
25. **CRM / All Contacts** (F6) â€” Kanban + lead drawer + import/export + Stage Editor (F7).
26. Phone Numbers page enhancements (F8) â€” inbound route column.
27. User Settings pages (H1-H6): Profile, Security, Notifications, Team, Billing info, API keys.
28. User calls list (G1) + call detail (G2).
29. Deep Analytics (G3) â€” replaces Reports.

### Phase 6 - Platform polish (2-3 days)
30. Branding settings (E3) â€” CSS vars + logo/favicon, user-side BrandingProvider consumes.
31. SMTP + Email Templates (E4).
32. Model allowlist page (E5).
33. Language page (E6).
34. Broadcast Notifications (E8) + notification bell UI in admin/user header.
35. Batch Jobs Monitor (E7).
36. Admin audit log middleware + page (E9).

### Phase 7 - User Extras (Nice to have) (3+ days)
37. Agents page (F5) list + creation wizard launcher.
38. Integrations page (H9) â€” Google Calendar + Sheets MVP.
39. Voices gallery (H10).
40. Appointments (H11).
41. Knowledge Base enhancements (H7).
42. Prompt templates (H12), Widgets (H13), User Webhooks (H14).

---

## Summary

- **Admin modules**: 26 (down from 47 â€” removed caiagent pool/engine/plugin/KYC/system/SIP/incoming patterns)
- **User modules**: 22 (removed SIP, Incoming Connections standalone pages)
- **Key innovation**: Provider Catalog + BYOK UX (E1 + H8) â€” users keep ownership of third-party model credentials while admin controls visibility, defaults, and pricing policy
- **Total architecture alignment**: 100% Dograh-native configuration registry, telephony providers, models â€” no caiagent-isms left
- **Next step**: Start Phase 0 when approved


