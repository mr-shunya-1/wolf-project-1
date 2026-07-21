from flask import Blueprint, request, jsonify
from app import ledger, stash
from app.auth import needs_capacity
from app.models import Expedition, Passage, CAPACITY_GUIDE, PHASE_OPEN, PHASE_CLOSED, PHASE_COMPLETED
from app.caching_keys import OPEN_TRAILS_CACHE_KEY

guide_desk = Blueprint("guide_desk", __name__, url_prefix="/api/guide")


def _own_trail_or_none(guide_id, trail_id):
    return Expedition.query.filter_by(id=trail_id, warden_id=guide_id).first()


@guide_desk.get("/trails")
@needs_capacity(CAPACITY_GUIDE)
def my_trails(prowler):
    trails = Expedition.query.filter_by(warden_id=prowler.id).all()
    out = []
    for trail in trails:
        brief = trail.to_brief()
        brief["headcount"] = Passage.query.filter_by(trail_id=trail.id).filter(Passage.phase != "Cancelled").count()
        out.append(brief)
    return jsonify(out)


@guide_desk.put("/trails/<int:trail_id>")
@needs_capacity(CAPACITY_GUIDE)
def steer_trail(prowler, trail_id):
    trail = _own_trail_or_none(prowler.id, trail_id)
    if not trail:
        return jsonify(gripe="you are not posted to this trail"), 403

    payload = request.get_json(force=True, silent=True) or {}
    if payload.get("berths_left") is not None:
        proposed = int(payload["berths_left"])
        if proposed < 0 or proposed > trail.berths_total:
            return jsonify(gripe="berths_left out of range"), 400
        trail.berths_left = proposed
    if payload.get("phase") in (PHASE_OPEN, PHASE_CLOSED):
        trail.phase = payload["phase"]

    ledger.session.commit()
    stash.delete(OPEN_TRAILS_CACHE_KEY)
    return jsonify(trail.to_brief())


@guide_desk.put("/trails/<int:trail_id>/wrap-up")
@needs_capacity(CAPACITY_GUIDE)
def wrap_up_trail(prowler, trail_id):
    trail = _own_trail_or_none(prowler.id, trail_id)
    if not trail:
        return jsonify(gripe="you are not posted to this trail"), 403

    trail.phase = PHASE_COMPLETED
    for passage in Passage.query.filter_by(trail_id=trail.id).filter(Passage.phase == "Booked").all():
        passage.phase = "Completed"
    ledger.session.commit()
    stash.delete(OPEN_TRAILS_CACHE_KEY)
    return jsonify(trail.to_brief())


@guide_desk.get("/trails/<int:trail_id>/rovers")
@needs_capacity(CAPACITY_GUIDE)
def rovers_on_trail(prowler, trail_id):
    trail = _own_trail_or_none(prowler.id, trail_id)
    if not trail:
        return jsonify(gripe="you are not posted to this trail"), 403
    passages = Passage.query.filter_by(trail_id=trail.id).filter(Passage.phase != "Cancelled").all()
    return jsonify([{"rover_name": p.rover.full_name, "contact": p.rover.contact, **p.to_brief()} for p in passages])
