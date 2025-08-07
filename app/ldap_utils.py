import ldap3
from ldap3.core.exceptions import LDAPException, LDAPInvalidDnError, LDAPEntryAlreadyExistsError, LDAPNoSuchAttributeError
from flask import current_app, flash

def get_ldap_connection():
    """
    Establishes a connection to the LDAP server using settings from the app config.
    The connection is NOT read-only and is set to raise exceptions on errors.
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
            read_only=False,
            # This makes ldap3 raise exceptions instead of returning False
            raise_exceptions=True
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
    # This function's error handling remains as is, since search does not raise exceptions
    # in the same way as add/modify by default, even with raise_exceptions=True.
    conn = get_ldap_connection()
    if not conn:
        return [], None

    # Temporarily disable exception raising for search operations to handle them gracefully
    conn.raise_exceptions = False

    base_dn = current_app.config['LDAP_BASE_DN']
    results = []

    try:
        if paged_size:
            generator = conn.extend.standard.paged_search(
                search_base=base_dn,
                search_filter=filter_str,
                attributes=attributes,
                paged_size=paged_size,
                cookie=paged_cookie
            )
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

    # Temporarily disable exception raising for this read operation
    conn.raise_exceptions = False

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
    Adds a new entry to the LDAP directory using try/except for error handling.
    """
    conn = get_ldap_connection()
    if not conn:
        return False

    try:
        conn.add(dn, object_class=object_classes, attributes=attributes)
        return True
    except LDAPEntryAlreadyExistsError:
        flash(f"An entry with DN '{dn}' already exists.", 'danger')
        return False
    except LDAPInvalidDnError:
        flash(f"The generated DN '{dn}' is invalid. Check your Base DN and company name.", 'danger')
        return False
    except LDAPException as e:
        print(f"LDAP add operation failed: {e}")
        flash(f'A critical error occurred during the LDAP add operation: {e}', 'danger')
        return False
    finally:
        if conn:
            conn.unbind()

def modify_ldap_entry(dn, changes):
    """
    Modifies an existing entry, catching specific exceptions like noSuchAttribute.
    """
    conn = get_ldap_connection()
    if not conn:
        return False

    try:
        conn.modify(dn, changes)
        return True
    except LDAPNoSuchAttributeError as e:
        print(f"LDAP Modify Failed with NoSuchAttribute: {e}")
        flash(f"Could not modify entry: An attribute in the form does not exist on the server. Details: {e}", 'danger')
        return False
    except LDAPException as e:
        print(f"LDAP modify operation failed: {e}")
        flash(f"A critical error occurred during the LDAP modify operation: {e}", 'danger')
        return False
    finally:
        if conn:
            conn.unbind()

