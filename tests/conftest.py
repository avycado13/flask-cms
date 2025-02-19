import pytest
from app import create_app

@pytest.fixture()
def app():
    app = create_app(config_class="config.TestingConfig")
    app.config.update({
        "TESTING": True,
        "SECURITY_PASSWORD_HASH":"plaintext",
        "WTF_CSRF_ENABLED": False,
        "SECURITY_EMAIL_VALIDATOR_ARGS": {"check_deliverability": False},
    })

    # other setup can go here

    yield app

    # clean up / reset resources here


@pytest.fixture()
def client(app):
    with app.app_context():
        yield app.test_client()
        yield app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()