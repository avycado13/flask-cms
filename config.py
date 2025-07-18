import secrets
import passlib
from typing import Optional


class Config:
    """
    Set Flask configuration variables.
    """

    SESSION_TYPE = "filesystem"
    SESSION_FILE_DIR = "cache"
    LANGUAGES: list[str] = ["en"]
    RQ_REDIS_URL = "redis://localhost:6379/0"
    ELASTICSEARCH_ENABLED: bool = False
    ELASTICSEARCH_URL: Optional[str] = "http://localhost:9200"
    ELASTICSEARCH_API_KEY: Optional[str] = (
        "RWhJVEpKVUJON2NUWE8zUFJ1VTQ6ZmVOTnpNLS1TS0NPYV80ZEo2OUNydw=="
    )
    POSTS_PER_PAGE: int = 10
    CLOUDSHELL_PREFIX: str = "/cloudshell"
    SECRET_KEY = secrets.token_urlsafe()
    SECURITY_PASSWORD_SALT = str(213691981621818227987771034862335535908)
    # Change for production env
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///test.db"
    DEBUG: bool = True
    # Flask Security
    # WebAuthn
    SECURITY_WEBAUTHN: bool = True
    SECURITY_WAN_ALLOW_AS_FIRST_FACTOR: bool = True
    SECURITY_WAN_ALLOW_AS_MULTI_FACTOR: bool = True
    SECURITY_WAN_ALLOW_AS_VERIFY: bool = True
    # Two Factor
    SECURITY_TWO_FACTOR: bool = True
    SECURITY_TWO_FACTOR_ENABLED_METHODS: list[str] = ["authenticator"]
    SECURITY_TOTP_SECRETS: dict[str, str] = {"1": "JBSWY3DPEHPK3PXP"}
    SECURITY_TOTP_ISSUER: str = "Flask CMS"
    SECURITY_REGISTERABLE: bool = True
    SECURITY_POST_LOGIN_VIEW = "/"
    SECURITY_SEND_REGISTER_EMAIL: bool = False
    SECURITY_USERNAME_ENABLE: bool = True
    # SECURITY_TWO_FACTOR_REQUIRED=True
    SECURITY_CSRF_IGNORE_UNAUTH_ENDPOINTS: bool = False
    TEMPLATES_AUTO_RELOAD = True
    POSTS_PER_PAGE = 3


class TestingConfig(Config):
    RQ_CONNECTION_CLASS = "fakeredis.FakeStrictRedis"
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
