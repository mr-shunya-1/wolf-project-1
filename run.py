import os
from app import forge_app

flask_app = forge_app()

if __name__ == "__main__":
    flask_app.run(debug=True, port=int(os.environ.get("PORT", 5001)))
