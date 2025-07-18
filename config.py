import os
import secrets
from typing import Optional


class Config:
    """
    Set Flask configuration variables using environment variables with sensible defaults.
    """

    SESSION_TYPE = os.getenv("SESSION_TYPE", "filesystem")
    SESSION_FILE_DIR = os.getenv("SESSION_FILE_DIR", "cache")
    LANGUAGES: list[str] = os.getenv("LANGUAGES", "en").split(",")
    RQ_REDIS_URL = os.getenv("RQ_REDIS_URL", "redis://localhost:6379/0")
    
    ELASTICSEARCH_ENABLED: bool = os.getenv("ELASTICSEARCH_ENABLED", "false").lower() == "true"
    ELASTICSEARCH_URL: Optional[str] = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
    ELASTICSEARCH_API_KEY: Optional[str] = os.getenv("ELASTICSEARCH_API_KEY")

    POSTS_PER_PAGE: int = int(os.getenv("POSTS_PER_PAGE", 10))
    SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe())
    SECURITY_PASSWORD_SALT = os.getenv(
        "SECURITY_PASSWORD_SALT", "213691981621818227987771034862335535908"
    )
    SQLALCHEMY_DATABASE_URI: str = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///test.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = os.getenv("SQLALCHEMY_TRACK_MODIFICATIONS", "false").lower() == "true"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # Flask Security
    SECURITY_WEBAUTHN: bool = os.getenv("SECURITY_WEBAUTHN", "true").lower() == "true"
    SECURITY_WAN_ALLOW_AS_FIRST_FACTOR: bool = os.getenv("SECURITY_WAN_ALLOW_AS_FIRST_FACTOR", "true").lower() == "true"
    SECURITY_WAN_ALLOW_AS_MULTI_FACTOR: bool = os.getenv("SECURITY_WAN_ALLOW_AS_MULTI_FACTOR", "true").lower() == "true"
    SECURITY_WAN_ALLOW_AS_VERIFY: bool = os.getenv("SECURITY_WAN_ALLOW_AS_VERIFY", "true").lower() == "true"

    SECURITY_TWO_FACTOR: bool = os.getenv("SECURITY_TWO_FACTOR", "true").lower() == "true"
    SECURITY_TWO_FACTOR_ENABLED_METHODS: list[str] = os.getenv("SECURITY_TWO_FACTOR_ENABLED_METHODS", "authenticator").split(",")
    SECURITY_TOTP_SECRETS: dict[str, str] = {
        k: v for k, v in (s.split(":") for s in os.getenv("SECURITY_TOTP_SECRETS", "1:JBSWY3DPEHPK3PXP").split(","))
    }
    SECURITY_TOTP_ISSUER: str = os.getenv("SECURITY_TOTP_ISSUER", "Flask CMS")
    SECURITY_REGISTERABLE: bool = os.getenv("SECURITY_REGISTERABLE", "true").lower() == "true"
    SECURITY_POST_LOGIN_VIEW = os.getenv("SECURITY_POST_LOGIN_VIEW", "/")
    SECURITY_SEND_REGISTER_EMAIL: bool = os.getenv("SECURITY_SEND_REGISTER_EMAIL", "false").lower() == "true"
    SECURITY_USERNAME_ENABLE: bool = os.getenv("SECURITY_USERNAME_ENABLE", "true").lower() == "true"
    SECURITY_CSRF_IGNORE_UNAUTH_ENDPOINTS: bool = os.getenv("SECURITY_CSRF_IGNORE_UNAUTH_ENDPOINTS", "false").lower() == "true"

    TEMPLATES_AUTO_RELOAD = os.getenv("TEMPLATES_AUTO_RELOAD", "true").lower() == "true"


class TestingConfig(Config):
    RQ_CONNECTION_CLASS = "fakeredis.FakeStrictRedis"
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False