import atexit
import base64

from apscheduler.schedulers.background import BackgroundScheduler
from authlib.integrations.flask_client import OAuth
from flask import Flask, redirect, request, url_for
from flask_caching import Cache
from flask_login import LoginManager, current_user
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from config import Config

# Initialize extensions
cache = Cache()
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
oauth = OAuth()
scheduler = BackgroundScheduler()
mail = Mail()


def b64encode_filter(s):
    """Jinja2 filter to base64 encode a string."""
    if isinstance(s, str):
        s = s.encode("utf-8")
    return base64.urlsafe_b64encode(s).decode("utf-8")


def create_app(config_class=Config):
    """
    The application factory. Follows Flask best practices.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions with the app
    cache.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    oauth.init_app(app)
    mail.init_app(app)

    # --- Register OAuth Providers ---
    if app.config["GOOGLE_CLIENT_ID"] and app.config["GOOGLE_CLIENT_SECRET"]:
        oauth.register(
            name="google",
            client_id=app.config["GOOGLE_CLIENT_ID"],
            client_secret=app.config["GOOGLE_CLIENT_SECRET"],
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile groups"},
        )
    if app.config["KEYCLOAK_CLIENT_ID"] and app.config["KEYCLOAK_SERVER_URL"]:
        oauth.register(
            name="keycloak",
            client_id=app.config["KEYCLOAK_CLIENT_ID"],
            client_secret=app.config["KEYCLOAK_CLIENT_SECRET"],
            server_metadata_url=f"{app.config['KEYCLOAK_SERVER_URL']}/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile groups"},
        )
    if app.config["AUTHENTIK_CLIENT_ID"] and app.config["AUTHENTIK_SERVER_URL"]:
        oauth.register(
            name="authentik",
            client_id=app.config["AUTHENTIK_CLIENT_ID"],
            client_secret=app.config["AUTHENTIK_CLIENT_SECRET"],
            server_metadata_url=f"{app.config['AUTHENTIK_SERVER_URL']}/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile groups"},
        )

    # Make the config available to all templates.
    @app.context_processor
    def inject_config():
        return dict(config=app.config)

    # Register custom Jinja2 filter
    app.jinja_env.filters["b64encode"] = b64encode_filter

    # Register blueprints
    from app.main import bp as main_bp

    app.register_blueprint(main_bp)
    from app.auth import bp as auth_bp

    app.register_blueprint(auth_bp)

    @app.before_request
    def before_request_hook():
        if current_user.is_authenticated and current_user.password_reset_required:
            if request.endpoint and request.endpoint not in ["auth.reset_password", "auth.logout", "static"]:
                return redirect(url_for("auth.reset_password"))

    # --- Start Background Scheduler ---
    from app.jobs import refresh_ldap_cache

    # Run the job once on startup to ensure cache is populated immediately
    with app.app_context():
        refresh_ldap_cache(app)

    scheduler.add_job(
        func=refresh_ldap_cache, args=[app], trigger="interval", seconds=app.config["CACHE_REFRESH_INTERVAL"]
    )
    scheduler.start()
    # Ensure the scheduler is shut down when the app exits
    atexit.register(lambda: scheduler.shutdown())

    return app
