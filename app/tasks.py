import csv
import io
import os
import json
import smtplib
import datetime as dt
import urllib.request
from email.mime.text import MIMEText

from app import courier, ledger
from app.models import Expedition, Passage, Wayfarer, CAPACITY_OVERSEER, CAPACITY_ROVER, PHASE_OPEN

EXPORT_DROPBOX = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "static", "exports")


def _mail_out(recipient, subject, html_body):
    server_addr = os.environ.get("MAIL_SERVER")
    sender = os.environ.get("MAIL_USERNAME")
    passcode = os.environ.get("MAIL_PASSWORD")
    if not server_addr or not sender or not passcode:
        print(f"[mail suppressed, no MAIL_* config] -> {recipient}: {subject}")
        return

    letter = MIMEText(html_body, "html")
    letter["Subject"] = subject
    letter["From"] = sender
    letter["To"] = recipient

    with smtplib.SMTP(server_addr, int(os.environ.get("MAIL_PORT", 587))) as pipe:
        pipe.starttls()
        pipe.login(sender, passcode)
        pipe.sendmail(sender, [recipient], letter.as_string())


def _ping_gchat(text):
    hook = os.environ.get("GCHAT_WEBHOOK_URL")
    if not hook:
        print(f"[gchat suppressed, no GCHAT_WEBHOOK_URL] -> {text}")
        return
    body = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(hook, data=body, headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=10)


@courier.task(name="app.tasks.nudge_upcoming_rovers")
def nudge_upcoming_rovers():
    horizon = dt.date.today() + dt.timedelta(days=1)
    soon_trails = Expedition.query.filter(Expedition.outset == horizon).all()

    nudged = 0
    for trail in soon_trails:
        live_passages = Passage.query.filter_by(trail_id=trail.id, phase="Booked").all()
        for passage in live_passages:
            rover = passage.rover
            message = (
                f"Heads up {rover.full_name} — {trail.title} in {trail.turf} kicks off tomorrow "
                f"({trail.outset}), runs {trail.span_days} day(s). Pack accordingly."
            )
            _ping_gchat(message)
            if rover.contact and "@" in rover.contact:
                _mail_out(rover.contact, f"Reminder: {trail.title} starts tomorrow", f"<p>{message}</p>")
            nudged += 1
    return {"nudged": nudged}


@courier.task(name="app.tasks.compile_monthly_digest")
def compile_monthly_digest():
    today = dt.date.today()
    if today.day != 1:
        return {"skipped": True}

    window_start = (today - dt.timedelta(days=1)).replace(day=1)
    window_end = today - dt.timedelta(days=1)

    finished = Expedition.query.filter(
        Expedition.phase == "Completed", Expedition.homecoming >= window_start, Expedition.homecoming <= window_end
    ).all()
    headcount_total = sum(
        Passage.query.filter_by(trail_id=t.id).filter(Passage.phase != "Cancelled").count() for t in finished
    )
    ranked = sorted(
        finished,
        key=lambda t: Passage.query.filter_by(trail_id=t.id).filter(Passage.phase != "Cancelled").count(),
        reverse=True,
    )[:3]

    rows = "".join(f"<li>{t.title} ({t.turf})</li>" for t in ranked)
    digest_html = f"""
    <h2>Monthly Trekking Digest — {window_start.strftime('%B %Y')}</h2>
    <p>Treks concluded: {len(finished)}</p>
    <p>Total participants: {headcount_total}</p>
    <p>Most popular treks:</p>
    <ul>{rows}</ul>
    """

    boss = Wayfarer.query.filter_by(capacity=CAPACITY_OVERSEER).first()
    if boss and boss.contact:
        _mail_out(boss.contact, f"TMA monthly digest — {window_start.strftime('%B %Y')}", digest_html)
    return {"finished": len(finished), "headcount_total": headcount_total}


@courier.task(name="app.tasks.spin_up_history_csv")
def spin_up_history_csv(rover_id):
    rover = Wayfarer.query.get(rover_id)
    if not rover:
        return None

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["User ID", "Trek Name", "Location", "Booking Status", "Booking Date", "Trek Start", "Trek End"])
    for passage in Passage.query.filter_by(rover_id=rover.id).all():
        writer.writerow(
            [
                rover.id,
                passage.trail.title,
                passage.trail.turf,
                passage.phase,
                passage.logged_at.date().isoformat() if passage.logged_at else "",
                passage.trail.outset.isoformat() if passage.trail.outset else "",
                passage.trail.homecoming.isoformat() if passage.trail.homecoming else "",
            ]
        )

    os.makedirs(EXPORT_DROPBOX, exist_ok=True)
    file_name = f"trek-history-{rover.id}-{int(dt.datetime.utcnow().timestamp())}.csv"
    disk_path = os.path.join(EXPORT_DROPBOX, file_name)
    with open(disk_path, "w", newline="") as fh:
        fh.write(buffer.getvalue())

    _ping_gchat(f"CSV export ready for {rover.full_name}: {file_name}")
    return f"/static/exports/{file_name}"
