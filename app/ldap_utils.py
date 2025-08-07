import ldap3
## Only the base LDAPException is needed for connection errors.
## Operational errors are handled by checking the connection result.
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
        # CORRECTED: raise_exceptions is False by default, which is the correct
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

def search_ldap(filter_str, attributes, paged_size=None, paged_cookie=None):
    """
    Performs a search on the LDAP directory, with optional pagination.
    """
    conn = get_ldap_connection()
    if not conn:
        return [], None

    base_dn = current_app.config['LDAP_BASE_DN']
    results = []

    try:
        if paged_size:
            paged_search_kwargs = {
                'search_base': base_dn,
                'search_filter': filter_str,
                'attributes': attributes,
                'paged_size': paged_size
            }
            if paged_cookie:
                paged_search_kwargs['paged_cookie'] = paged_cookie

            generator = conn.extend.standard.paged_search(**paged_search_kwargs)

            for entry in generator:
                if entry['type'] == 'searchResEntry':
                    result_dict = {'dn': entry['dn']}
                    for attr in attributes:
                        if attr in entry['attributes']:
                           result_dict[attr] = entry['attributes'][attr][0] if len(entry['attributes'][attr]) == 1 else entry['attributes'][attr]
                        else:
                           result_dict[attr] = None
                    results.append(result_dict)

            next_cookie = conn.result.get('cookie')
            return results, next_cookie
        else:
            conn.search(
                search_base=base_dn,
                search_filter=filter_str,
                attributes=attributes
            )
            for entry in conn.entries:
                result_dict = {'dn': entry.entry_dn}
                for attr in attributes:
                    result_dict[attr] = entry[attr].value if entry[attr] else None
                results.append(result_dict)
            return results, None

    except LDAPException as e:
        print(f"LDAP search failed: {e}")
        flash('An error occurred while searching the directory.', 'warning')
        return [], None
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
            # Check the 'description' key in the result dictionary.
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
            # CORRECTED: Check the 'description' key for the specific error.
            if conn.result.get('description') == 'noSuchAttribute':
                # The 'message' key often contains the name of the problematic attribute.
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

