import secrets
from datetime import datetime, timedelta
from app import db, login_manager
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    # 'sso' or 'local' or 'ldap' to know the origin
    auth_source = db.Column(db.String(20), default='local')
    # Flag to force password reset on first login
    password_reset_required = db.Column(db.Boolean, default=False)
    # New column to store user's page size preference
    page_size = db.Column(db.Integer, default=20)

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
        expiration_hours = current_app.config['PASSWORD_RESET_EXPIRATION_HOURS']
        self.password_reset_expiration = datetime.utcnow() + timedelta(hours=expiration_hours)
        db.session.add(self)
        return self.password_reset_token

    @staticmethod
    def verify_reset_password_token(token):
        """Verifies a token and checks if it has expired."""
        user = User.query.filter_by(password_reset_token=token).first()
        if user is None or user.password_reset_expiration < datetime.utcnow():
            return None
        return user

    def __repr__(self):
        return f'<User {self.username}>'
