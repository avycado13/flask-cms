from flask import Blueprint


bp = Blueprint("dashboard", __name__)

from app.dash import routes
