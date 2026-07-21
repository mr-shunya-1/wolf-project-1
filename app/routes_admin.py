import datetime as dt
from flask import Blueprint, request, jsonify
from sqlalchemy import or_
from app import ledger, stash
from app.auth import needs_capacity
from app.models import (
    Wayfarer,
    Expedition,
    Passage,
    Deployment,
    CAPACITY_OVERSEER,
    CAPACITY_GUIDE,
    CAPACITY_ROVER,
    STANDING_ACTIVE,
    STANDING_BENCHED,
    PASSAGE_BOOKED,
)
from app.caching_keys import OPEN_TRAILS_CACHE_KEY

overseer_desk = Blueprint("overseer_desk", __name__, url_prefix="/api/overseer")


def _parse_day(raw):
    return dt.datetime.strptime(raw, "%Y-%m-%d").date()


@overseer_desk.get("/dashboard")
@needs_capacity(CAPACITY_OVERSEER)
def dashboard(prowler):
    return jsonify(
        trail_count=Expedition.query.count(),
        rover_count=Wayfarer.query.filter_by(capacity=CAPACITY_ROVER).count(),
        guide_count=Wayfarer.query.filter_by(capacity=CAPACITY_GUIDE).count(),
        passage_count=Passage.query.count(),
    )


@overseer_desk.get("/stats")
@needs_capacity(CAPACITY_OVERSEER)
def stats(prowler):
    tally_by_trail = (
        ledger.session.query(Passage.trail_id, ledger.func.count(Passage.id))
        .filter(Passage.phase != "Cancelled")
        .group_by(Passage.trail_id)
        .all()
    )
    ranked = sorted(tally_by_trail, key=lambda row: row[1], reverse=True)[:5]
    favourites = []
    for trail_id, headcount in ranked:
        trail = Expedition.query.get(trail_id)
        if trail:
            favourites.append({"title": trail.title, "headcount": headcount})
    return jsonify(favourites=favourites)


@overseer_desk.get("/trails")
@needs_capacity(CAPACITY_OVERSEER)
def list_trails(prowler):
    return jsonify([t.to_brief() for t in Expedition.query.order_by(Expedition.id.desc()).all()])


@overseer_desk.post("/trails")
@needs_capacity(CAPACITY_OVERSEER)
def carve_trail(prowler):
    payload = request.get_json(force=True, silent=True) or {}
    required = ["title", "turf", "span_days", "berths_total", "outset", "homecoming"]
    missing = [field for field in required if not payload.get(field) and payload.get(field) != 0]
    if missing:
        return jsonify(gripe=f"missing fields: {', '.join(missing)}"), 400

    trail = Expedition(
        title=payload["title"].strip(),
        turf=payload["turf"].strip(),
        grit=payload.get("grit", "Moderate"),
        span_days=int(payload["span_days"]),
        berths_total=int(payload["berths_total"]),
        berths_left=int(payload["berths_total"]),
        outset=_parse_day(payload["outset"]),
        homecoming=_parse_day(payload["homecoming"]),
    )
    ledger.session.add(trail)
    ledger.session.commit()
    stash.delete(OPEN_TRAILS_CACHE_KEY)
    return jsonify(trail.to_brief()), 201


@overseer_desk.put("/trails/<int:trail_id>")
@needs_capacity(CAPACITY_OVERSEER)
def revise_trail(prowler, trail_id):
    trail = Expedition.query.get_or_404(trail_id)
    payload = request.get_json(force=True, silent=True) or {}

    for plain_field in ("title", "turf", "grit", "phase"):
        if payload.get(plain_field):
            setattr(trail, plain_field, payload[plain_field])
    if payload.get("span_days") is not None:
        trail.span_days = int(payload["span_days"])
    if payload.get("berths_total") is not None:
        bumped_by = int(payload["berths_total"]) - trail.berths_total
        trail.berths_total = int(payload["berths_total"])
        trail.berths_left = max(0, trail.berths_left + bumped_by)
    if payload.get("outset"):
        trail.outset = _parse_day(payload["outset"])
    if payload.get("homecoming"):
        trail.homecoming = _parse_day(payload["homecoming"])

    ledger.session.commit()
    stash.delete(OPEN_TRAILS_CACHE_KEY)
    return jsonify(trail.to_brief())


