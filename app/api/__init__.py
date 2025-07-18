from flask import Blueprint
from flask_restx import Api

bp = Blueprint("api", __name__)
# api = Api(bp)

from app.api import routes
