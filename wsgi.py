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
# This is the entry point for a WSGI server like Gunicorn or uWSGI.
# Example usage: gunicorn --bind 0.0.0.0:8000 wsgi:application
import os

import click
from flask_migrate import upgrade

from app import create_app, db
from app.models import User

application = create_app()


# --- Database Auto-Migration ---
def run_migrations():
    """
    Automatically applies database migrations on startup.
    """
    # Check if the migrations directory exists
    migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")

    if os.path.exists(migrations_dir):
        print("----------------------------------------------------------------")
        print("Checking for database migrations...")
        with application.app_context():
            try:
                # This is equivalent to running 'flask db upgrade'
                upgrade()
                print("Database schema is up to date.")
            except Exception as e:  # pylint: disable=broad-exception-caught
                print(f"Error during database migration: {e}")
                print("If this is a fresh install, ensure you have run 'flask db init' locally first.")
        print("----------------------------------------------------------------")
    else:
        print("WARNING: 'migrations' directory not found. Skipping auto-migration.")


def ensure_default_admin():
    """
    Automatically creates the default admin user on startup if:
    1. ENABLE_LOCAL_LOGIN is True
    2. The 'admin' user does not already exist.
    """
    with application.app_context():
        # 1. Check config
        if not application.config.get("ENABLE_LOCAL_LOGIN"):
            return

        # 2. Check if admin exists
        if User.query.filter_by(username="admin").first():
            return

        print("----------------------------------------------------------------")
        print("Creating default admin user...")

        # Get admin credentials from environment variables, falling back to defaults if not set
        admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
        admin_password = os.environ.get("ADMIN_INITIAL_PASS", "changeme")

        try:
            admin_user = User(
                username="admin",
                email=admin_email,
                auth_source="local",
                password_reset_required=True,
                is_admin=True,  # The default admin is always an admin
            )
            admin_user.set_password(admin_password)
            db.session.add(admin_user)
            db.session.commit()
            print("Default admin user created with the initial password provided. Please login to reset.")
        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"Error creating default admin user: {e}")

        print("----------------------------------------------------------------")


# --- Startup Sequence ---
# 1. Apply DB Migrations
run_migrations()
# 2. Ensure Admin User Exists
ensure_default_admin()


@application.cli.command("create-admin")
def create_admin():
    """Creates the default admin user (CLI Wrapper)."""
    ensure_default_admin()


@application.cli.command("grant-admin")
@click.argument("username")
def grant_admin(username):
    """Grants admin privileges to a user."""
    user = User.query.filter_by(username=username).first()
    if user:
        user.is_admin = True
        db.session.commit()
        print(f"User {username} has been granted admin privileges.")
    else:
        print(f"User {username} not found.")


# You can also run this file directly for development:
if __name__ == "__main__":
    # Note: The reloader and debugger should be disabled in production.
    # The create_app function reads the FLASK_DEBUG environment variable.
    application.run(host="0.0.0.0")
