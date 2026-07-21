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

`requirements.txt` (installed above) covers: `Flask`, `Flask-SQLAlchemy`, `Flask-Caching`, `celery`, `redis`, `Werkzeug`, `python-dotenv`. Outbound email uses the standard library `smtplib`; the Google Chat reminder uses `urllib` — no extra mail/PDF packages are required.

## Running the app locally

You need **three processes running at the same time**, each in its own terminal tab, with the virtual environment activated in each.

**Terminal 1 — Redis** (skip if you already have a Redis service running):

```bash
redis-server
```

**Terminal 2 — Celery worker + beat** (handles reminders, monthly reports, CSV export):

```bash
celery -A celery_worker.celery worker --beat --loglevel=info
```

**Terminal 3 — Flask app** (creates the SQLite DB and the single Admin account on first launch):

```bash
python run.py
```

Then open **http://127.0.0.1:5001** in your browser.

> **macOS note:** port `5000` is claimed by default by the AirPlay Receiver (Control Center), which will silently intercept the connection and show a confusing 403 page instead of a normal "connection refused". `run.py` therefore defaults to port **5001** — override with the `PORT` env var if you need a different one, and don't fight over `5000` unless you've disabled AirPlay Receiver in System Settings → General → AirDrop & Handoff.

## Default ports

| Service | Default port | Configurable via |
|---|---|---|
| Flask app | `5001` | `PORT` env var |
| Redis | `6379` | `REDIS_URL` in `.env` |
| Celery | no listening port (connects out to Redis) | `CELERY_BROKER_URL` in `.env` |

If port `6379` is already taken on your machine, change `REDIS_URL` (and the matching `CELERY_*` urls) in `.env` and restart the affected process.

## Environment variables (`.env`)

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `5001` | Flask dev server port |
| `FLASK_SECRET` | *(set your own)* | Flask session signing key |
| `SQLITE_PATH` | `sqlite:///tma.db` | SQLite file location |
| `REDIS_URL` | `redis://localhost:6379/0` | Cache backend |
| `CELERY_BROKER_URL` | `redis://localhost:6379/1` | Celery broker |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/2` | Celery result store |
| `MAIL_SERVER` / `MAIL_PORT` / `MAIL_USERNAME` / `MAIL_PASSWORD` | *(your SMTP)* | Outbound email for reminders & monthly report — left blank, mail is skipped and logged to stdout instead |
| `GCHAT_WEBHOOK_URL` | *(your webhook)* | Google Chat reminder delivery — left blank, pings are skipped and logged to stdout instead |
| `BOSS_HANDLE` / `BOSS_CIPHER` | `overseer` / `change-me-please` | The single Admin account, seeded on first run — **change `BOSS_CIPHER` before first launch** |

## First run — what happens automatically

On the first `python run.py`:

1. SQLite tables are created programmatically (`app/models.py` + `ledger.create_all()`), never via manual DB tooling.
2. The single Admin account is created from `BOSS_HANDLE` / `BOSS_CIPHER` in `.env`.
3. No further manual setup is needed — register a Trekker account from the UI, and have the Admin create Staff accounts and treks from the Admin dashboard.

## Logging in

| Role | How to get an account |
|---|---|
| Admin | Pre-seeded — use `BOSS_HANDLE` / `BOSS_CIPHER` from `.env` |
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
- **"Access to localhost was denied" / HTTP 403 on port 5000** — that's macOS AirPlay Receiver, not Flask; use port `5001` (the default here) instead, or disable AirPlay Receiver in System Settings.
- **Port already in use** — set `PORT` to a free port and restart `python run.py`.
- **DB looks stale/corrupted** — delete `tma.db` and restart `python run.py`; it will be recreated and re-seeded.

## Note on code style

Per project requirements, application code in this repository intentionally avoids conventional identifier naming and inline comments. The rationale and full disclosure of tooling/assistance used is documented in the final project report (not in this README).
