import os
from flask import Flask, request, current_app,send_from_directory
from app.extensions import db, migrate, csrf, babel, security
from flask_security import (
    SQLAlchemyUserDatastore,
)
from config import Config
from app.models import User, Role, WebAuthn


def get_locale():
    return request.accept_languages.best_match(current_app.config["LANGUAGES"])


def create_app(config_class=Config):
    app = Flask(__name__)

    app.config.from_object(config_class)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    babel.init_app(app, locale_selector=get_locale)
    user_datastore = SQLAlchemyUserDatastore(db, User, Role, WebAuthn)
    security.init_app(app, user_datastore)

    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(os.path.join(app.root_path, 'static'),
                                'favicon.ico', mimetype='image/vnd.microsoft.icon')

    from app.main import bp as main_bp

    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()
    return app
