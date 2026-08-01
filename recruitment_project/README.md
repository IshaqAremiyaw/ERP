# RecruitPro — Django + Bootstrap Recruitment System

A full recruitment/HR system: applicant registration & job applications,
HR-controlled job postings, application review, interview scheduling,
analytics, and employee management. SQLite by default, PostgreSQL-ready.

## Features (and where to find them)

| Feature | URL | Notes |
|---|---|---|
| 🏠 Dashboard | `/dashboard/` | Routes to applicant or HR view by role |
| 🔐 Login & Registration | `/login/`, `/register/` | Separate applicant/HR signup flows |
| 👤 Applicant Portal | `/applicant/dashboard/` | Stats + recent applications |
| 💼 Job Listings | `/jobs/` | Public, searchable |
| 📝 Apply for Jobs | `/jobs/<id>/apply/` | Cover letter + resume upload |
| 📄 Resume Upload | `/applicant/resume/` | Also editable from profile |
| 📊 HR Dashboard | `/hr/dashboard/` | Org-wide stats |
| 📅 Interview Scheduling | `/hr/interviews/` | Schedule/edit, auto-updates application status |
| 📈 Recruitment Analytics | `/hr/analytics/` | Chart.js funnel + top jobs |
| 👥 Employee Management | `/hr/employees/` | Auto-created when an application is marked "Hired" |
| 📧 Email Notifications | — | Console backend by default; fires on apply, status change, interview scheduled |

## Setup

```bash
pip install -r requirements.txt
python manage.py makemigrations recruitment
python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver
```

Visit `http://127.0.0.1:8000/`. Emails print to the terminal (console backend) —
check the terminal running `runserver` to see notification content.

### HR signup

HR registration (`/register/hr/`) requires an invite code. The default
for local testing is `HR-ONBOARD-2026` — set in
`recruitment/forms.py` (`HRRegistrationForm.HR_INVITE_CODE`). Replace
this with an environment variable or DB-backed code before deploying.

## Running tests

```bash
python manage.py test recruitment
```

Covers model behavior (status transitions, history logging, one-application-
per-job) and view-level smoke tests (dashboards, role gating, apply flow).

## Switching to PostgreSQL

1. `pip install psycopg2-binary`
2. In `config/settings.py`, swap the `DATABASES` block for the commented-out
   PostgreSQL example already there, and set these environment variables:
   `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
3. Re-run `python manage.py migrate`

## Switching email to real SMTP

In `config/settings.py`, comment out the console `EMAIL_BACKEND` line and
uncomment the SMTP block underneath it, filling in your provider's host,
port, and credentials (e.g. Gmail app password, SendGrid, etc.).

## Notes

- Resumes and other uploads are stored in `/media/` (served locally in
  DEBUG mode only — use S3 or similar in production).
- The `Employee` model is created automatically the first time an
  application's status is set to `HIRED` from the review screen.
