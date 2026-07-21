from app import forge_app

flask_app = forge_app()

if __name__ == "__main__":
    flask_app.run(debug=True, port=5000)
