import functools
from flask import Blueprint, request, session, jsonify
from app import ledger
from app.models import Wayfarer, CAPACITY_ROVER, STANDING_ACTIVE

gatehouse = Blueprint("gatehouse", __name__, url_prefix="/api/auth")


def current_wayfarer():
    prowler_id = session.get("prowler_id")
    if not prowler_id:
        return None
    return Wayfarer.query.get(prowler_id)


def needs_capacity(*allowed_capacities):
    def decorator(view_fn):
        @functools.wraps(view_fn)
        def wrapped(*args, **kwargs):
            prowler = current_wayfarer()
            if not prowler:
                return jsonify(gripe="not signed in"), 401
            if prowler.is_barred():
                return jsonify(gripe="account benched"), 403
            if allowed_capacities and prowler.capacity not in allowed_capacities:
                return jsonify(gripe="not permitted for this role"), 403
            return view_fn(*args, prowler=prowler, **kwargs)

        return wrapped

    return decorator


@gatehouse.post("/register")
def self_enrol():
    payload = request.get_json(force=True, silent=True) or {}
    handle = (payload.get("handle") or "").strip()
    secret = payload.get("secret") or ""
    full_name = (payload.get("full_name") or "").strip()
    contact = (payload.get("contact") or "").strip()

    if not handle or not secret or not full_name:
        return jsonify(gripe="handle, secret and full_name are required"), 400
    if len(secret) < 6:
        return jsonify(gripe="secret must be at least 6 characters"), 400
    if Wayfarer.query.filter_by(handle=handle).first():
        return jsonify(gripe="handle already taken"), 409

    newcomer = Wayfarer(
        handle=handle,
        full_name=full_name,
        contact=contact,
        capacity=CAPACITY_ROVER,
        standing=STANDING_ACTIVE,
    )
    newcomer.set_cipher(secret)
    ledger.session.add(newcomer)
    ledger.session.commit()
    return jsonify(newcomer.to_brief()), 201


@gatehouse.post("/login")
def step_inside():
    payload = request.get_json(force=True, silent=True) or {}
    handle = (payload.get("handle") or "").strip()
    secret = payload.get("secret") or ""

    prowler = Wayfarer.query.filter_by(handle=handle).first()
    if not prowler or not prowler.cipher_matches(secret):
        return jsonify(gripe="bad handle or secret"), 401
    if prowler.is_barred():
        return jsonify(gripe="account benched"), 403

    session["prowler_id"] = prowler.id
    return jsonify(prowler.to_brief())


@gatehouse.post("/logout")
def step_outside():
    session.pop("prowler_id", None)
    return jsonify(ok=True)


@gatehouse.get("/whoami")
def whoami():
    prowler = current_wayfarer()
    if not prowler:
        return jsonify(prowler=None)
    return jsonify(prowler=prowler.to_brief())


@gatehouse.put("/profile")
@needs_capacity(CAPACITY_ROVER)
def touch_up_profile(prowler):
    payload = request.get_json(force=True, silent=True) or {}
    if "full_name" in payload and payload["full_name"].strip():
        prowler.full_name = payload["full_name"].strip()
    if "contact" in payload:
        prowler.contact = payload["contact"].strip()
    if payload.get("secret"):
        if len(payload["secret"]) < 6:
            return jsonify(gripe="secret must be at least 6 characters"), 400
        prowler.set_cipher(payload["secret"])
    ledger.session.commit()
    return jsonify(prowler.to_brief())
