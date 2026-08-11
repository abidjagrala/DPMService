# Architecture

DPM Service — internal architecture reference. This document describes the
runtime structure, data model, authentication flow, authorization system, and
conventions used by the project.

## Overview

- **Framework:** Django 5.2
- **Python:** 3.10.1 (pinned via `.python-version` / pyenv)
- **Database (dev):** SQLite (`db.sqlite3`)
- **Database (prod):** MySQL (via `DJANGO_MODE=production`)
- **Templating:** Django templates with `APP_DIRS=True`
- **Frontend:** Tailwind CSS via built pipeline (`static/dist/`), DaisyUI components, HTMX
- **Form rendering:** `django-crispy-forms` + `crispy-tailwind` template pack
- **Charts/Reports:** ReportLab (PDF generation)
- **2FA:** pyotp (TOTP), qrcode
- **AI:** OpenAI-compatible API integration

## Project Layout

```
dpmservice1/
├── manage.py
├── architecture.md
├── coding_rules.md
├── requirements.txt
├── dpmservice/              # project package (settings, root urls, wsgi)
│   ├── settings.py
│   ├── urls.py
│   ├── views.py             # error handlers (400, 403, 404, 500)
│   └── wsgi.py
├── accounts/                # users, auth, roles, settings (mail/sms/whatsapp)
├── clients/                 # clients, employees, branches, locations
├── tickets/                 # service tickets
├── assets/                  # inventory / assets / assignments
├── hosting/                 # domain & hosting, AMC
├── masters/                 # states, cities, service types, asset types, transport types
├── network/                 # subnets, IPs, network devices
├── dashboard/               # dashboard views & KPIs
├── comments/                # generic comments (via contenttypes)
├── notifications/           # email/SMS/WhatsApp notification dispatch
├── authorization/           # RBAC: roles, module/model/field/menu permissions
├── system/                  # backup & restore
├── ai/                      # AI tools (chat, suggestions, settings)
└── api/                     # REST API (DRF)
```

## Apps Summary

| App | Module Code | Purpose |
|-----|-------------|---------|
| `accounts` | `settings` | User model, auth, 2FA, profile, mail/SMS/WhatsApp settings |
| `clients` | `clients`, `employees` | Client, Employee, Branch, Location management |
| `tickets` | `tickets` | Service ticket CRUD, status, PDF, comments |
| `assets` | `assets` | Asset management, assignments, returns |
| `hosting` | `domain_hosting` | Domain/hosting management, invoices, AMC |
| `masters` | `masters` | Reference data: State, City, ServiceType, AssetType, TransportType |
| `network` | `devices` | Network devices (subnets, IPs, devices) |
| `dashboard` | `dashboard` | Dashboard KPIs and summaries |
| `comments` | — | Generic comment system (contenttypes framework) |
| `notifications` | `notifications` | Email/SMS/WhatsApp dispatch via MSG91 |
| `authorization` | `authorization` | Full RBAC system (see below) |
| `system` | `system` | Database backup & restore |
| `ai` | `ai` | AI chat, suggestions, provider settings |
| `api` | — | REST API endpoints (DRF) |

## Data Model

### `User` (`accounts.User`)

Custom user inheriting from `AbstractBaseUser + PermissionsMixin`. Uses
`email` as `USERNAME_FIELD`.

| Field | Type | Notes |
|-------|------|-------|
| `email` | EmailField (unique) | Login identifier |
| `first_name` | CharField(150) | Optional |
| `last_name` | CharField(150) | Optional |
| `role` | CharField(20) | Enum: `admin`, `manager`, `staff`, `client`. Default `client` |
| `is_active` | BooleanField | Login allowed when True |
| `is_staff` | BooleanField | Controls Django admin access |
| `is_superuser` | BooleanField | From PermissionsMixin |
| `totp_secret` | CharField(32) | TOTP 2FA secret |
| `two_factor_enabled` | BooleanField | 2FA toggle |
| `password_reset_token` | UUIDField | Password reset token |

Helper properties: `is_admin`, `is_manager`, `is_staff_member`, `is_client`.

### Core Models

```
User ──1:1──→ Client (client_profile)     # Client linked to a user
User ──1:1──→ Employee (employee_profile) # Employee linked to a user
Client ──FK──→ Branch                     # Client belongs to a branch
Employee ──M2M──→ Branch                  # Employee can belong to multiple branches

ServiceTicket ──FK──→ Client              # Ticket belongs to a client
ServiceTicket ──FK──→ Employee (assigned_to)
ServiceTicket ──FK──→ User (created_by)
ServiceTicket ──M2M──→ Asset              # Ticket can involve multiple assets
ServiceTicket ──FK──→ ServiceType
ServiceTicket ──FK──→ Location
ServiceTicket ──FK──→ TransportType

TicketComment ──FK──→ ServiceTicket
TicketHistory ──FK──→ ServiceTicket

Asset ──FK──→ Client
Asset ──FK──→ AssetType
AssetAssignment ──FK──→ Asset
AssetAssignment ──FK──→ Employee (holder)

NetworkDevice ──FK──→ Subnet
Subnet ──FK──→ Client

DomainHosting ──FK──→ Client
HostingInvoice ──FK──→ DomainHosting
AMC ──FK──→ Client

Branch ──FK──→ City ──FK──→ State
Location ──FK──→ City
```

