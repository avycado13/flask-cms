from flask import Blueprint
from flask_restx import Api

bp = Blueprint("errors", __name__)
api = Api(bp)
