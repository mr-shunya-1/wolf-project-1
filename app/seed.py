import os
from app import ledger
from app.models import Wayfarer, CAPACITY_OVERSEER


def plant_the_one_true_overseer():
    already_there = Wayfarer.query.filter_by(capacity=CAPACITY_OVERSEER).first()
    if already_there:
        return already_there

    boss = Wayfarer(
        handle=os.environ.get("BOSS_HANDLE", "overseer"),
        full_name="System Overseer",
        contact=os.environ.get("MAIL_USERNAME", "overseer@tma.local"),
        capacity=CAPACITY_OVERSEER,
    )
    boss.set_cipher(os.environ.get("BOSS_CIPHER", "change-me-please"))
    ledger.session.add(boss)
    ledger.session.commit()
    return boss
