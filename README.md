# Task Management System (TMS)

Task Management System (TMS) is a Django-based intern task tracking platform that enables administrators and supervisors to assign work, monitor progress, evaluate performance, and manage task approval workflows through a secure role-based system.

Three roles, one app: **Admins** run the system, **Supervisors** mentor and approve, **Interns** do the work and report progress.

---

## Features

- **Authentication & Authorization** — secure login/logout, role-based access control (Admin / Supervisor / Intern), password change, profile editing.
- **Task Management** — create, assign, prioritize, edit, and delete tasks; status tracking (Pending → In Progress → Completed).
- **Progress Tracking** — interns log progress updates with percentage completion; full history kept per task; dashboards summarize status counts.
- **Feedback & Approval Workflow** — supervisors/admins leave comments and ratings on tasks, and must explicitly approve a completed task.
- **Performance Evaluations** — periodic, structured evaluations of interns (score, strengths, areas for improvement) separate from per-task comments.
- **In-App Notifications** — bell-icon notifications for new task assignments, progress updates, feedback, approvals, and upcoming deadlines.
- **Reporting & Analytics** — task breakdowns by status/priority, per-intern completion rates, overdue tracking, CSV export.
- **Audit Logging** — security-relevant events (logins, failed logins, account changes, deletions, approvals) are logged to `logs/security.log`.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Backend | Django 5.0 (Python 3.10+) |
| Frontend | Django Templates + Bootstrap 5 (via CDN, no build step) |
| Database | SQLite (file-based, zero setup) |
| Auth | Django's built-in auth system, custom `User` model with `role` field |

---

## Project Structure

```
tms/
├── config/                 # Project-level settings, root URLs, WSGI/ASGI
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── core/                   # Shared infrastructure: RBAC mixins, middleware, home redirect
│   ├── mixins.py           #   RoleRequiredMixin and role-specific subclasses
│   ├── middleware.py       #   Force-logout of deactivated accounts
│   └── management/commands/seed_demo_data.py
├── accounts/                # Custom User model, auth views, admin user management
│   ├── models.py            #   User (role field), AuditLog
│   ├── forms.py
│   ├── views.py
│   └── signals.py           #   Login/logout/failed-login audit logging
├── tasks/                   # Task CRUD, progress updates, approval workflow
│   ├── models.py             #   Task, ProgressUpdate, ActivityLog
│   ├── views.py               #   Role + ownership-scoped querysets throughout
│   └── management/commands/send_deadline_reminders.py
├── feedback/                 # Comments and structured performance evaluations
│   └── models.py              #   FeedbackItem, PerformanceEvaluation
├── notifications/             # In-app notification bell
│   ├── models.py
│   ├── services.py            #   notify() — single creation entry point
│   └── context_processors.py  #   Makes unread count available in every template
├── reports/                   # Read-only analytics & CSV export
│   └── views.py
├── templates/                  # All HTML templates (mirrors app structure)
├── static/css/styles.css
├── requirements.txt
├── .env.example
├── .gitignore
└── manage.py
```

---

## Getting Started

### 1. Prerequisites
- Python 3.10 or later
- pip

### 2. Clone / unzip and enter the project
```bash
cd tms
```

### 3. Create and activate a virtual environment
```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 4. Install dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure environment variables
```bash
cp .env.example .env
```
Then open `.env` and generate a real secret key:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```
Paste the output into `DJANGO_SECRET_KEY` in `.env`.

### 6. Run migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Create your own admin account
```bash
python manage.py createsuperuser
```
Follow the prompts (the account is automatically given the `admin` role and superuser status).

**Optional:** instead of (or in addition to) step 7, seed some demo accounts and a sample task so you can explore the app immediately:
```bash
python manage.py seed_demo_data
```
This creates:
| Username | Password | Role |
|---|---|---|
| `admin` | `AdminPass123!` | Administrator |
| `supervisor1` | `SuperPass123!` | Supervisor |
| `intern1` | `InternPass123!` | Intern |

> **Change these passwords (or delete these accounts) before deploying anywhere other than your own machine.**

### 8. Run the development server
```bash
python manage.py runserver
```
Visit **http://127.0.0.1:8000/** and log in.

---

## Optional: Scheduled Deadline Reminders

`send_deadline_reminders` notifies interns of tasks due within the next 24 hours. It's idempotent (safe to run repeatedly) and designed to run on a schedule:

```bash
python manage.py send_deadline_reminders
```

Example cron entry (runs hourly):
```
0 * * * * cd /path/to/tms && /path/to/venv/bin/python manage.py send_deadline_reminders
```

---

## Roles & Permissions at a Glance

| Action | Admin | Supervisor | Intern |
|---|:---:|:---:|:---:|
| Create / deactivate user accounts | ✅ | ❌ | ❌ |
| Create & assign tasks | ✅ (anyone) | ✅ (own interns only) | ❌ |
| Edit / delete tasks | ✅ | ✅ (own interns' tasks) | ❌ |
| View task | ✅ (all) | ✅ (own interns' only) | ✅ (own only) |
| Submit progress update | ❌ | ❌ | ✅ (own tasks only) |
| Approve completed task | ✅ | ✅ (own interns' tasks) | ❌ |
| Leave feedback / comments | ✅ | ✅ (own interns' tasks) | ❌ |
| Write performance evaluations | ✅ | ✅ (own interns only) | ❌ |
| View own evaluations | — | — | ✅ |
| View reports & export CSV | ✅ (org-wide) | ✅ (own team only) | ❌ |

All permissions are enforced on the server using Django role-based access control and object-level authorization.
---

## Security Measures Implemented

- **Password hashing** via Django's default PBKDF2 algorithm (salted, iterated); minimum length and common-password validators enabled.
- **CSRF protection** on every state-changing form (Django's `{% csrf_token %}` + middleware); destructive actions (delete user, delete task) are POST-only, never reachable via a GET link.
- **SQL injection protection** — all data access goes through the Django ORM; there is no raw SQL anywhere in the codebase.
- **XSS protection** — Django templates auto-escape all variables by default; no `|safe` filter is used on user-supplied content.
- **Clickjacking protection** — `X-Frame-Options: DENY`.
- **Session security** — `HttpOnly` cookies, 8-hour expiry, secure cookies forced on automatically outside `DEBUG` mode, sessions expire on browser close.
- **Object-level authorization** — every queryset returning tasks/users/notifications/evaluations is pre-filtered to what the requesting user is allowed to see, closing IDOR (insecure direct object reference) gaps.
- **Privilege escalation prevention** — the form a user fills out to edit their own profile cannot touch `role`, `is_active`, `is_staff`, `is_superuser`, or `supervisor`; only an admin's separate form can.
- **Account deactivation enforcement** — a custom middleware force-logs-out any session belonging to an account an admin has just deactivated, instead of waiting for the session to expire naturally.
- **Audit trail** — logins, failed logins, logouts, password changes, user creation/deactivation/deletion, task creation/approval, and report exports are all logged to `logs/security.log`, and account-management events are additionally stored in the `AuditLog` database table (read-only in Django admin — entries can never be edited or deleted through the app).
- **Self-lockout prevention** — an admin cannot delete their own account.
- **Secrets out of source control** — `SECRET_KEY` and all environment-specific config are loaded from `.env`, which is git-ignored; `.env.example` documents what's needed without exposing real values.
- **Production-ready settings** — `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, and HSTS headers automatically turn on whenever `DEBUG=False`.
- **Upload size limits** — request body size is capped to mitigate denial-of-service via oversized uploads.





## Author
**Smriti Giri**
Bachelor of Information Technology Student



