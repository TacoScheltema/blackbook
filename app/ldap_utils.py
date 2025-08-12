import ldap3
from ldap3.core.exceptions import LDAPException
from flask import current_app, flash

def get_ldap_connection(user_dn=None, password=None, read_only=False):
    """
    Establishes a connection to the LDAP server.
    Can bind with the admin user from config or a specific user for authentication.
    """
    server_uri = current_app.config.get('LDAP_SERVER')
    use_ssl = current_app.config.get('LDAP_USE_SSL', False)

    # If no user is provided, use the admin bind credentials from the config
    if user_dn is None:
        user_dn = current_app.config.get('LDAP_BIND_DN')
        password = current_app.config.get('LDAP_BIND_PASSWORD')

    try:
        server = ldap3.Server(server_uri, get_info=ldap3.ALL, use_ssl=use_ssl)
        connection = ldap3.Connection(
            server,
            user=user_dn,
            password=password,
            auto_bind=True,
            read_only=read_only
        )
        return connection
    except LDAPException as e:
        print(f"Failed to connect or bind to LDAP server: {e}")
        return None

def authenticate_ldap_user(username, password):
    """
    Attempts to bind to the LDAP server with a given username and password.
    Returns True if successful, False otherwise.
    """
    # We need to construct the user's full DN to bind.
    # This is a common pattern, but might need adjustment for your specific LDAP schema.
    # e.g., "uid=<username>,ou=people,dc=example,dc=com"
    base_dn = current_app.config.get('LDAP_BASE_DN')
    user_dn = f"cn={username},{base_dn}" # This assumes users are under the base DN with a CN. Adjust if needed.

    conn = get_ldap_connection(user_dn=user_dn, password=password)
    if conn:
        conn.unbind()
        return True
    return False

def search_ldap(filter_str, attributes, size_limit=0):
    """
    Performs a search on the LDAP directory using the admin credentials.
    """
    conn = get_ldap_connection(read_only=True)
    if not conn:
        return []

    base_dn = current_app.config['LDAP_BASE_DN']

    try:
        conn.search(
            search_base=base_dn,
            search_filter=filter_str,
            attributes=attributes,
            size_limit=size_limit
        )
        results = []
        for entry in conn.entries:
            result_dict = {'dn': entry.entry_dn}
            for attr in attributes:
                result_dict[attr] = entry[attr].values if entry[attr] else []
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
    conn = get_ldap_connection(read_only=True)
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
    Adds a new entry to the LDAP directory by checking the operation result.
    """
    conn = get_ldap_connection()
    if not conn:
        return False

    try:
        success = conn.add(dn, object_class=object_classes, attributes=attributes)
        if not success:
            print(f"LDAP Add Failed: {conn.result}")
            if conn.result.get('description') == 'entryAlreadyExists':
                flash(f"An entry with DN '{dn}' already exists.", 'danger')
            elif conn.result.get('description') == 'invalidDNSyntax':
                 flash(f"The generated DN '{dn}' is invalid. Check your Base DN and the entry name.", 'danger')
            else:
                flash(f"Could not add entry: {conn.result.get('message', 'Unknown error')}", 'danger')
            return False
        return True
    except LDAPException as e:
        print(f"LDAP add operation failed: {e}")
        flash(f'A critical error occurred during the LDAP add operation: {e}', 'danger')
        return False
    finally:
        if conn:
            conn.unbind()

def modify_ldap_entry(dn, changes):
    """
    Modifies an existing entry by checking the operation result for errors.
    """
    conn = get_ldap_connection()
    if not conn:
        return False

    try:
        success = conn.modify(dn, changes)
        if not success:
            print(f"LDAP Modify Failed: {conn.result}")
            if conn.result.get('description') == 'noSuchAttribute':
                error_details = conn.result.get('message', 'N/A')
                flash(f"Could not modify entry. The server reports a missing attribute. Details: {error_details}", 'danger')
            else:
                flash(f"Could not modify entry: {conn.result.get('message', 'Unknown error')}", 'danger')
            return False
        return True
    except LDAPException as e:
        print(f"LDAP modify operation failed: {e}")
        flash(f"A critical error occurred during the LDAP modify operation: {e}", 'danger')
        return False
    finally:
        if conn:
            conn.unbind()

