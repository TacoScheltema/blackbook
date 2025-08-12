import base64
from flask import Flask
from flask_caching import Cache
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
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
    # Google
    if app.config['GOOGLE_CLIENT_ID'] and app.config['GOOGLE_CLIENT_SECRET']:
        oauth.register(
            name='google',
            client_id=app.config['GOOGLE_CLIENT_ID'],
            client_secret=app.config['GOOGLE_CLIENT_SECRET'],
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'}
        )

    # Keycloak
    if app.config['KEYCLOAK_CLIENT_ID'] and app.config['KEYCLOAK_SERVER_URL']:
        oauth.register(
            name='keycloak',
            client_id=app.config['KEYCLOAK_CLIENT_ID'],
            client_secret=app.config['KEYCLOAK_CLIENT_SECRET'],
            server_metadata_url=f"{app.config['KEYCLOAK_SERVER_URL']}/.well-known/openid-configuration",
            client_kwargs={'scope': 'openid email profile'}
        )

    # Authentik
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

    with app.app_context():
        db.create_all()

    return app

