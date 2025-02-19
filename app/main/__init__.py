from flask import Blueprint, render_template, redirect, url_for, request

bp = Blueprint("main", __name__)

from app.main import routes
