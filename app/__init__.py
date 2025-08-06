# app/__init__.py
import base64
from flask import Flask
from config import Config

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

    # Register custom Jinja2 filter for base64 encoding DNs in URLs
    app.jinja_env.filters['b64encode'] = b64encode_filter

    # Register blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    # A simple check to ensure LDAP configuration is present
    if not all([app.config['LDAP_SERVER'], app.config['LDAP_BASE_DN']]):
        @app.route('/')
        def missing_config():
            return """
            <h1>Configuration Error</h1>
            <p>LDAP_SERVER and LDAP_BASE_DN must be set in your environment variables.</p>
            <p>Please create a <code>.env</code> file based on <code>.env.example</code>.</p>
            """, 500

    return app