## Authentication

- **Login identifier:** email (case-normalised)
- **Backend:** Django's `ModelBackend`
- **2FA:** TOTP via pyotp — optional, user-enabled from profile
- **Login throttle:** 5 attempts, 5-minute lockout
- **Session idle timeout:** 20 minutes (via `IdleSessionMiddleware`)

### Login Flow

```
EmailLoginForm → validate captcha → authenticate()
  ├─ 2FA enabled → redirect to TOTP verify → login()
  ├─ 2FA not set up → redirect to TOTP setup → login()
  └─ No 2FA → login() directly
```

### Settings

```
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'accounts:dashboard'
LOGOUT_REDIRECT_URL = 'accounts:login'
```

## Authorization System (RBAC)

**Location:** `authorization/` app

The authorization system provides granular, configurable permissions per role,
managed via the admin UI at `/authorization/`.

### Permission Layers

1. **Module Permissions** — view/create/edit/delete/export/import per module
2. **Model Permissions** — view/create/edit/delete per model
3. **Field Permissions** — hidden/readonly/editable per field
4. **Menu Permissions** — visibility per sidebar menu item
5. **Notification Settings** — per-role notification preferences

### Module Codes

| Code | Label |
|------|-------|
| `dashboard` | Dashboard |
| `clients` | Clients |
| `employees` | Employees |
| `assets` | Assets |
| `devices` | Devices |
| `tickets` | Tickets |
| `domain_hosting` | Domain & Hosting |
| `masters` | Masters |
| `settings` | Settings |
| `ai` | AI |
| `system` | System |
| `authorization` | Authorization & Roles |
| `notifications` | Notifications |

### Model Names (for ModelPermission)

`client`, `employee`, `asset`, `assetassignment`, `subnet`, `ipaddress`,
`networkdevice`, `serviceticket`, `ticketcomment`, `tickethistory`,
`domainhosting`, `hostinginvoice`, `amc`, `servicetype`, `assettype`,
`transporttype`, `state`, `city`, `location`, `branch`, `user`, `group`, `role`

### How Permissions Are Checked

**Decorators** (in `authorization/services/permission_engine.py`):

```python
@module_required('tickets', 'view')       # module-level check
@model_required('serviceticket', 'create') # model-level check
```

**Permission resolution order:**

1. Superuser → all permissions granted automatically
2. `User.role == 'admin'` → all permissions granted automatically
3. `User.role == 'manager'` → all permissions granted (via role-based defaults)
4. `User.role == 'staff'` → scoped module/model defaults (tickets, assets, devices, hosting)
5. `User.role == 'client'` → scoped module/model defaults (tickets, assets)
6. `UserRoleAssignment` objects → override defaults with explicit RBAC permissions
7. `ModulePermission` / `ModelPermission` records → checked from DB

**Key function:** `get_user_permissions(user)` — aggregates all permissions,
cached in Django cache (5-minute TTL). Call `clear_user_permissions(user_id)`
or `clear_all_permissions()` to invalidate.

### Role-Based Default Permissions (Fallback)

When no `UserRoleAssignment` exists for a user, defaults are applied based on
`User.role`:

| Role | Modules | Models |
|------|---------|--------|
| admin/superuser | All | All |
| manager | All | All |
| staff | dashboard, tickets, assets, devices, domain_hosting | serviceticket, asset, networkdevice, domainhosting |
| client | dashboard, tickets, assets | serviceticket, asset |

### Authorization Admin UI

| URL | View | Purpose |
|-----|------|---------|
| `/authorization/` | `auth_dashboard` | Overview |
| `/authorization/groups/` | CRUD | Group management |
| `/authorization/roles/` | CRUD + clone | Role management |
| `/authorization/permissions/modules/` | Matrix | Module permission editor |
| `/authorization/permissions/models/` | Matrix | Model permission editor |
| `/authorization/permissions/fields/` | Matrix | Field permission editor |
| `/authorization/permissions/menus/` | Matrix | Menu visibility editor |
| `/authorization/assignments/` | CRUD | User-to-role assignment |
| `/authorization/audit-log/` | List | Audit trail |
| `/authorization/seed/` | Action | Seed default modules/menus |

## Error Handling

