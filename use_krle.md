# How to Use — Trekking Management Application

## 1. Run it locally

You need three terminals open at the same time, all `cd`'d into `wolf-project-1` with the virtualenv activated.

```bash
# one-time setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

**Terminal 1 — Redis**
```bash
redis-server
```

**Terminal 2 — Celery worker + beat** (daily reminders, monthly report, CSV export)
```bash
source .venv/bin/activate
celery -A celery_worker.celery worker --beat --loglevel=info
```

**Terminal 3 — Flask app**
```bash
source .venv/bin/activate
python run.py
```

Open **http://127.0.0.1:5001** in your browser.

> macOS: don't use port 5000 — AirPlay Receiver squats on it and you'll get a misleading 403 page instead of the app. `run.py` defaults to 5001 already; override with `PORT=xxxx python run.py` if 5001 is also busy.

## 2. Filling the database — there is nothing to "fill" manually

The database is created empty on first launch (`tma.db`, SQLite) — no seed script populates sample treks or users beyond the one Admin account. Everything else you put in yourself through the UI, in this order:

1. **Log in as Admin** (credentials below).
2. **Admin → Guides tab** → recruit at least one Trek Staff account (handle + secret you choose).
3. **Admin → Trails tab** → carve a trek (title, location, difficulty, days, slots, start/end dates), then assign the guide you just created and set its phase to **Open**.
4. **Register a Trekker account** from the sign-in screen ("New trekker? Register here") — this is the only self-service registration; Admin and Staff accounts are never self-registered.
5. As that Trekker, book the now-Open trek from the **Browse** tab.

That's the whole loop — repeat step 2–5 to add more staff, treks, and bookings. If you want to reset everything, stop the app and delete `tma.db`; it's recreated (and the Admin re-seeded) on the next `python run.py`.

## 3. Login credentials

| Role | Handle | Secret | Where it comes from |
|---|---|---|---|
| **Admin** | `overseer` (or whatever `BOSS_HANDLE` is set to in `.env`) | `overseerpass` (or whatever `BOSS_CIPHER` is set to in `.env`) | Seeded automatically on first run — **this is the only account that pre-exists** |
| Trek Staff | whatever handle you pick when Admin recruits them | whatever secret you pick at that time | Created by Admin from the Guides tab |
| Trekker | whatever handle you pick when registering | whatever secret you pick (min. 6 characters) | Self-registered from the sign-in screen |

If you haven't touched `.env`, the defaults from `.env.example` are `BOSS_HANDLE=overseer` / `BOSS_CIPHER=change-me-please` — set your own in `.env` before first launch if you want something else, since the Admin account is only created once (deleting `tma.db` and restarting re-seeds it from whatever `.env` says at that time).

## 4. Using the Admin portal

After logging in as Admin you land on a tabbed dashboard:

- **Overview** — total treks, trekkers, staff, and bookings, plus a bar chart of the most-booked treks.
- **Trails** — create new treks (title, location, difficulty, duration, slots, start/end date); change a trek's phase (`Pending` / `Approved` / `Open` / `Closed` / `Completed`) from the dropdown; assign a guide to a trek from its own dropdown. A trek only becomes bookable by trekkers once its phase is **Open**.
- **Guides** — recruit new Trek Staff (handle, name, contact, secret); bench or reinstate a guide's account (a benched account can't log in).
- **People** — every non-admin account (staff and trekkers); bench/reinstate any of them the same way as Guides.
- **Bookings** — every booking in the system across all trekkers and treks, with phase and payment state.
- **Search** — look up trails or people by name/location/handle.

Anything you do here — carving a trek, assigning a guide, benching an account — takes effect immediately for the affected staff/trekker on their next page load; trek listings a trekker sees are cached for up to 2 minutes but are invalidated instantly on any trek mutation, so you won't see stale data after making a change yourself.
