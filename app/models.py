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
import secrets
from datetime import datetime, timedelta, timezone

from flask import current_app
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, login_manager


@login_manager.user_loader
def load_user(id):
    return db.session.get(User, int(id))


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
    password_reset_expiration = db.Column(db.DateTime)

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
