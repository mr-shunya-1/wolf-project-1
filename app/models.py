import datetime as dt
from werkzeug.security import generate_password_hash, check_password_hash
from app import ledger

CAPACITY_OVERSEER = "overseer"
CAPACITY_GUIDE = "guide"
CAPACITY_ROVER = "rover"

STANDING_ACTIVE = "active"
STANDING_BENCHED = "benched"

GRIT_EASY = "Easy"
GRIT_MODERATE = "Moderate"
GRIT_HARD = "Hard"

PHASE_PENDING = "Pending"
PHASE_APPROVED = "Approved"
PHASE_OPEN = "Open"
PHASE_CLOSED = "Closed"
PHASE_COMPLETED = "Completed"

PASSAGE_BOOKED = "Booked"
PASSAGE_CANCELLED = "Cancelled"
PASSAGE_COMPLETED = "Completed"

TOLL_UNPAID = "Unpaid"
TOLL_PAID = "Paid"


class Wayfarer(ledger.Model):
    __tablename__ = "wayfarer"

    id = ledger.Column(ledger.Integer, primary_key=True)
    handle = ledger.Column(ledger.String(64), unique=True, nullable=False)
    cipher = ledger.Column(ledger.String(256), nullable=False)
    full_name = ledger.Column(ledger.String(120), nullable=False)
    contact = ledger.Column(ledger.String(120), nullable=True)
    capacity = ledger.Column(ledger.String(16), nullable=False, default=CAPACITY_ROVER)
    standing = ledger.Column(ledger.String(16), nullable=False, default=STANDING_ACTIVE)
    joined_at = ledger.Column(ledger.DateTime, default=dt.datetime.utcnow)

    warded_trails = ledger.relationship(
        "Expedition", back_populates="warden", foreign_keys="Expedition.warden_id"
    )
    passages = ledger.relationship(
        "Passage", back_populates="rover", foreign_keys="Passage.rover_id"
    )

    def set_cipher(self, raw_secret):
        self.cipher = generate_password_hash(raw_secret)

    def cipher_matches(self, raw_secret):
        return check_password_hash(self.cipher, raw_secret)

    def is_barred(self):
        return self.standing == STANDING_BENCHED

    def to_brief(self):
        return {
            "id": self.id,
            "handle": self.handle,
            "full_name": self.full_name,
            "contact": self.contact,
            "capacity": self.capacity,
            "standing": self.standing,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
        }


class Expedition(ledger.Model):
    __tablename__ = "expedition"

    id = ledger.Column(ledger.Integer, primary_key=True)
    title = ledger.Column(ledger.String(120), nullable=False)
    turf = ledger.Column(ledger.String(120), nullable=False)
    grit = ledger.Column(ledger.String(16), nullable=False, default=GRIT_MODERATE)
    span_days = ledger.Column(ledger.Integer, nullable=False)
    berths_total = ledger.Column(ledger.Integer, nullable=False)
    berths_left = ledger.Column(ledger.Integer, nullable=False)
    warden_id = ledger.Column(ledger.Integer, ledger.ForeignKey("wayfarer.id"), nullable=True)
    phase = ledger.Column(ledger.String(16), nullable=False, default=PHASE_PENDING)
    outset = ledger.Column(ledger.Date, nullable=False)
    homecoming = ledger.Column(ledger.Date, nullable=False)
    forged_at = ledger.Column(ledger.DateTime, default=dt.datetime.utcnow)

    warden = ledger.relationship("Wayfarer", back_populates="warded_trails", foreign_keys=[warden_id])
    passages = ledger.relationship("Passage", back_populates="trail", foreign_keys="Passage.trail_id")
    postings = ledger.relationship("Deployment", back_populates="trail", foreign_keys="Deployment.trail_id")

    def to_brief(self):
        return {
            "id": self.id,
            "title": self.title,
            "turf": self.turf,
            "grit": self.grit,
            "span_days": self.span_days,
            "berths_total": self.berths_total,
            "berths_left": self.berths_left,
            "warden_id": self.warden_id,
            "warden_name": self.warden.full_name if self.warden else None,
            "phase": self.phase,
            "outset": self.outset.isoformat() if self.outset else None,
            "homecoming": self.homecoming.isoformat() if self.homecoming else None,
        }


class Passage(ledger.Model):
    __tablename__ = "passage"
    __table_args__ = (
        ledger.UniqueConstraint("rover_id", "trail_id", "phase", name="one_live_passage_per_rover_trail"),
    )

    id = ledger.Column(ledger.Integer, primary_key=True)
    rover_id = ledger.Column(ledger.Integer, ledger.ForeignKey("wayfarer.id"), nullable=False)
    trail_id = ledger.Column(ledger.Integer, ledger.ForeignKey("expedition.id"), nullable=False)
    logged_at = ledger.Column(ledger.DateTime, default=dt.datetime.utcnow)
    phase = ledger.Column(ledger.String(16), nullable=False, default=PASSAGE_BOOKED)
    toll_state = ledger.Column(ledger.String(16), nullable=False, default=TOLL_UNPAID)

    rover = ledger.relationship("Wayfarer", back_populates="passages", foreign_keys=[rover_id])
    trail = ledger.relationship("Expedition", back_populates="passages", foreign_keys=[trail_id])

    def to_brief(self):
        return {
            "id": self.id,
            "rover_id": self.rover_id,
            "trail_id": self.trail_id,
            "trail_title": self.trail.title if self.trail else None,
            "turf": self.trail.turf if self.trail else None,
            "logged_at": self.logged_at.isoformat() if self.logged_at else None,
            "phase": self.phase,
            "toll_state": self.toll_state,
        }


class Deployment(ledger.Model):
    __tablename__ = "deployment"

    id = ledger.Column(ledger.Integer, primary_key=True)
    guide_id = ledger.Column(ledger.Integer, ledger.ForeignKey("wayfarer.id"), nullable=False)
    trail_id = ledger.Column(ledger.Integer, ledger.ForeignKey("expedition.id"), nullable=False)
    poster_id = ledger.Column(ledger.Integer, ledger.ForeignKey("wayfarer.id"), nullable=False)
    posted_at = ledger.Column(ledger.DateTime, default=dt.datetime.utcnow)

    guide = ledger.relationship("Wayfarer", foreign_keys=[guide_id])
    trail = ledger.relationship("Expedition", back_populates="postings", foreign_keys=[trail_id])
    poster = ledger.relationship("Wayfarer", foreign_keys=[poster_id])
