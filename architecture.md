# Architecture

DPM Service — internal architecture reference. This document describes the
runtime structure, data model, authentication flow, and conventions used by
the project as it stands today.

## Overview

- **Framework:** Django 5.2
- **Python:** 3.10.1 (pinned via `.python-version` / pyenv)
- **Database (dev):** SQLite (`db.sqlite3`)
- **Templating:** Django templates with `APP_DIRS=True`
- **Frontend:** Tailwind CSS via Play CDN (`https://cdn.tailwindcss.com`)
  — **dev only**; must be replaced with a built Tailwind asset pipeline
  before any production deployment.
- **Form rendering:** `django-crispy-forms` + `crispy-tailwind` template pack

## Project Layout

```
dpmservice1/
├── manage.py
├── architecture.md          # this file
├── coding_rules.md
├── dpmservice/              # project package (settings, root urls, wsgi/asgi)
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── accounts/                # users, auth, roles
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── migrations/
│   └── templates/accounts/
├── clients/                 # clients, employees, branches, homeworkers, locations
│   ├── models.py            # Client, Employee, Branch, Homeworker, Location
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   ├── migrations/
│   └── templates/clients/
├── tickets/                 # service tickets
├── assets/                  # inventory / assets
├── hosting/                 # domain & hosting, AMC
├── masters/                 # states, cities, service types, asset types
├── dashboard/               # dashboard views
├── comments/                # ticket comments
├── notifications/           # notification system
├── authorization/           # roles & permissions
├── system/                  # backup & restore
└── network/                 # subnets, IPs, devices
```

## Apps

### `accounts`

Owns the user identity layer: custom user model, authentication views,
profile management, and the administrative user list.

It exposes no public Python API beyond the standard Django user contract
(`get_user_model()`, role properties on the user instance, and `role_required`
in `accounts.views`).

## Data Model

### `User` (`accounts.User`)

Custom user inheriting from `AbstractBaseUser + PermissionsMixin`. Replaces
the default `username` field with `email`.

| Field          | Type            | Notes                                      |
|----------------|-----------------|--------------------------------------------|
| `email`        | EmailField (unique) | Login identifier (`USERNAME_FIELD`).   |
| `first_name`   | CharField(150)  | Optional.                                  |
| `last_name`    | CharField(150)  | Optional.                                  |
| `role`         | CharField(20)   | Enum: `admin`, `manager`, `staff`, `client`. Default `client`. |
| `is_active`    | BooleanField    | Login allowed when `True`.                 |
| `is_staff`     | BooleanField    | Controls Django admin access (orthogonal to `role`). |
| `is_superuser` | BooleanField    | From `PermissionsMixin`.                   |
| `date_joined`  | DateTimeField   | Auto on create.                            |
| `last_login`   | DateTimeField   | Managed by Django auth.                    |

Helper properties on `User`:
- `is_admin`, `is_manager`, `is_staff_member`, `is_client` (role checks).
  Note: `is_staff_member` exists deliberately to avoid collision with
  Django's built-in `is_staff` field.

### Roles

| Role     | Self-register | Admin site | `role_required` access |
|----------|---------------|------------|------------------------|
| Admin    | No (created by admin) | Yes (`is_staff=True`) | All role-gated views |
| Manager  | No            | Yes (`is_staff=True` by `create_manager`) | Manager-and-above views |
| Staff    | No            | Yes (`is_staff=True` by `create_staff`)   | Staff views |
| Client   | Yes (default for `register_view`) | No  | Client views only |

Public registration via `register_view` always creates a `client`-role user.
Higher roles must be created through the Django admin or
`User.objects.create_manager/staff/superuser`.

## Authentication

- **Login identifier:** email (case-normalised via `BaseUserManager.normalize_email`
  and `clean_email`).
- **Backend:** Django's default `ModelBackend`. Because `USERNAME_FIELD = 'email'`,
  passing the email as `username` to `authenticate()` is the canonical pattern.
- **Login flow:** `EmailLoginForm` → `authenticate()` → `login(request, user)`.
  Honours an optional `next` parameter from POST or GET.
- **Logout flow:** POST-only (CSRF-protected) via `logout_view`.
- **Authorization:** Two layers.
  1. `@login_required` on any view requiring authentication.
  2. `@role_required(*roles)` (in `accounts.views`) for role-gated views.
     Superusers bypass role checks.
- **Settings:**
  - `LOGIN_URL = 'accounts:login'`
  - `LOGIN_REDIRECT_URL = 'accounts:dashboard'`
  - `LOGOUT_REDIRECT_URL = 'accounts:login'`

## URL Structure

Root URLconf: `dpmservice/urls.py`.

| Path                     | Include                |
|--------------------------|------------------------|
| `/admin/`                | `django.contrib.admin` |
| `/accounts/`             | `accounts.urls` (namespace: `accounts`) |
| `/company/`              | `clients.urls` (namespace: `clients`) |

Within `accounts.urls`:

| Name                       | Path                          | Access                |
|----------------------------|-------------------------------|-----------------------|
| `accounts:register`        | `/accounts/register/`         | Anonymous             |
| `accounts:login`           | `/accounts/login/`            | Anonymous             |
| `accounts:logout`          | `/accounts/logout/` (POST)    | Authenticated         |
| `accounts:dashboard`       | `/accounts/dashboard/`        | Authenticated (per-role template) |
| `accounts:profile`         | `/accounts/profile/`          | Authenticated         |
| `accounts:profile_edit`    | `/accounts/profile/edit/`     | Authenticated         |
| `accounts:password_change` | `/accounts/profile/password/` | Authenticated         |
| `accounts:user_list`       | `/accounts/users/`            | Admin or Manager      |
| `accounts:user_detail`     | `/accounts/users/<id>/`       | Admin only            |

