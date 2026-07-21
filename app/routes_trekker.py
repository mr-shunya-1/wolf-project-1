from flask import Blueprint, request, jsonify
from app import ledger, stash
from app.auth import needs_capacity
from app.models import Expedition, Passage, CAPACITY_ROVER, PHASE_OPEN, PASSAGE_BOOKED, PASSAGE_CANCELLED
from app.caching_keys import OPEN_TRAILS_CACHE_KEY
from app.tasks import spin_up_history_csv

rover_desk = Blueprint("rover_desk", __name__, url_prefix="/api/rover")


@rover_desk.get("/trails")
@needs_capacity(CAPACITY_ROVER)
def browse_open_trails(prowler):
    grit = request.args.get("grit")
    turf = request.args.get("turf")
    max_span = request.args.get("max_span")

    if not grit and not turf and not max_span:
        cached = stash.get(OPEN_TRAILS_CACHE_KEY)
        if cached is not None:
            return jsonify(cached)

    query = Expedition.query.filter_by(phase=PHASE_OPEN)
    if grit:
        query = query.filter(Expedition.grit == grit)
    if turf:
        query = query.filter(Expedition.turf.ilike(f"%{turf}%"))
    if max_span:
        query = query.filter(Expedition.span_days <= int(max_span))

    briefs = [t.to_brief() for t in query.order_by(Expedition.outset.asc()).all()]

    if not grit and not turf and not max_span:
        stash.set(OPEN_TRAILS_CACHE_KEY, briefs, timeout=120)

    return jsonify(briefs)


@rover_desk.post("/trails/<int:trail_id>/book")
@needs_capacity(CAPACITY_ROVER)
def stake_a_claim(prowler, trail_id):
    trail = Expedition.query.get_or_404(trail_id)

    if trail.phase != PHASE_OPEN:
        return jsonify(gripe="trail is not open for booking"), 400
    if trail.berths_left <= 0:
        return jsonify(gripe="no berths left"), 409

    already = Passage.query.filter_by(rover_id=prowler.id, trail_id=trail.id, phase=PASSAGE_BOOKED).first()
    if already:
        return jsonify(gripe="you already have a live booking for this trail"), 409

    trail.berths_left -= 1
    passage = Passage(rover_id=prowler.id, trail_id=trail.id, phase=PASSAGE_BOOKED)
    ledger.session.add(passage)
    ledger.session.commit()
    stash.delete(OPEN_TRAILS_CACHE_KEY)
    return jsonify(passage.to_brief()), 201


@rover_desk.put("/passages/<int:passage_id>/cancel")
@needs_capacity(CAPACITY_ROVER)
def relinquish_claim(prowler, passage_id):
    passage = Passage.query.filter_by(id=passage_id, rover_id=prowler.id).first()
    if not passage:
        return jsonify(gripe="no such booking"), 404
    if passage.phase != PASSAGE_BOOKED:
        return jsonify(gripe="only a live booking can be cancelled"), 400

    passage.phase = PASSAGE_CANCELLED
    passage.trail.berths_left += 1
    ledger.session.commit()
    stash.delete(OPEN_TRAILS_CACHE_KEY)
    return jsonify(passage.to_brief())


@rover_desk.get("/passages")
@needs_capacity(CAPACITY_ROVER)
def my_history(prowler):
    passages = Passage.query.filter_by(rover_id=prowler.id).order_by(Passage.logged_at.desc()).all()
    return jsonify([p.to_brief() for p in passages])


@rover_desk.post("/export")
@needs_capacity(CAPACITY_ROVER)
def kick_off_export(prowler):
    outcome = spin_up_history_csv.delay(prowler.id)
    return jsonify(job_id=outcome.id), 202


@rover_desk.get("/export/<job_id>")
@needs_capacity(CAPACITY_ROVER)
def peek_export(prowler, job_id):
    outcome = spin_up_history_csv.AsyncResult(job_id)
    if not outcome.ready():
        return jsonify(status="pending")
    return jsonify(status="done", download=outcome.result)
