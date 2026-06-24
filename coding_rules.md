# Coding Rules

Conventions in this codebase. Rules marked **MUST** are non-negotiable;
**SHOULD** rules are defaults that may be overridden with justification.

## Python

- **MUST** target Python 3.10+. Use language features freely (`match`,
  `|` unions, `Self`, etc.).
- **MUST** follow PEP 8. 4-space indentation. Maximum line length is a soft
  100; do not chase 79.
- **SHOULD** use type hints on function signatures of any non-trivial helper.
  View functions and form methods are exempt because their types are dictated
  by Django.
- **MUST NOT** wrap obviously-named code in comments. Comments explain *why*,
  never *what*. The code should already say *what*.

## Django

- **MUST** use **function-based views (FBV)** for HTTP request handlers.
  Class-based views (generic or otherwise) are not used in this project.
- **MUST** decorate each FBV with:
  1. `@login_required` or `@role_required(...)` (authorization, outermost)
  2. `@csrf_protect` if the view writes state (often implicit; declare it on
     auth-related views regardless)
  3. `@never_cache` on auth-flow views (login, register, logout)
  4. `@require_http_methods([...])` (innermost) to constrain methods
- **MUST** use Django's URL `reverse` / `{% url %}`. **MUST NOT** hardcode
  paths in code or templates.
- **MUST** namespace app `urls.py` with `app_name = '<app>'`.
- **SHOULD** pin one URL per logical view; do not piggyback unrelated behaviour
  on a single endpoint.
- **MUST** redirect-after-POST on successful form submission. Render the form
  back (without redirect) on validation failure.

## Models

- **MUST** define `__str__` for any model with a UI presence.
- **MUST** set `class Meta: verbose_name`, `verbose_name_plural`, and a
  default `ordering` when the model is listed in the admin or any view.
- **SHOULD** wrap user-facing strings (`verbose_name`, field labels,
  validation errors) in `gettext_lazy` even if i18n is not yet enabled.
- **MUST** use `TextChoices` / `IntegerChoices` for enum-like fields. No
  free-form magic strings.
- **MUST NOT** add business logic to model managers that belongs on a
  service layer; managers are for query helpers and object creation only.
- **MUST** prefer `email__iexact` lookups (and similar) over relying on the
  field's normalized form to avoid duplicate identities.

## Forms

- **MUST** validate per-field in `clean_<field>` and cross-field in `clean`.
- **MUST** run passwords through `password_validation.validate_password`
  before saving.
- **MUST** normalise emails to lowercase in `clean_email`.
- **SHOULD** raise `forms.ValidationError` with a translatable message;
  never raise bare exceptions for user input.

## Templates

- **MUST** extend `accounts/templates/accounts/base.html` (or the relevant
  app base) for any rendered page.
- **MUST** render forms via `{% load crispy_forms_tags %}` + `{{ form|crispy }}`
  unless there is a documented reason for hand-rolling the markup.
- **MUST** use `{% url 'namespace:name' %}` for links.
- **MUST** include `{% csrf_token %}` in every POST form.
- **SHOULD** keep templates dumb: no business logic, only presentation and
  trivial conditionals.
- Tailwind utility classes only. **MUST NOT** introduce a `static/css/*.css`
  file without prior discussion.

## URLs

- **MUST** use kebab-case in URL paths (`profile/edit/`, not
  `profileEdit/` or `profile_edit/`).
- **MUST** name every URL pattern (`name='...'`).
- **MUST** end paths with a trailing slash (Django's `APPEND_SLASH` default).

## Imports

Order, separated by single blank lines:

1. Standard library
2. Third-party (including Django)
3. Local app imports (relative `.module` first, then sibling apps)

`from x import a, b, c` over multiple `import` lines for the same module.
Alphabetise within each group.

## Naming

- **Modules:** `snake_case`.
- **Classes:** `PascalCase`.
- **Functions / variables:** `snake_case`.
- **Constants:** `UPPER_SNAKE_CASE`.
- **Templates:** `snake_case.html`.
- **URL names:** `snake_case`, scoped by app namespace.
- **View functions:** suffix with `_view` (e.g. `login_view`) to disambiguate
  from helpers.

## Security

- **MUST NOT** commit `SECRET_KEY`, database credentials, API keys, or any
  other secret. Use environment variables.
- **MUST NOT** log passwords, raw tokens, or full PII.
- **MUST** use Django's `set_password` / `check_password`; never compare
  password hashes manually.
- **MUST** require POST for any state-changing action (including logout).

## Migrations

- **MUST** commit migrations alongside the model change that produced them.
- **MUST** review migrations before commit. Auto-generated names are fine
  for initial migrations; rename or `--name` for clarity on subsequent ones.
- **MUST NOT** edit applied migrations on a shared branch. Add a new
  migration to amend the schema.

## Testing

- **SHOULD** add at minimum a smoke test for any new view: request → expected
  status / template.
- Test layout: `<app>/tests.py` for now; split into `tests/` package once a
  file exceeds ~300 lines.
- Test runner: Django's built-in (`python3 manage.py test`). pytest may be
  introduced later; if so, document it here.

## Dependencies

- **MUST** justify each new third-party package in the PR / commit message.
- **SHOULD** prefer Django built-ins over third-party packages when the gap
  is small.
- Pinned dependencies will live in `requirements.txt` (TODO — not yet
  introduced).

## Commits

- **MUST** write commits in present tense, imperative mood
  ("Add user list view", not "Added" / "Adds").
- **SHOULD** keep one logical change per commit. Refactors separate from
  feature work.
- **MUST NOT** commit generated files (`__pycache__/`, `*.pyc`, `db.sqlite3`,
  `.python-version` is acceptable but project-team's call).

## Code Review Checklist

Before requesting review, the author has checked:

- [ ] `python3 manage.py check` is clean.
- [ ] `python3 manage.py makemigrations --check --dry-run` finds nothing.
- [ ] New URLs are namespaced and named.
- [ ] New views use the decorator stack from the **Django** section.
- [ ] New forms validate email/password per the **Forms** section.
- [ ] Templates extend the project base and use `{% csrf_token %}` where needed.
- [ ] No secrets in the diff.