Within `clients.urls` (mounted at `/company/`):

| Name                       | Path                          | Access                |
|----------------------------|-------------------------------|-----------------------|
| `clients:branch_list`      | `/company/branches/`          | Admin or Manager      |
| `clients:branch_create`    | `/company/branches/new/`      | Admin or Manager      |
| `clients:branch_update`    | `/company/branches/<pk>/edit/`| Admin or Manager      |
| `clients:branch_delete`    | `/company/branches/<pk>/delete/`| Admin or Manager    |
| `clients:client_list`      | `/company/clients/`           | Admin or Manager      |
| `clients:employee_list`    | `/company/employees/`         | Admin or Manager      |
| `clients:homeworker_list`  | `/company/homeworkers/`       | Admin, Manager, Client|
| `clients:location_list`    | `/company/locations/`         | Admin or Manager      |

## Views

All views are **function-based**. Class-based views are not used in this
project (see `coding_rules.md`).

Each view explicitly declares its HTTP methods via
`@require_http_methods([...])`. Mutating views are `@csrf_protect` (implicit
through Django middleware, but stated explicitly on auth-adjacent views).
Authentication views are `@never_cache` to prevent stale auth UI.

## Forms

`accounts/forms.py` owns all form validation and password handling:

| Form                     | Purpose                                              |
|--------------------------|------------------------------------------------------|
| `UserRegistrationForm`   | Public self-registration; locks role to `client`.    |
| `EmailLoginForm`         | Email + password authentication; mirrors `AuthenticationForm` API (`get_user()`). |
| `ProfileUpdateForm`      | User edits own first/last name + email.              |
| `AdminUserCreationForm`  | Admin creates a user of any role.                    |
| `AdminUserChangeForm`    | Admin edits a user (read-only hashed password field).|

All forms perform their own `clean_email` to enforce case-insensitive uniqueness.
Password forms call `password_validation.validate_password`.

## Admin

`accounts/admin.py` registers `User` with `UserAdmin` (subclass of Django's
`BaseUserAdmin`) using the two admin forms above. Fieldsets group personal
info, role/permissions, and timestamps separately.

## Frontend

- Tailwind utility classes only. No custom CSS files.
- Layout via `accounts/templates/accounts/base.html`.
- Forms rendered with `{% load crispy_forms_tags %}` and `{{ form|crispy }}`.
- Per-role dashboard: `dashboard_view` dispatches to one of four templates
  based on `request.user.role`.

## Migrations

- One migration per logical schema change.
- Initial migration: `accounts/migrations/0001_initial.py` (creates `User`).
- Migrations are committed alongside the model changes they accompany.

## Configuration & Secrets

Currently `SECRET_KEY` is hardcoded in `dpmservice/settings.py` (development
default produced by `startproject`). Before deployment:

- Move `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, database credentials, and any
  third-party keys into environment variables.
- Replace the Tailwind Play CDN with a built Tailwind bundle.
- Switch the database from SQLite to PostgreSQL (or equivalent).

### `clients` app

Owns client, employee, homeworker, location, and **branch** management.

#### `Branch` (`clients.Branch`)

Represents a physical branch/office of a client company.

| Field       | Type              | Notes                                  |
|-------------|-------------------|----------------------------------------|
| `name`      | CharField(200)    | Branch name.                           |
| `address`   | TextField         | Branch address.                        |
| `city`      | FK → masters.City | Optional (`null=True, blank=True`).    |
| `state`     | FK → masters.State| Optional (`null=True, blank=True`).    |
| `pincode`   | CharField(10)     | Optional.                              |
| `is_active` | BooleanField      | Default `True`.                        |
| `created_at`| DateTimeField     | Auto on create.                        |
| `updated_at`| DateTimeField     | Auto on update.                        |

#### `Client` (`clients.Client`)

Business client using DPM services. Has an optional FK to `Branch`.

| Field          | Type              | Notes                                  |
|----------------|-------------------|----------------------------------------|
| `user`         | OneToOne → User   | Optional (`null=True`). Links to user with `role=CLIENT`. |
| `company_name` | CharField(200)    | Client company name.                   |
| `branch`       | FK → Branch       | Optional (`null=True, blank=True`). Client belongs to one branch. |
| ...            | ...               | (other fields unchanged)              |

#### `Employee` (`clients.Employee`)

ARWASYS employee handling DPM services. Has M2M to `Branch`.

| Field      | Type              | Notes                                  |
|------------|-------------------|----------------------------------------|
| `user`     | OneToOne → User   | Links to user with `role=STAFF`.       |
| `branches` | M2M → Branch      | Blank allowed. Employee can belong to multiple branches. |
| ...        | ...               | (other fields unchanged)              |

#### Relationships

```
Branch (1) ──→ (M) Client       # Client.branch
Branch (M) ←─→ (M) Employee     # Employee.branches (M2M)
```

## Out of Scope (Future Work)

- Email verification / password reset flows
- Two-factor authentication
- Audit log of admin actions on users
- API surface (DRF or similar) — not yet introduced
- Production-grade static asset pipeline