@overseer_desk.delete("/trails/<int:trail_id>")
@needs_capacity(CAPACITY_OVERSEER)
def scrap_trail(prowler, trail_id):
    trail = Expedition.query.get_or_404(trail_id)
    ledger.session.delete(trail)
    ledger.session.commit()
    stash.delete(OPEN_TRAILS_CACHE_KEY)
    return jsonify(ok=True)


@overseer_desk.post("/trails/<int:trail_id>/assign")
@needs_capacity(CAPACITY_OVERSEER)
def post_a_guide(prowler, trail_id):
    trail = Expedition.query.get_or_404(trail_id)
    payload = request.get_json(force=True, silent=True) or {}
    guide_id = payload.get("guide_id")
    guide = Wayfarer.query.filter_by(id=guide_id, capacity=CAPACITY_GUIDE).first()
    if not guide:
        return jsonify(gripe="no such guide"), 404

    trail.warden_id = guide.id
    ledger.session.add(Deployment(guide_id=guide.id, trail_id=trail.id, poster_id=prowler.id))
    ledger.session.commit()
    stash.delete(OPEN_TRAILS_CACHE_KEY)
    return jsonify(trail.to_brief())


@overseer_desk.get("/guides")
@needs_capacity(CAPACITY_OVERSEER)
def list_guides(prowler):
    return jsonify([g.to_brief() for g in Wayfarer.query.filter_by(capacity=CAPACITY_GUIDE).all()])


@overseer_desk.post("/guides")
@needs_capacity(CAPACITY_OVERSEER)
def recruit_guide(prowler):
    payload = request.get_json(force=True, silent=True) or {}
    handle = (payload.get("handle") or "").strip()
    secret = payload.get("secret") or ""
    full_name = (payload.get("full_name") or "").strip()

    if not handle or not secret or not full_name:
        return jsonify(gripe="handle, secret and full_name are required"), 400
    if Wayfarer.query.filter_by(handle=handle).first():
        return jsonify(gripe="handle already taken"), 409

    guide = Wayfarer(
        handle=handle,
        full_name=full_name,
        contact=(payload.get("contact") or "").strip(),
        capacity=CAPACITY_GUIDE,
        standing=STANDING_ACTIVE,
    )
    guide.set_cipher(secret)
    ledger.session.add(guide)
    ledger.session.commit()
    return jsonify(guide.to_brief()), 201


@overseer_desk.get("/wayfarers")
@needs_capacity(CAPACITY_OVERSEER)
def list_wayfarers(prowler):
    return jsonify([w.to_brief() for w in Wayfarer.query.filter(Wayfarer.capacity != CAPACITY_OVERSEER).all()])


@overseer_desk.put("/wayfarers/<int:wayfarer_id>/standing")
@needs_capacity(CAPACITY_OVERSEER)
def toggle_standing(prowler, wayfarer_id):
    target = Wayfarer.query.get_or_404(wayfarer_id)
    if target.capacity == CAPACITY_OVERSEER:
        return jsonify(gripe="cannot bench the overseer"), 400
    payload = request.get_json(force=True, silent=True) or {}
    wanted = payload.get("standing")
    if wanted not in (STANDING_ACTIVE, STANDING_BENCHED):
        return jsonify(gripe="standing must be active or benched"), 400
    target.standing = wanted
    ledger.session.commit()
    return jsonify(target.to_brief())


@overseer_desk.get("/search")
@needs_capacity(CAPACITY_OVERSEER)
def rummage(prowler):
    needle = f"%{request.args.get('q', '').strip()}%"
    kind = request.args.get("kind", "trails")

    if kind == "trails":
        hits = Expedition.query.filter(or_(Expedition.title.ilike(needle), Expedition.turf.ilike(needle))).all()
        return jsonify([h.to_brief() for h in hits])

    hits = Wayfarer.query.filter(
        Wayfarer.capacity != CAPACITY_OVERSEER,
        or_(Wayfarer.handle.ilike(needle), Wayfarer.full_name.ilike(needle)),
    ).all()
    return jsonify([h.to_brief() for h in hits])


@overseer_desk.get("/passages")
@needs_capacity(CAPACITY_OVERSEER)
def all_passages(prowler):
    return jsonify([p.to_brief() for p in Passage.query.order_by(Passage.id.desc()).all()])
