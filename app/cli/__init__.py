from flask import Blueprint

bp = Blueprint("cli", __name__, cli_group=None)

from app.cli import translate  # noqa
