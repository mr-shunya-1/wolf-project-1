import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from celery import Celery

ledger = SQLAlchemy()
stash = Cache()
courier = Celery(__name__)


def _wire_courier(flask_app):
    courier.conf.update(
        broker_url=flask_app.config["CELERY_BROKER_URL"],
        result_backend=flask_app.config["CELERY_RESULT_BACKEND"],
        timezone="UTC",
        beat_schedule={
            "nudge-upcoming-rovers": {
                "task": "app.tasks.nudge_upcoming_rovers",
                "schedule": flask_app.config["REMINDER_INTERVAL_SECONDS"],
            },
            "compile-monthly-digest": {
                "task": "app.tasks.compile_monthly_digest",
                "schedule": flask_app.config["DIGEST_CHECK_INTERVAL_SECONDS"],
            },
        },
    )

    class _ContextTask(courier.Task):
        def __call__(self, *a, **kw):
            with flask_app.app_context():
                return self.run(*a, **kw)

    courier.Task = _ContextTask
    return courier


def forge_app():
    flask_app = Flask(__name__)
    flask_app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET", "change-me-please")
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("SQLITE_PATH", "sqlite:///tma.db")
    flask_app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    flask_app.config["CACHE_TYPE"] = "RedisCache"
    flask_app.config["CACHE_REDIS_URL"] = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    flask_app.config["CACHE_DEFAULT_TIMEOUT"] = 60
    flask_app.config["CELERY_BROKER_URL"] = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1")
    flask_app.config["CELERY_RESULT_BACKEND"] = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    flask_app.config["REMINDER_INTERVAL_SECONDS"] = int(os.environ.get("REMINDER_INTERVAL_SECONDS", 86400))
    flask_app.config["DIGEST_CHECK_INTERVAL_SECONDS"] = int(os.environ.get("DIGEST_CHECK_INTERVAL_SECONDS", 3600))

    ledger.init_app(flask_app)
    stash.init_app(flask_app)
    _wire_courier(flask_app)

    from app.auth import gatehouse
    from app.routes_admin import overseer_desk
    from app.routes_staff import guide_desk
    from app.routes_trekker import rover_desk

    flask_app.register_blueprint(gatehouse)
    flask_app.register_blueprint(overseer_desk)
    flask_app.register_blueprint(guide_desk)
    flask_app.register_blueprint(rover_desk)

    from flask import render_template

    @flask_app.get("/")
    @flask_app.get("/<path:_ignored>")
    def _spa_shell(_ignored=None):
        return render_template("index.html")

    with flask_app.app_context():
        ledger.create_all()
        from app.seed import plant_the_one_true_overseer
        plant_the_one_true_overseer()

    return flask_app
