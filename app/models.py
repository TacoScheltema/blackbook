# This file is part of Blackbook.
#
# Blackbook is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Blackbook is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Blackbook.  If not, see <https://www.gnu.org/licenses/>.

#
# Author: Taco Scheltema https://github.com/TacoScheltema/blackbook
#

import secrets
from datetime import datetime, timedelta, timezone

from flask import current_app
from flask_login import UserMixin
from sqlalchemy.types import DateTime, TypeDecorator
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, login_manager


@login_manager.user_loader
def load_user(id):
    return db.session.get(User, int(id))


class AwareDateTime(TypeDecorator):  # pylint: disable=too-many-ancestors
    """
    A custom SQLAlchemy type to ensure all datetimes are timezone-aware (UTC).
    Stores naive UTC datetimes in the database and returns aware UTC datetimes.
    """

    impl = DateTime
    cache_ok = True

    @property
    def python_type(self):
        """Returns the Python type expected by this column."""
        return datetime

    def process_bind_param(self, value, dialect):
        """Called when saving to the DB."""
        if value is None:
            return value
        if value.tzinfo is None:
            # Assume naive datetime is UTC
            value = value.replace(tzinfo=timezone.utc)
        # Convert to naive UTC for DB storage
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        """Called when loading from the DB."""
        if value is None:
            return value
        # Reattach UTC tzinfo
        return value.replace(tzinfo=timezone.utc)

    def process_literal_param(self, value, dialect):
        """
        Allows the type to be used in SQL expressions and default values
        in migration scripts (e.g., Alembic).
        """
        if value is None:
            return "NULL"
        # Delegate the formatting to the underlying DateTime type
        return self.impl.process_literal_param(value, dialect)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    # 'sso' or 'local' or 'ldap' to know the origin
    auth_source = db.Column(db.String(20), default="local")
    # Flag to force password reset on first login
    password_reset_required = db.Column(db.Boolean, default=False)
    # New column to store user's page size preference
    page_size = db.Column(db.Integer, default=20)
    is_admin = db.Column(db.Boolean, default=False)
    is_editor = db.Column(db.Boolean, default=False)

    # New fields for password reset tokens
    password_reset_token = db.Column(db.String(32), index=True, unique=True)
    password_reset_expiration = db.Column(AwareDateTime(), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_reset_password_token(self):
        """Generates a secure token and sets its expiration."""
        self.password_reset_token = secrets.token_urlsafe(24)
        expiration_hours = current_app.config["PASSWORD_RESET_EXPIRATION_HOURS"]
        self.password_reset_expiration = datetime.now(timezone.utc) + timedelta(hours=expiration_hours)
        db.session.add(self)
        return self.password_reset_token

    @staticmethod
    def verify_reset_password_token(token):
        """Verifies a token and checks if it has expired."""
        user = User.query.filter_by(password_reset_token=token).first()
        if user is None or user.password_reset_expiration < datetime.now(timezone.utc):
            return None
        return user

    def __repr__(self):
        return f"<User {self.username}>"
