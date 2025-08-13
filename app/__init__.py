import base64
from flask import Flask, request, redirect, url_for
from flask_caching import Cache
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from authlib.integrations.flask_client import OAuth
from config import Config

# Initialize extensions
cache = Cache()
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login' # Redirect to this page if user is not logged in
oauth = OAuth()

def b64encode_filter(s):
    """Jinja2 filter to base64 encode a string."""
    if isinstance(s, str):
        s = s.encode('utf-8')
    return base64.urlsafe_b64encode(s).decode('utf-8')

def create_default_admin(app):
    with app.app_context():
        from app.models import User
        # Check if local login is enabled and if the admin user doesn't exist
        if app.config['ENABLE_LOCAL_LOGIN'] and not User.query.get(1):
            print("Creating default admin user...")
            admin_user = User(
                username='admin',
                auth_source='local',
                password_reset_required=True
            )
            admin_user.set_password('changeme')
            db.session.add(admin_user)
            db.session.commit()
            print("Default admin user created with password 'changeme'. Please login to reset.")

def create_app(config_class=Config):
    """
    The application factory. Follows Flask best practices.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions with the app
    cache.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    oauth.init_app(app)

    # --- Register OAuth Providers ---
    if app.config['GOOGLE_CLIENT_ID'] and app.config['GOOGLE_CLIENT_SECRET']:
        oauth.register(
            name='google',
            client_id=app.config['GOOGLE_CLIENT_ID'],
            client_secret=app.config['GOOGLE_CLIENT_SECRET'],
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'}
        )
    if app.config['KEYCLOAK_CLIENT_ID'] and app.config['KEYCLOAK_SERVER_URL']:
        oauth.register(
            name='keycloak',
            client_id=app.config['KEYCLOAK_CLIENT_ID'],
            client_secret=app.config['KEYCLOAK_CLIENT_SECRET'],
            server_metadata_url=f"{app.config['KEYCLOAK_SERVER_URL']}/.well-known/openid-configuration",
            client_kwargs={'scope': 'openid email profile'}
        )
    if app.config['AUTHENTIK_CLIENT_ID'] and app.config['AUTHENTIK_SERVER_URL']:
        oauth.register(
            name='authentik',
            client_id=app.config['AUTHENTIK_CLIENT_ID'],
            client_secret=app.config['AUTHENTIK_CLIENT_SECRET'],
            server_metadata_url=f"{app.config['AUTHENTIK_SERVER_URL']}/.well-known/openid-configuration",
            client_kwargs={'scope': 'openid email profile'}
        )

    # Make the config available to all templates.
    @app.context_processor
    def inject_config():
        return dict(config=app.config)

    # Register custom Jinja2 filter
    app.jinja_env.filters['b64encode'] = b64encode_filter

    # Register blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    @app.before_request
    def before_request_hook():
        # This function runs before every request.
        # If the user is logged in and needs to reset their password,
        # it redirects them to the reset page, unless they are already there.
        if current_user.is_authenticated and current_user.password_reset_required:
            if request.endpoint and request.endpoint not in ['auth.reset_password', 'auth.logout', 'static']:
                return redirect(url_for('auth.reset_password'))

    with app.app_context():
        db.create_all()
        create_default_admin(app)

    return app
