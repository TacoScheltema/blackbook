import ldap3
# Only the base LDAPException is needed for connection errors.
# Operational errors are handled by checking the connection result.
from ldap3.core.exceptions import LDAPException
from flask import current_app, flash

def get_ldap_connection():
    """
    Establishes a connection to the LDAP server using settings from the app config.
    """
    try:
        use_ssl = current_app.config.get('LDAP_USE_SSL', False)
        server = ldap3.Server(
            current_app.config['LDAP_SERVER'],
            get_info=ldap3.ALL,
            use_ssl=use_ssl
        )
        # raise_exceptions is False by default, which is the correct
        # pattern for checking conn.result after an operation.
        connection = ldap3.Connection(
            server,
            user=current_app.config['LDAP_BIND_DN'],
            password=current_app.config['LDAP_BIND_PASSWORD'],
            auto_bind=True,
            read_only=False
        )
        return connection
    except LDAPException as e:
        print(f"Failed to connect to LDAP server: {e}")
        flash('Could not connect to the LDAP server.', 'danger')
        return None

def search_ldap(filter_str, attributes, size_limit=0):
    """
    Performs a search on the LDAP directory.
    Pagination is handled in the route by slicing the full result set.

    :param filter_str: The LDAP search filter string.
    :param attributes: A list of attributes to retrieve for each entry.
    :param size_limit: The maximum number of entries to return (0 for no limit).
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
            attributes=attributes,
            size_limit=size_limit
        )
        results = []
        for entry in conn.entries:
            # Convert ldap3 entry object to a more usable dictionary
            result_dict = {'dn': entry.entry_dn}
            for attr in attributes:
                # Store all values for an attribute in a list.
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

