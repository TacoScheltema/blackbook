# This is the entry point for a WSGI server like Gunicorn or uWSGI.
# Example usage: gunicorn --bind 0.0.0.0:8000 wsgi:application
from app import create_app

application = create_app()

# You can also run this file directly for development:
if __name__ == "__main__":
    # Note: The reloader and debugger should be disabled in production.
    # The create_app function reads the FLASK_DEBUG environment variable.
    application.run(host='0.0.0.0')

