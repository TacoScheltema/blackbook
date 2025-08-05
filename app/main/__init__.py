# app/main/__init__.py
from flask import Blueprint

# A Blueprint is a way to organize a group of related views and other code.
bp = Blueprint('main', __name__)

# Import the routes module to link the views to the blueprint.
# This is imported at the bottom to avoid circular dependencies.
from app.main import routes
