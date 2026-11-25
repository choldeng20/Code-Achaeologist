from flask import Flask


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

    from app.routes.analysis import analysis

    app.register_blueprint(analysis)
    return app
