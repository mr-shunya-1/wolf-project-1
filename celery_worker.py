from app import forge_app, courier
import app.tasks  # noqa: F401  registers the celery tasks

flask_app = forge_app()
flask_app.app_context().push()

celery = courier
