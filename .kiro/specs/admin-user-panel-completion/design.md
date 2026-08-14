# Design Document

## 1. System Architecture

### 1.1 Architecture Overview

The Admin/User Panel completion follows a standard three-tier architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js 15)                   │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Admin Pages │  │ User Pages   │  │ Shared Components│  │
│  │ /superadmin │  │ /overview    │  │ Tables, Forms    │  │
│  │ /calls      │  │ /campaigns   │  │ Modals, Charts   │  │
│  │ /billing    │  │ /contacts    │  │ Players          │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↕ HTTP/REST
┌─────────────────────────────────────────────────────────────┐
│                  Backend API (FastAPI)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │ Admin Routes │  │ User Routes  │  │ Middleware       │ │
│  │ /admin/*     │  │ /campaigns/* │  │ - Auth           │ │
│  │              │  │ /contacts/*  │  │ - Admin Audit    │ │
│  └──────────────┘  └──────────────┘  └──────────────────┘ │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Services Layer                          │  │
│  │  - Admin Key Injection  - Notification Broadcast    │  │
│  │  - Credit Management    - Email Templating          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↕ SQL
┌─────────────────────────────────────────────────────────────┐
│                  Database (PostgreSQL)                      │
│  - global_settings          - credit_packages               │
│  - admin_audit_logs         - plans                         │
│  - banned_words             - transactions                  │
│  - violations               - lead_stages                   │
│  - notifications            - notification_deliveries       │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. API Design

### 2.1 Admin Call Moderation Routes

**Base Path:** `/admin/calls`

#### GET /admin/calls
List all platform calls with filtering and pagination.

**Query Parameters:**
```typescript
{
  page?: number           // default: 1
  limit?: number          // default: 50, max: 100
  status?: string         // 'completed' | 'failed' | 'in_progress'
  direction?: string      // 'inbound' | 'outbound'
  user_id?: number
  org_id?: number
  phone_number?: string
  date_from?: string      // ISO 8601
  date_to?: string        // ISO 8601
  search?: string         // searches run_id, user email, org name
}
```

**Response:**
```typescript
{
  items: Array<{
    id: number
    started_at: string
    caller: string
    callee: string
    user: { id: number, email: string, name: string }
    organization: { id: number, name: string }
    status: string
    duration_seconds: number
    workflow: { id: number, name: string }
    disposition: string | null
    recording_url: string | null
  }>
  total: number
  page: number
  pages: number
}
```

#### GET /admin/calls/{run_id}
Get detailed call information.

**Response:**
```typescript
{
  id: number
  started_at: string
  completed_at: string
  caller: string
  callee: string
  direction: string
  status: string
  duration_seconds: number
  workflow: { id: number, name: string, config: object }
  user: { id: number, email: string, name: string, status: string }
  organization: { id: number, name: string, status: string }
  recording_url: string | null
  transcript: Array<{
    speaker: string
    text: string
    timestamp: number
  }>
  ai_summary: string | null
  sentiment: string | null
  classification: string | null
  events: Array<{
    type: string
    timestamp: string
    data: object
  }>
  admin_notes: Array<{
    note: string
    created_by: { id: number, email: string }
    created_at: string
  }>
  moderation_actions: Array<{
    action: string
    reason: string
    created_by: { id: number, email: string }
    created_at: string
  }>
}
```

#### POST /admin/calls/{run_id}/ban-user
Ban the user who made this call.

**Request Body:**
```typescript
{
  reason: string  // required, min 10 chars
}
```

**Response:**
```typescript
{
  success: true
  message: "User banned successfully"
  user: { id: number, email: string, status: "banned" }
}
```

**Side Effects:**
- Updates `users.status = 'banned'`
- Creates admin_audit_logs entry
- Future workflow executions blocked for this user

#### POST /admin/calls/{run_id}/flag
Flag a call for review.

**Request Body:**
```typescript
{
  severity: 'low' | 'medium' | 'high' | 'critical'
  reason: string
}
```

**Response:**
```typescript
{
  success: true
  violation_id: number
}
```

**Side Effects:**
- Creates violations record with status='pending'

#### PATCH /admin/calls/{run_id}/notes
Add admin notes to a call.

**Request Body:**
```typescript
{
  note: string  // required
}
```

**Response:**
```typescript
{
  success: true
  note: {
    id: number
    note: string
    created_by: { id: number, email: string }
    created_at: string
  }
}
```

#### DELETE /admin/calls/{run_id}
Delete a call record.

**Response:**
```typescript
{
  success: true
  message: "Call deleted successfully"
}
```

**Side Effects:**
- Soft-deletes workflow_run record
- Recording remains in MinIO (cleanup job separate)
- Violations remain (orphaned but visible)

#### GET /admin/calls/violations
Get moderation queue.

**Query Parameters:**
```typescript
{
  severity?: string       // 'low' | 'medium' | 'high' | 'critical'
  status?: string        // 'pending' | 'reviewed' | 'actioned' | 'dismissed'
  page?: number
  limit?: number
}
```

**Response:**
```typescript
{
  items: Array<{
    id: number
    call_id: number
    call_timestamp: string
    user: { id: number, email: string }
    org: { id: number, name: string }
    detected_phrase: string
    severity: string
    status: string
    reviewed_by: { id: number, email: string } | null
    reviewed_at: string | null
  }>
  total: number
  page: number
  pages: number
}
```

---

### 2.2 Admin Content Routes

**Base Path:** `/admin/content`

#### GET /admin/content/banned-words
List all banned words.

**Query Parameters:**
```typescript
{
  page?: number
  limit?: number
  severity?: string
  enabled?: boolean
  search?: string
}
```

**Response:**
```typescript
{
  items: Array<{
    id: number
    phrase: string
    severity: 'low' | 'medium' | 'high' | 'critical'
    enabled: boolean
    created_at: string
  }>
  total: number
}
```

#### POST /admin/content/banned-words
Create a banned word.

**Request Body:**
```typescript
{
  phrase: string          // required, min 2 chars
  severity: string        // required
  enabled?: boolean       // default: true
}
```

#### PATCH /admin/content/banned-words/{id}
Update a banned word.

#### DELETE /admin/content/banned-words/{id}
Delete a banned word.

#### POST /admin/content/banned-words/import
Import banned words from CSV.

**Request:** multipart/form-data with file field

**Response:**
```typescript
{
  success: true
  imported: number
  errors: Array<{ row: number, error: string }>
}
```

#### GET /admin/content/banned-words/export
Export to CSV.

**Response:** text/csv file download

---

### 2.3 Admin Billing Routes

**Base Path:** `/admin/billing`

#### GET /admin/billing/packages
List credit packages.

#### POST /admin/billing/packages
Create package.

**Request Body:**
```typescript
{
  name: string
  credits: number           // positive integer
  price_usd: number        // decimal, two places
  badge?: string           // e.g., "Popular"
  features?: string[]      // ["Feature 1", "Feature 2"]
  enabled?: boolean        // default: true
  display_order?: number   // default: 0
}
```

#### PATCH /admin/billing/packages/{id}
Update package.

#### DELETE /admin/billing/packages/{id}
Delete package (soft-delete if referenced in transactions).

---

#### GET /admin/billing/plans
List subscription plans.

#### POST /admin/billing/plans
Create plan.

**Request Body:**
```typescript
{
  key: string                      // 'free' | 'pro' | 'enterprise' | 'custom'
  display_name: string
  max_workflows?: number           // null = unlimited
  max_phone_numbers?: number
  max_concurrent_calls?: number
  included_credits_monthly: number // default: 0
  allow_custom_models: boolean     // default: false
  support_tier: string             // 'none' | 'standard' | 'priority'
  enabled?: boolean                // default: true
  display_order?: number
}
```

#### PATCH /admin/billing/plans/{id}
Update plan.

#### DELETE /admin/billing/plans/{id}
Delete plan (validation: cannot delete default plan or plan with users).

---

#### GET /admin/billing/transactions
List transactions ledger.

**Query Parameters:**
```typescript
{
  user_id?: number
  org_id?: number
  type?: 'purchase' | 'usage_debit' | 'manual_adjust' | 'refund'
  date_from?: string
  date_to?: string
  amount_min?: number
  amount_max?: number
  page?: number
  limit?: number
}
```

**Response:**
```typescript
{
  items: Array<{
    id: number
    created_at: string
    user: { id: number, email: string } | null
    org: { id: number, name: string } | null
    type: string
    credits_delta: number      // + for add, - for deduct
    currency_amount_usd: number | null
    reference_type: string | null
    reference_id: number | null
    admin_note: string | null
  }>
  total: number
}
```

#### GET /admin/billing/transactions/export
Export CSV.

---

#### POST /admin/billing/backfill
Bulk credit backfill.

**Request Body - Mode 1 (By Plan):**
```typescript
{
  mode: 'by_plan'
  plan_keys: string[]     // ['free', 'pro']
  credits: number
  note: string            // required
}
```

**Request Body - Mode 2 (By CSV):**
```typescript
{
  mode: 'by_csv'
  csv_data: string        // CSV content: email,credits\nuser@example.com,100
  note: string
}
```

**Response:**
```typescript
{
  success: true
  applied_count: number
  errors: Array<{ email: string, error: string }>
  transaction_ids: number[]
}
```

---

### 2.4 Admin Settings Routes

**Base Path:** `/admin/settings`

#### GET /admin/settings/general
Get all general settings.

**Response:**
```typescript
{
  app_name: string
  default_plan: string
  default_credits_new_user: number
  enable_signup: boolean
  maintenance_mode: boolean
  maintenance_banner_text: string
  support_email: string
  support_url: string
  price_per_second_default: number
  min_credit_purchase: number
  invoice_prefix: string
  invoice_starting_number: number
  system_timezone: string
  referral_bonus_credits: number
  low_credit_threshold: number
  enabled_telephony_providers: string[]
  credit_burn_rate_multiplier: number
  custom_html_head: string
  custom_html_body: string
}
```

#### PATCH /admin/settings/general
Update settings (partial update allowed).

**Request Body:** Any subset of the GET response fields.

**Validation:**
- `enable_signup`: boolean
- `maintenance_mode`: boolean (when true, shows banner + 503 API except admin routes)
- `price_per_second_default`: must be positive
- `min_credit_purchase`: must be >= 1

---

#### GET /admin/settings/branding
Get branding settings.

**Response:**
```typescript
{
  logo_light_url: string | null
  logo_dark_url: string | null
  favicon_url: string | null
  primary_color: string          // hex color
  welcome_greeting: string
  footer_links: Array<{
    label: string
    url: string
    new_tab: boolean
  }>
}
```

#### POST /admin/settings/branding/upload
Upload logo/favicon.

**Request:** multipart/form-data
- `type`: 'logo_light' | 'logo_dark' | 'favicon'
- `file`: File

**Response:**
```typescript
{
  success: true
  url: string              // MinIO URL
}
```

**Validation:**
- Logo: max 2MB, PNG/SVG/JPEG
- Favicon: max 512KB, ICO/PNG

#### PATCH /admin/settings/branding
Update branding settings (non-file fields).

---

#### GET /admin/settings/email
Get SMTP config and email templates.

**Response:**
```typescript
{
  smtp: {
    host: string
    port: number
    security: 'none' | 'ssl' | 'tls'
    username: string
    password: string        // masked: "***"
    from_name: string
    from_email: string
  }
  templates: Array<{
    key: string           // 'welcome_email', etc.
    subject: string
    html_body: string
    variables: string[]   // ['user_name', 'credits']
  }>
}
```

#### PATCH /admin/settings/email/smtp
Update SMTP config.

**Request Body:** SMTP object from GET response (password not required if not changing).

#### POST /admin/settings/email/test
Send test email.

**Request Body:**
```typescript
{
  recipient: string      // email address
}
```

**Response:**
```typescript
{
  success: boolean
  message: string
}
```

#### PATCH /admin/settings/email/templates/{key}
Update email template.

**Request Body:**
```typescript
{
  subject: string
  html_body: string      // Jinja2 template with {{variables}}
}
```

**Validation:**
- Check for undefined variables (warnings only, don't block)

#### POST /admin/settings/email/templates/{key}/test
Send test template.

**Request Body:**
```typescript
{
  recipient: string
}
```

---

#### GET /admin/settings/models
Get model allowlist and pricing.

**Response:**
```typescript
{
  models: Array<{
    provider: string
    service_type: 'llm' | 'tts' | 'stt' | 'embeddings' | 'realtime'
    model_id: string
    model_name: string
    visibility: 'show' | 'hidden'
    premium_only: boolean
    price_override: {
      per_1k_tokens?: number    // for LLM
      per_minute?: number        // for TTS/STT
    } | null
  }>
}
```

#### PATCH /admin/settings/models
Bulk update model settings.

**Request Body:**
```typescript
{
  updates: Array<{
    provider: string
    service_type: string
    model_id: string
    visibility?: 'show' | 'hidden'
    premium_only?: boolean
    price_override?: object | null
  }>
}
```

---

#### GET /admin/settings/languages
Get language settings.

**Response:**
```typescript
{
  languages: Array<{
    code: string          // 'en', 'es', 'hi'
    name: string          // 'English', 'Spanish'
    flag_icon: string     // emoji or icon code
    enabled: boolean
    is_default: boolean
  }>
}
```

#### PATCH /admin/settings/languages
Update language settings.

**Request Body:**
```typescript
{
  updates: Array<{
    code: string
    enabled?: boolean
    is_default?: boolean
  }>
}
```

**Validation:**
- At least one language must be enabled
- Cannot disable English
- Only one language can be default

---

### 2.5 Admin Supporting Routes

#### GET /admin/jobs
Get running batch jobs.

**Response:**
```typescript
{
  jobs: Array<{
    id: string
    type: 'campaign' | 'kb_indexing' | 'import'
    owner: { id: number, email: string }
    status: 'running' | 'completed' | 'failed' | 'cancelled'
    progress_percent: number
    last_update: string
    error_message: string | null
    reference_id: number | null    // campaign_id or kb_id
  }>
}
```

#### POST /admin/jobs/{id}/cancel
Cancel a running job.

---

#### GET /admin/notifications
List broadcast notifications.

**Response:**
```typescript
{
  items: Array<{
    id: number
    title: string
    message: string
    icon: string
    link: string | null
    display_type: 'bell_only' | 'banner' | 'both'
    priority: number
    dismissible: boolean
    expires_at: string | null
    created_by: { id: number, email: string }
    created_at: string
    viewed_count: number
    total_users: number
  }>
}
```

#### POST /admin/notifications
Create and broadcast notification.

**Request Body:**
```typescript
{
  title: string                   // required, max 200 chars
  message: string                // required, markdown supported
  icon: string                   // 'bell' | 'alert' | 'info' | 'success' | 'warning' | 'megaphone' | 'sparkles' | 'gift' | 'party'
  link?: string                  // URL
  display_type: string           // required
  priority?: number              // 1-10, default: 5
  dismissible?: boolean          // default: true
  expires_at?: string            // ISO 8601
}
```

**Response:**
```typescript
{
  success: true
  notification_id: number
  deliveries_created: number
}
```

**Side Effects:**
- Creates notifications record
- Creates notification_deliveries for all active users
- Background job via ARQ

#### DELETE /admin/notifications/{id}
Delete notification (cascade deletes deliveries).

---

#### GET /admin/audit-log
Get admin audit log.

**Query Parameters:**
```typescript
{
  admin_user_id?: number
  action_type?: string       // 'create' | 'update' | 'delete'
  target_type?: string       // 'user' | 'org' | 'call' | etc.
  date_from?: string
  date_to?: string
  search?: string           // search summary_json
  page?: number
  limit?: number
}
```

**Response:**
```typescript
{
  items: Array<{
    id: number
    timestamp: string
    admin: { id: number, email: string }
    action_type: string
    target_type: string
    target_id: number | null
    ip_address: string
    summary: string          // auto-generated description
  }>
  total: number
}
```

#### GET /admin/audit-log/export
Export CSV.

---

## 3. Database Design

### 3.1 Migration Plan

**Migration Sequence:**

1. **Migration: a1b2c3d4e001** (Already created, needs to be applied)
   - Creates `global_settings` table
   - Status: ✅ Created, ❌ Not Applied

2. **Migration: a1b2c3d4e002_add_moderation_tables**
   - Creates `banned_words` table
   - Creates `violations` table
   - Status: ❌ To be created

3. **Migration: a1b2c3d4e003_add_billing_tables**
   - Creates `credit_packages` table
   - Creates `plans` table
   - Creates `transactions` table
   - Status: ❌ To be created

4. **Migration: a1b2c3d4e004_add_notification_tables**
   - Creates `notifications` table
   - Creates `notification_deliveries` table
   - Status: ❌ To be created

5. **Migration: a1b2c3d4e005_add_admin_audit_table**
   - Creates `admin_audit_logs` table
   - Status: ❌ To be created

6. **Migration: a1b2c3d4e006_add_crm_tables**
   - Creates `lead_stages` table
   - Status: ❌ To be created

7. **Migration: a1b2c3d4e007_add_status_columns**
   - Adds `workflows.is_active` column
   - Adds `organizations.status` column
   - Adds `users.status`, `users.plan_type`, `users.last_login_at`, `users.last_login_ip` columns
   - Status: ❌ To be created

### 3.2 Complete Table Schemas

See requirements.md Section 3.1 for complete SQL definitions.

---

## 4. Frontend Architecture

### 4.1 Component Structure

**Shared Component Library:**
```
ui/src/components/
├── admin/
│   ├── AdminSidebar.tsx           [✅ EXISTS]
│   ├── AdminHeader.tsx            [❌ CREATE]
│   ├── AdminMetricCard.tsx        [❌ CREATE]
│   ├── CallsTable.tsx             [❌ CREATE]
│   ├── RecordingPlayer.tsx        [❌ CREATE]
│   ├── TranscriptViewer.tsx       [❌ CREATE]
│   ├── ModerationSidebar.tsx      [❌ CREATE]
│   ├── UserTable.tsx              [❌ CREATE]
│   ├── OrgTable.tsx               [❌ CREATE]
│   ├── WorkflowsTable.tsx         [❌ CREATE]
│   ├── PackageForm.tsx            [❌ CREATE]
│   ├── PlanForm.tsx               [❌ CREATE]
│   ├── CreditBackfillWizard.tsx   [❌ CREATE]
│   ├── EmailTemplateEditor.tsx    [❌ CREATE]
│   ├── BrandingPreview.tsx        [❌ CREATE]
│   └── SettingsTabsShell.tsx      [❌ CREATE]
│
└── user/
    ├── SidebarFooter.tsx          [❌ CREATE] - credits widget
    ├── CampaignCard.tsx           [❌ CREATE]
    ├── CampaignTable.tsx          [❌ CREATE]
    ├── LeadBoard.tsx              [❌ CREATE] - Kanban
    ├── LeadDrawer.tsx             [❌ CREATE]
    ├── CreditPurchaseDialog.tsx   [❌ CREATE]
    └── [existing charts/reports]  [✅ REUSE]
```

### 4.2 State Management

**Approach:** React Server Components + Client Components with hooks

**Data Fetching Patterns:**
- **Server Components:** Fetch data on server, pass to client components
- **Client Components:** Use SWR for real-time updates, mutations
- **Forms:** React Hook Form + Zod validation
- **Tables:** TanStack Table for sorting/filtering/pagination

**Example Pattern:**
```typescript
// Server Component (page.tsx)
export default async function AdminCallsPage({
  searchParams
}: {
  searchParams: { page?: string; status?: string }
}) {
  const calls = await fetchCalls(searchParams)
  return <CallsTable initialData={calls} />
}

// Client Component (CallsTable.tsx)
'use client'
export function CallsTable({ initialData }) {
  const { data, mutate } = useSWR('/admin/calls', fetcher, {
    fallbackData: initialData,
    refreshInterval: 30000  // 30s polling
  })
  // Table implementation
}
```

### 4.3 Form Validation

**Library:** Zod schemas matching backend Pydantic models

**Example:**
```typescript
const BanUserSchema = z.object({
  reason: z.string().min(10, "Reason must be at least 10 characters")
})

type BanUserForm = z.infer<typeof BanUserSchema>

// In component
const form = useForm<BanUserForm>({
  resolver: zodResolver(BanUserSchema)
})
```

### 4.4 Error Handling

**Pattern:**
```typescript
try {
  const response = await fetch('/admin/calls/123/ban-user', {
    method: 'POST',
    body: JSON.stringify({ reason })
  })
  
  if (!response.ok) {
    const error = await response.json()
    toast.error(error.detail || "Failed to ban user")
    return
  }
  
  toast.success("User banned successfully")
  mutate()  // Refresh data
} catch (err) {
  toast.error("Network error")
}
```

---

## 5. Service Layer Design

### 5.1 Admin Audit Middleware

**File:** `api/middleware/admin_audit.py`

**Implementation:**
```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

class AdminAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Only log admin routes with state-changing methods
        if (request.url.path.startswith("/admin/") and 
            request.method in ["POST", "PATCH", "DELETE"]):
            await self.log_action(request, response)
        
        return response
    
    async def log_action(self, request: Request, response: Response):
        user = request.state.user  # from auth middleware
        
        # Extract action details
        action_type = self.get_action_type(request.method)
        target_type, target_id = self.parse_path(request.url.path)
        
        # Create audit log entry
        async with get_db() as db:
            log = AdminAuditLogModel(
                admin_user_id=user.id,
                action_type=action_type,
                target_type=target_type,
                target_id=target_id,
                ip_address=request.client.host,
                summary_json=self.generate_summary(request, response)
            )
            db.add(log)
            await db.commit()
    
    def generate_summary(self, request, response) -> dict:
        # Auto-generate human-readable summary
        # "User 123 banned by admin 1"
        # "Credits adjusted: user 456 +500"
        pass
```

**Integration:** Add to `api/main.py`:
```python
from api.middleware.admin_audit import AdminAuditMiddleware

app.add_middleware(AdminAuditMiddleware)
```

---

### 5.2 Notification Broadcast Service

**File:** `api/services/notification_service.py`

**Implementation:**
```python
from arq import create_pool
from sqlalchemy import select
from api.db.models import NotificationModel, NotificationDeliveryModel, UserModel

async def broadcast_notification(
    title: str,
    message: str,
    icon: str,
    link: str | None,
    display_type: str,
    priority: int,
    dismissible: bool,
    expires_at: datetime | None,
    created_by_id: int
) -> int:
    """
    Create notification and queue delivery to all active users.
    Returns notification_id.
    """
    async with get_db() as db:
        # Create notification record
        notification = NotificationModel(
            title=title,
            message=message,
            icon=icon,
            link=link,
            display_type=display_type,
            priority=priority,
            dismissible=dismissible,
            expires_at=expires_at,
            created_by=created_by_id
        )
        db.add(notification)
        await db.flush()
        
        notification_id = notification.id
        
        # Get all active users
        result = await db.execute(
            select(UserModel.id).where(UserModel.status == 'active')
        )
        user_ids = [row[0] for row in result]
        
        # Queue background job for delivery creation
        redis = await create_pool(settings.REDIS_URL)
        await redis.enqueue_job(
            'create_notification_deliveries',
            notification_id,
            user_ids
        )
        
        await db.commit()
        return notification_id

# Background job
async def create_notification_deliveries(
    ctx: dict,
    notification_id: int,
    user_ids: list[int]
):
    """
    ARQ background job to create delivery records.
    Processes in batches of 100.
    """
    async with get_db() as db:
        for i in range(0, len(user_ids), 100):
            batch = user_ids[i:i+100]
            deliveries = [
                NotificationDeliveryModel(
                    notification_id=notification_id,
                    user_id=uid
                )
                for uid in batch
            ]
            db.add_all(deliveries)
            await db.commit()
```

---

### 5.3 Credit Management Service

**File:** `api/services/credit_service.py`

**Functions:**
```python
async def add_credits(
    user_id: int,
    org_id: int | None,
    credits: int,
    note: str,
    reference_type: str = "manual_adjust",
    reference_id: int | None = None
) -> int:
    """Add credits and create transaction record."""
    pass

async def deduct_credits(
    org_id: int,
    credits: int,
    reference_type: str = "usage_debit",
    reference_id: int | None = None
) -> bool:
    """
    Deduct credits after call.
    Returns True if successful, False if insufficient balance.
    """
    pass

async def calculate_call_cost(
    duration_seconds: int,
    provider: str,
    model: str,
    org_id: int
) -> int:
    """
    Calculate credits to deduct for a call.
    Uses admin price_override if set, else price_per_second_default.
    """
    pass

async def get_credit_balance(org_id: int) -> int:
    """Get current credit balance for org."""
    pass
```

---

## 6. Integration Patterns

### 6.1 Workflow Execution Enforcement

**File:** `api/services/workflow/execution.py` (modify existing)

**Add checks:**
```python
async def execute_workflow(workflow_id: int, user_id: int):
    # Get user and org
    user = await get_user(user_id)
    org = await get_organization(user.org_id)
    
    # Check 1: User status
    if user.status == 'banned':
        raise HTTPException(403, "User is banned")
    
    # Check 2: Workflow active status
    workflow = await get_workflow(workflow_id)
    if not workflow.is_active:
        raise HTTPException(403, "Workflow is disabled")
    
    # Check 3: Organization status
    if org.status == 'disabled':
        raise HTTPException(403, "Organization is disabled")
    
    # Execute workflow...
    result = await run_workflow(workflow)
    
    # Deduct credits after completion
    cost = await calculate_call_cost(
        result.duration_seconds,
        workflow.config.provider,
        workflow.config.model,
        org.id
    )
    await deduct_credits(org.id, cost, "usage_debit", result.id)
    
    return result
```

### 6.2 Email Template Rendering

**File:** `api/services/email_service.py` (modify existing)

**Add template support:**
```python
from jinja2 import Template

async def send_template_email(
    template_key: str,
    recipient: str,
    context: dict
):
    """
    Render and send email template.
    
    Args:
        template_key: 'welcome_email' | 'password_reset' | etc.
        recipient: email address
        context: variables dict, e.g., {'user_name': 'John', 'credits': 100}
    """
    # Get SMTP config from global_settings
    smtp_config = await get_global_setting('smtp_config')
    
    # Get template from global_settings
    template = await get_global_setting(f'email_template:{template_key}')
    
    # Render template
    subject_template = Template(template['subject'])
    body_template = Template(template['html_body'])
    
    subject = subject_template.render(**context)
    body = body_template.render(**context)
    
    # Send email
    await send_email(
        to=recipient,
        subject=subject,
        html=body,
        smtp_config=smtp_config
    )
```

---

## 7. Testing Strategy

### 7.1 Backend Tests

**Unit Tests:**
- `tests/services/test_credit_service.py` - credit calculations
- `tests/middleware/test_admin_audit.py` - audit logging
- `tests/services/test_notification_service.py` - notification creation

**Integration Tests:**
- `tests/routes/admin/test_calls.py` - call moderation endpoints
- `tests/routes/admin/test_billing.py` - billing CRUD
- `tests/routes/admin/test_settings.py` - settings updates

**Example Test:**
```python
async def test_ban_user_creates_audit_log():
    # Setup
    user = await create_test_user()
    call = await create_test_call(user.id)
    
    # Execute
    response = await client.post(
        f"/admin/calls/{call.id}/ban-user",
        json={"reason": "Spam detected"},
        headers=admin_auth_headers
    )
    
    # Assert
    assert response.status_code == 200
    assert user.status == "banned"
    
    # Check audit log
    log = await db.execute(
        select(AdminAuditLogModel)
        .where(AdminAuditLogModel.target_id == user.id)
    )
    assert log is not None
```

### 7.2 Frontend Tests

**Component Tests (Jest + React Testing Library):**
- `RecordingPlayer.test.tsx` - audio playback
- `CallsTable.test.tsx` - table rendering, filters
- `CreditBackfillWizard.test.tsx` - multi-step form

**E2E Tests (Playwright):**
- `admin-moderation.spec.ts` - ban user flow
- `admin-billing.spec.ts` - create package, user purchases
- `user-campaigns.spec.ts` - create campaign, view results

---

## 8. Security Considerations

### 8.1 Admin Route Protection

**Enforcement at multiple layers:**

1. **Middleware:** `api/middleware/auth.py`
   ```python
   async def require_superuser(request: Request):
       user = request.state.user
       if not user.is_superuser or user.email != "admin@admin.com":
           raise HTTPException(403, "Admin access required")
   ```

2. **Route dependency:**
   ```python
   @router.get("/admin/calls")
   async def get_calls(
       user: UserModel = Depends(require_superuser)
   ):
       pass
   ```

3. **Frontend guard:** `ui/src/app/superadmin/layout.tsx`
   ```typescript
   export default async function AdminLayout({ children }) {
     const session = await getSession()
     if (!session.user.is_superuser || session.user.email !== 'admin@admin.com') {
       redirect('/overview')
     }
     return <>{children}</>
   }
   ```

### 8.2 Data Encryption

**SMTP credentials:** Encrypted in `global_settings` table via GlobalSettingsClient

**API keys:** Already encrypted via existing admin key infrastructure

### 8.3 Rate Limiting

**Apply to credit-sensitive endpoints:**
- Credit backfill: 1 request per 10 seconds
- Notification broadcast: 1 per minute
- Ban user: 10 per minute

---

## 9. Performance Optimization

### 9.1 Database Indexes

All indexes defined in migration files (see requirements.md Section 3.1).

**Key indexes:**
- `admin_audit_logs(admin_user_id)` - filter by admin
- `admin_audit_logs(created_at DESC)` - time-range queries
- `transactions(user_id, created_at DESC)` - user ledger
- `violations(status)` - moderation queue filtering
- `notification_deliveries(user_id, notification_id)` - user notifications

### 9.2 Query Optimization

**Pagination:** All list endpoints use limit/offset pagination

**Lazy loading:** Recording URLs not fetched in list queries

**Eager loading:** User/org relationships prefetched with joins

**Example:**
```python
# Efficient query with joins
query = (
    select(WorkflowRunModel)
    .options(
        selectinload(WorkflowRunModel.user),
        selectinload(WorkflowRunModel.organization)
    )
    .limit(limit)
    .offset(offset)
)
```

### 9.3 Caching

**Global settings:** Cache in memory for 5 minutes
```python
from functools import lru_cache
from datetime import datetime, timedelta

_settings_cache = {}
_cache_expiry = {}

async def get_global_setting(key: str):
    if key in _settings_cache and _cache_expiry[key] > datetime.now():
        return _settings_cache[key]
    
    value = await db_fetch_setting(key)
    _settings_cache[key] = value
    _cache_expiry[key] = datetime.now() + timedelta(minutes=5)
    return value
```

---

## 10. Deployment Considerations

### 10.1 Migration Execution Order

1. Apply existing migration: `alembic upgrade a1b2c3d4e001`
2. Create and apply moderation tables migration
3. Create and apply billing tables migration
4. Create and apply notification tables migration
5. Create and apply audit log migration
6. Create and apply CRM tables migration
7. Create and apply column additions migration

**Command:**
```bash
cd api
alembic upgrade head
```

### 10.2 Backwards Compatibility

**New columns with defaults:** All new columns have default values, no data migration needed.

**New tables:** No existing data to migrate, start empty.

**Breaking changes:** None - all changes are additive.

### 10.3 Rollback Plan

Each migration has a `downgrade()` function:
```bash
alembic downgrade -1  # Rollback one migration
```

---

## 11. Monitoring & Observability

### 11.1 Metrics to Track

- Admin actions per hour (audit log count)
- Credit transactions per day
- User bans per day
- Notification delivery success rate
- Call moderation queue length
- API response times for admin endpoints

### 11.2 Logging

**Structured logging for key events:**
- User banned: `logger.warning("User banned", extra={"user_id": 123, "admin_id": 1})`
- Credits adjusted: `logger.info("Credits added", extra={"org_id": 456, "amount": 500})`
- Notification broadcast: `logger.info("Notification sent", extra={"notification_id": 789, "users": 1000})`

---

## Acceptance Criteria

✅ This design document is complete when:
- All API endpoints specified with request/response schemas
- Database migration plan defined with sequence
- Frontend component architecture documented
- Service layer implementations designed
- Integration patterns with existing systems specified
- Security considerations addressed
- Performance optimizations planned
- Testing strategy defined
- Deployment plan documented

**Status:** ✅ COMPLETE

**Next Step:** Create tasks.md breaking down implementation into actionable tasks.
