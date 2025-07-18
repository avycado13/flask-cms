import os
from flask import Flask, request, current_app, send_from_directory
from app.extensions import (
    db,
    migrate,
    csrf,
    babel,
    security,
    moment,
    mail,
    dropzone,
    session,
)
from flask_security import (
    SQLAlchemyUserDatastore,
)
from elasticsearch import Elasticsearch
from config import Config
from app.models import User, Role, WebAuthn
import rq
from redis import Redis


def get_locale():
    override = request.args.get("lang")
    if override:
        return override
    return request.accept_languages.best_match(
        current_app.config.get("LANGUAGES", ["en"])
    )


def create_app(config_class=Config):
    app = Flask(__name__)

    app.config.from_object(config_class)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["DROPZONE_ENABLE_CSRF"] = True

    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    csrf.init_app(app)
    mail.init_app(app)
    babel.init_app(app, locale_selector=get_locale)
    moment.init_app(app)
    dropzone.init_app(app)

    user_datastore = SQLAlchemyUserDatastore(db, User, Role, WebAuthn)
    security.init_app(app, user_datastore)
    session.init_app(app)

    app.elasticsearch = (
        Elasticsearch(
            [app.config["ELASTICSEARCH_URL"]],
            api_key=app.config["ELASTICSEARCH_API_KEY"],
        )
        if app.config["ELASTICSEARCH_ENABLED"]
        else None
    )
    app.redis = Redis.from_url(app.config["RQ_REDIS_URL"])
    app.task_queue = rq.Queue("microblog-tasks", connection=app.redis)

    @app.route("/favicon.ico")
    def favicon():
        return send_from_directory(
            os.path.join(app.root_path, "static"),
            "favicon.ico",
            mimetype="image/vnd.microsoft.icon",
        )

    from app.errors import bp as errors_bp

    app.register_blueprint(errors_bp)

    from app.main import bp as main_bp

    app.register_blueprint(main_bp)

    from app.cli import bp as cli_bp

    app.register_blueprint(cli_bp)

    from app.api import bp as api_bp

    app.register_blueprint(api_bp)


    from app.dash import bp as dash_bp

    app.register_blueprint(dash_bp,url_prefix="/dash")

    with app.app_context():
        db.create_all()

    return app
