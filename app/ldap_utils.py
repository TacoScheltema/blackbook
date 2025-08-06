# app/ldap_utils.py
import ldap3
from ldap3.core.exceptions import LDAPException, LDAPInvalidDNSyntaxResult, LDAPEntryAlreadyExistsResult
from flask import current_app, flash

def get_ldap_connection():
    """
    Establishes a connection to the LDAP server using settings from the app config.
    The connection is NOT read-only to allow for add/modify operations.
    """
    try:
        use_ssl = current_app.config.get('LDAP_USE_SSL', False)
        server = ldap3.Server(
            current_app.config['LDAP_SERVER'],
            get_info=ldap3.ALL,
            use_ssl=use_ssl
        )
        connection = ldap3.Connection(
            server,
            user=current_app.config['LDAP_BIND_DN'],
            password=current_app.config['LDAP_BIND_PASSWORD'],
            auto_bind=True,
            # Changed from read_only=True to allow write operations
            read_only=False 
        )
        return connection
    except LDAPException as e:
        print(f"Failed to connect to LDAP server: {e}")
        flash('Could not connect to the LDAP server.', 'danger')
        return None

def search_ldap(filter_str, attributes):
    """
    Performs a search on the LDAP directory.

    :param filter_str: The LDAP search filter string.
    :param attributes: A list of attributes to retrieve for each entry.
    :return: A list of entry dictionaries or an empty list on error.
    """
    conn = get_ldap_connection()
    if not conn:
        return []

    base_dn = current_app.config['LDAP_BASE_DN']

    try:
        conn.search(
            search_base=base_dn,
            search_filter=filter_str,
            attributes=attributes
        )
        results = []
        for entry in conn.entries:
            result_dict = {'dn': entry.entry_dn}
            for attr in attributes:
                result_dict[attr] = entry[attr].value if entry[attr] else None
            results.append(result_dict)
        return results
    except LDAPException as e:
        print(f"LDAP search failed: {e}")
        flash('An error occurred while searching the directory.', 'warning')
        return []
    finally:
        if conn:
            conn.unbind()

def get_entry_by_dn(dn, attributes):
    """
    Retrieves a single entry by its Distinguished Name (DN).
    """
    conn = get_ldap_connection()
    if not conn:
        return None

    try:
        conn.search(
            search_base=dn,
            search_filter='(objectClass=*)',
            search_scope=ldap3.BASE,
            attributes=attributes
        )
        if conn.entries:
            entry = conn.entries[0]
            result_dict = {'dn': entry.entry_dn}
            for attr in attributes:
                result_dict[attr] = entry[attr].values if entry[attr] else []
            return result_dict
        return None
    except LDAPException as e:
        print(f"Failed to fetch entry by DN '{dn}': {e}")
        flash('Could not retrieve the specified entry.', 'warning')
        return None
    finally:
        if conn:
            conn.unbind()

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

# ---

# app/ldap_utils.py
import ldap3
from ldap3.core.exceptions import LDAPException, LDAPInvalidDnError, LDAPEntryAlreadyExistsError
from flask import current_app, flash

def get_ldap_connection():
    """
    Establishes a connection to the LDAP server using settings from the app config.
    The connection is NOT read-only to allow for add/modify operations.
    """
    try:
        use_ssl = current_app.config.get('LDAP_USE_SSL', False)
        server = ldap3.Server(
            current_app.config['LDAP_SERVER'],
            get_info=ldap3.ALL,
            use_ssl=use_ssl
        )
        connection = ldap3.Connection(
            server,
            user=current_app.config['LDAP_BIND_DN'],
            password=current_app.config['LDAP_BIND_PASSWORD'],
            auto_bind=True,
            # Changed from read_only=True to allow write operations
            read_only=False 
        )
        return connection
    except LDAPException as e:
        print(f"Failed to connect to LDAP server: {e}")
        flash('Could not connect to the LDAP server.', 'danger')
        return None

def search_ldap(filter_str, attributes):
    """
    Performs a search on the LDAP directory.

    :param filter_str: The LDAP search filter string.
    :param attributes: A list of attributes to retrieve for each entry.
    :return: A list of entry dictionaries or an empty list on error.
    """
    conn = get_ldap_connection()
    if not conn:
        return []
    
    base_dn = current_app.config['LDAP_BASE_DN']
    
    try:
        conn.search(
            search_base=base_dn,
            search_filter=filter_str,
            attributes=attributes
        )
        results = []
        for entry in conn.entries:
            result_dict = {'dn': entry.entry_dn}
            for attr in attributes:
                result_dict[attr] = entry[attr].value if entry[attr] else None
            results.append(result_dict)
        return results
    except LDAPException as e:
        print(f"LDAP search failed: {e}")
        flash('An error occurred while searching the directory.', 'warning')
        return []
    finally:
        if conn:
            conn.unbind()

def get_entry_by_dn(dn, attributes):
    """
    Retrieves a single entry by its Distinguished Name (DN).
    """
    conn = get_ldap_connection()
    if not conn:
        return None
    
    try:
        conn.search(
            search_base=dn,
            search_filter='(objectClass=*)',
            search_scope=ldap3.BASE,
            attributes=attributes
        )
        if conn.entries:
            entry = conn.entries[0]
            result_dict = {'dn': entry.entry_dn}
            for attr in attributes:
                result_dict[attr] = entry[attr].values if entry[attr] else []
            return result_dict
        return None
    except LDAPException as e:
        print(f"Failed to fetch entry by DN '{dn}': {e}")
        flash('Could not retrieve the specified entry.', 'warning')
        return None
    finally:
        if conn:
            conn.unbind()

def add_ldap_entry(dn, object_classes, attributes):
    """
    Adds a new entry to the LDAP directory.

    :param dn: The Distinguished Name (DN) for the new entry.
    :param object_classes: A list of object classes for the new entry.
    :param attributes: A dictionary of attributes for the new entry.
    :return: True if successful, False otherwise.
    """
    conn = get_ldap_connection()
    if not conn:
        return False
    
    try:
        success = conn.add(
            dn,
            object_class=object_classes,
            attributes=attributes
        )
        if not success:
            # Provide more specific feedback if the add fails
            print(f"LDAP Add Failed: {conn.result}")
            if isinstance(conn.result.get('description'), str):
                 flash(f"Could not add company: {conn.result['description']}", 'danger')
            else:
                 flash("An unknown error occurred while adding the company.", 'danger')
            return False
        return True
    except LDAPEntryAlreadyExistsResult:
        flash(f"An entry with DN '{dn}' already exists.", 'danger')
        return False
    except LDAPInvalidDNSyntaxResult:
        flash(f"The generated DN '{dn}' is invalid. Check your Base DN and company name.", 'danger')
        return False
    except LDAPException as e:
        print(f"LDAP add operation failed: {e}")
        flash('A critical error occurred during the LDAP operation.', 'danger')
        return False
    finally:
        if conn:
            conn.unbind()
