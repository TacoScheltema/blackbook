# This is the entry point for a WSGI server like Gunicorn or uWSGI.
# Example usage: gunicorn --bind 0.0.0.0:8000 wsgi:application
import click

from app import create_app, db
from app.models import User

application = create_app()


@application.cli.command("create-admin")
def create_admin():
    """Creates the default admin user."""
    if application.config["ENABLE_LOCAL_LOGIN"]:
        if User.query.filter_by(username="admin").first():
            print("Admin user already exists.")
            return

        print("Creating default admin user...")
        admin_user = User(
            username="admin",
            email="admin@example.com",
            auth_source="local",
            password_reset_required=True,
            is_admin=True,  # The default admin is always an admin
        )
        admin_user.set_password("changeme")
        db.session.add(admin_user)
        db.session.commit()
        print("Default admin user created with password 'changeme'. Please login to reset.")
    else:
        print("Local login is disabled. Cannot create admin user.")


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
