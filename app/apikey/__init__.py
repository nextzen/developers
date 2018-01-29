from flask import Blueprint

keys_bp = Blueprint('apikey', __name__)

from . import views
