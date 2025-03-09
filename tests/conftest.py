import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import create_app
from flask import Flask


@pytest.fixture()
def app():
    app = create_app(config_class="config.TestingConfig")
    app.config.update(
        {
            "TESTING": True,
            "SECURITY_PASSWORD_HASH": "plaintext",
            "WTF_CSRF_ENABLED": False,
            "SECURITY_EMAIL_VALIDATOR_ARGS": {"check_deliverability": False},
        }
    )

    # other setup can go here
    app.test_request_context().push()
    yield app


@pytest.fixture()
def client(app: Flask):
    with app.app_context():
        yield app.test_client()


@pytest.fixture()
def runner(app: Flask):
    return app.test_cli_runner()
