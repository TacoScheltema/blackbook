# This is the entry point for a WSGI server like Gunicorn or uWSGI.
# Example usage: gunicorn --bind 0.0.0.0:8000 wsgi:application
from app import create_app, db
from app.models import User
import click

application = create_app()

@application.cli.command("create-admin")
def create_admin():
    """Creates the default admin user."""
    if application.config['ENABLE_LOCAL_LOGIN']:
        if User.query.get(1):
            print("Admin user already exists.")
            return

        print("Creating default admin user...")
        admin_user = User(
            username='admin',
            email='admin@example.com', # Added a default email
            auth_source='local',
            password_reset_required=True
        )
        admin_user.set_password('changeme')
        db.session.add(admin_user)
        db.session.commit()
        print("Default admin user created with password 'changeme'. Please login to reset.")
    else:
        print("Local login is disabled. Cannot create admin user.")

# You can also run this file directly for development:
if __name__ == "__main__":
    # Note: The reloader and debugger should be disabled in production.
    # The create_app function reads the FLASK_DEBUG environment variable.
    application.run(host='0.0.0.0')