**File:** `dpmservice/views.py`

Custom error pages for all HTTP error codes:

| Handler | Template | Fallback |
|---------|----------|----------|
| `custom_400` | `accounts/400.html` | Inline HTML |
| `custom_403` | `accounts/403.html` | Inline HTML |
| `custom_404` | `accounts/404.html` | Inline HTML |
| `custom_500` | `accounts/500.html` | Inline HTML |

All handlers use `_safe_render()` which falls back to inline HTML if the
template fails to render (prevents white screen of death in production).

Registered in `dpmservice/urls.py`:
```python
handler400 = custom_400
handler403 = custom_403
handler404 = custom_404
handler500 = custom_500
```

## URL Structure

Root URLconf: `dpmservice/urls.py`.

| Path | Include | Namespace |
|------|---------|-----------|
| `/admin/` | `django.contrib.admin` | — |
| `/accounts/` | `accounts.urls` | `accounts` |
| `/masters/` | `masters.urls` | `masters` |
| `/company/` | `clients.urls` | `clients` |
| `/inventory/` | `assets.urls` | `assets` |
| `/` (root) | `tickets.urls` | `tickets` |
| `/dashboard/` | `dashboard.urls` | `dashboard` |
| `/hosting/` | `hosting.urls` | `hosting` |
| `/comments/` | `comments.urls` | `comments` |
| `/api/` | `api.urls` | `api` |
| `/notifications/` | `notifications.urls` | `notifications` |
| `/authorization/` | `authorization.urls` | `authorization` |
| `/system/` | `system.urls` | `system` |
| `/ai/` | `ai.urls` | `ai` |

## Views

All views are **function-based** (no CBVs).

### Decorator Stack (applied in this order)

```python
@module_required('tickets', 'view')       # authorization check (outermost)
@model_required('serviceticket', 'view')   # model-level authorization
@csrf_protect                              # CSRF protection (POST)
@require_http_methods(['GET', 'POST'])     # method constraint (innermost)
```

### HTMX Support

Views check `is_htmx(request)` to return partial templates for HTMX requests.
HTMX responses use `_hx_toast()` for toast notifications with
`HX-Trigger` headers.

### Ticket Views Permission Matrix

| View | Module Perm | Model Perm | Additional Check |
|------|-------------|------------|-----------------|
| `ticket_list_view` | `tickets.view` | — | Client sees own, Staff sees branch |
| `ticket_create_view` | `tickets.create` | `serviceticket.create` | Client auto-assigned |
| `ticket_update_view` | `tickets.edit` | `serviceticket.edit` | Client: own tickets only |
| `ticket_detail_view` | `tickets.view` | `serviceticket.view` | Client: own tickets only |
| `ticket_status_view` | `tickets.edit` | `serviceticket.edit` | Client: own tickets only |
| `ticket_delete_view` | `tickets.delete` | `serviceticket.delete` | — |
| `ticket_detail_pdf` | `tickets.view` | `serviceticket.view` | Client: own tickets only |
| `ticket_assets_api` | `tickets.view` | — | JSON API |

## Templates

- **Base:** `accounts/templates/accounts/base.html` (full app shell with sidebar, topbar, toasts)
- **App bases:** Each app has its own `base.html` extending `accounts/base.html`
- **Partials:** HTMX-compatible partials prefixed with `_` (e.g., `_ticket_form_partial.html`)
- **Error pages:** `accounts/400.html`, `accounts/403.html`, `accounts/404.html`, `accounts/500.html`
- **CSS:** Tailwind + DaisyUI via `static/dist/main.css`
- **JS:** Alpine.js, HTMX (bundled in `static/dist/`)

### Template Tags

| Tag Library | Tags | Purpose |
|-------------|------|---------|
| `daisy` | `daisy_field`, `daisy_form_errors`, `searchable_select`, `basename` | DaisyUI form rendering |
| `comments` | `show_comments` | Generic comment display |
| `i18n` | `{% trans %}` | Translation |

## Frontend Stack

- **CSS:** Tailwind CSS (built), DaisyUI component library
- **JS:** Alpine.js (reactivity), HTMX (AJAX partials)
- **Theme:** Light/Dark toggle via `data-theme` attribute
- **Searchable Selects:** Custom `searchableSelect` Alpine.js component
- **Quick Add Modals:** Inline creation forms via HTMX

## Configuration & Secrets

All sensitive values read from environment variables via `python-decouple`:

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | Debug mode |
| `DJANGO_MODE` | `development` or `production` |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | MySQL (prod) |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | SMTP |
| `OPENAI_API_KEY`, `AI_MODEL`, `AI_BASE_URL` | AI integration |

## Migrations

- One migration per logical schema change
- Migrations committed alongside model changes
- Never edit applied migrations on shared branches
