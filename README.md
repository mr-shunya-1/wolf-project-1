# Trekking Management Application (TMA)

A role-based trekking management platform for **Admin**, **Trek Staff**, and **Users (Trekkers)** — trek creation & approval, staff assignment, slot-aware booking, booking history, caching, and scheduled/async background jobs.

See [PLAN.md](PLAN.md) for the build plan and architecture rationale.

## Tech stack

| Purpose | Technology |
|---|---|
| API / backend | Python 3, Flask |
| UI | Vue 3 (loaded via CDN, no Node/npm build step) + Bootstrap 5 |
| Database | SQLite (created programmatically on first run — no manual DB tooling) |
| Cache | Redis |
| Background jobs | Celery (worker + beat), Redis as broker/result backend |
| Charts | Chart.js (CDN) |

No Node.js, npm, or any frontend build tool is required — Vue and Bootstrap are pulled from CDN inside the single Jinja2 entry page.

## Prerequisites

Install these before doing anything else:

| Requirement | Version | Check with |
|---|---|---|
| Python | 3.10+ | `python3 --version` |
| pip | bundled with Python | `pip3 --version` |
| Redis server | 6.x+ | `redis-server --version` |
| git | any | `git --version` |

Redis install:

- **macOS (Homebrew):** `brew install redis`
- **Ubuntu/Debian:** `sudo apt update && sudo apt install redis-server`
- **Windows:** use WSL2 + the Ubuntu instructions above, or Redis' official Docker image (`docker run -p 6379:6379 redis:7`)

## Installation

```bash
# 1. clone and enter the project
git clone <this-repo-url>
cd wolf-project-1

# 2. create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. install python dependencies
pip install -r requirements.txt

# 4. copy the environment template and adjust if needed
cp .env.example .env
```

`requirements.txt` (installed above) covers: `flask`, `flask-sqlalchemy`, `flask-caching`, `celery`, `redis`, `flask-mail`, `python-dotenv`, `reportlab` (or `weasyprint`, for PDF reports).

## Running the app locally

You need **three processes running at the same time**, each in its own terminal tab, with the virtual environment activated in each.

**Terminal 1 — Redis** (skip if you already have a Redis service running):

```bash
redis-server
```

**Terminal 2 — Celery worker + beat** (handles reminders, monthly reports, CSV export):

```bash
celery -A app.tasks worker --beat --loglevel=info
```

**Terminal 3 — Flask app** (creates the SQLite DB and the single Admin account on first launch):

```bash
python run.py
```

Then open **http://localhost:5000** in your browser.

## Default ports

| Service | Default port | Configurable via |
|---|---|---|
| Flask app | `5000` | `FLASK_RUN_PORT` in `.env` |
| Redis | `6379` | `REDIS_URL` in `.env` |
| Celery | no listening port (connects out to Redis) | `CELERY_BROKER_URL` in `.env` |

If port `5000` or `6379` is already taken on your machine, change the corresponding value in `.env` and restart the affected process.

## Environment variables (`.env`)

| Variable | Default | Purpose |
|---|---|---|
| `FLASK_RUN_PORT` | `5000` | Flask dev server port |
| `SECRET_KEY` | *(set your own)* | Flask session signing key |
| `SQLALCHEMY_DATABASE_URI` | `sqlite:///tma.db` | SQLite file location |
| `REDIS_URL` | `redis://localhost:6379/0` | Cache backend |
| `CELERY_BROKER_URL` | `redis://localhost:6379/1` | Celery broker |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/2` | Celery result store |
| `MAIL_SERVER` / `MAIL_PORT` / `MAIL_USERNAME` / `MAIL_PASSWORD` | *(your SMTP)* | Outbound email for reminders & monthly report |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | `admin@tma.local` / `admin123` | Seeded on first run — **change after first login** |

## First run — what happens automatically

On the first `python run.py`:

1. SQLite tables are created programmatically (`app/seed.py`), never via manual DB tooling.
2. The single Admin account is created from `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env`.
3. No further manual setup is needed — register a Trekker account from the UI, and have the Admin create Staff accounts and treks from the Admin dashboard.

## Logging in

| Role | How to get an account |
|---|---|
| Admin | Pre-seeded — use `ADMIN_EMAIL` / `ADMIN_PASSWORD` from `.env` |
| Trek Staff | Created by Admin from the Admin dashboard (no self-registration) |
| User (Trekker) | Self-register from the app's Register page |

## Background jobs reference

| Job | Trigger | What it does |
|---|---|---|
| Daily reminders | Celery Beat, once/day | Notifies users about upcoming treks (email/webhook) |
| Monthly activity report | Celery Beat, 1st of each month | Emails Admin an HTML/PDF report of treks conducted, participation, popular treks |
| Booking history export | User-triggered from dashboard | Async CSV export of the user's booking history, with a completion alert |

## Troubleshooting

- **`redis.exceptions.ConnectionError`** — Redis isn't running; start it with `redis-server`, or check `REDIS_URL` in `.env`.
- **Celery tasks never run** — confirm the worker+beat terminal is still open and pointed at the same Redis instance as the Flask app.
- **Port already in use** — change `FLASK_RUN_PORT` in `.env`, or stop whatever else is bound to `5000`.
- **DB looks stale/corrupted** — delete `tma.db` and restart `python run.py`; it will be recreated and re-seeded.

## Note on code style

Per project requirements, application code in this repository intentionally avoids conventional identifier naming and inline comments. The rationale and full disclosure of tooling/assistance used is documented in the final project report (not in this README).
