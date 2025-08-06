import ldap3
from ldap3.core.exceptions import LDAPException, LDAPInvalidDNSyntaxResult, LDAPEntryAlreadyExistsResult, LDAPInvalidFilterError, LDAPOperationsErrorResult
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
            read_only=False 
        )
        return connection
    except LDAPException as e:
        print(f"Failed to connect to LDAP server: {e}")
        flash('Could not connect to the LDAP server.', 'danger')
        return None

def search_ldap(filter_str, attributes, paged_size=20, paged_cookie=None):
    """
    Performs a paged search on the LDAP directory.

    :param filter_str: The LDAP search filter string.
    :param attributes: A list of attributes to retrieve for each entry.
    :param paged_size: The number of results per page.
    :param paged_cookie: The cookie from the previous paged search.
    :return: A tuple containing (list of results, next page cookie).
    """
    conn = get_ldap_connection()
    if not conn:
        return [], None
    
    base_dn = current_app.config['LDAP_BASE_DN']
    
    try:
        # The conn.search method returns a boolean.
        # The results and cookie are retrieved from the connection object afterward.
        search_was_sent = conn.search(
            search_base=base_dn,
            search_filter=filter_str,
            attributes=attributes,
            paged_size=paged_size,
            paged_cookie=paged_cookie
        )

        if not search_was_sent:
            print(f"LDAP Search returned False. Result: {conn.result}")
            flash('The search could not be performed.', 'warning')
            return [], None

        results = []
        for entry in conn.entries:
            result_dict = {'dn': entry.entry_dn}
            # Use entry_raw_attributes for consistency and to avoid decoding issues here
            raw_attrs = entry.entry_raw_attributes
            for attr in attributes:
                # Get the first value if it exists, decode from bytes, otherwise None
                raw_values = raw_attrs.get(attr, [])
                result_dict[attr] = raw_values[0].decode('utf-8', 'ignore') if raw_values else None
            results.append(result_dict)
        
        # Correctly retrieve the cookie for the next page from the paged results control
        paged_control = conn.result['controls'].get('1.2.840.113556.1.4.319', {})
        next_cookie = paged_control.get('value', {}).get('cookie')

        return results, next_cookie
        
    except (LDAPInvalidFilterError, LDAPOperationsErrorResult) as e:
        print(f"LDAP search failed due to invalid filter or operation: {e}")
        flash('An error occurred while searching the directory. Check LDAP filter syntax.', 'warning')
        return [], None
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
            print(f"LDAP Add Failed: {conn.result}")
            if isinstance(conn.result.get('description'), str):
                 flash(f"Could not add entry: {conn.result['description']}", 'danger')
            else:
                 flash("An unknown error occurred while adding the entry.", 'danger')
            return False
        return True
    except LDAPEntryAlreadyExistsResult:
        flash(f"An entry with DN '{dn}' already exists.", 'danger')
        return False
    except LDAPInvalidDNSyntaxResult:
        flash(f"The generated DN '{dn}' is invalid. Check your Base DN and entry name.", 'danger')
        return False
    except LDAPException as e:
        print(f"LDAP add operation failed: {e}")
        flash('A critical error occurred during the LDAP operation.', 'danger')
        return False
    finally:
        if conn:
            conn.unbind()

def modify_ldap_entry(dn, changes):
    """
    Modifies an existing entry in the LDAP directory.

    :param dn: The Distinguished Name (DN) of the entry to modify.
    :param changes: A dictionary of changes.
                    Format: {'attribute_name': [(MODIFY_TYPE, [values])]}
                    Example: {'mail': [(ldap3.MODIFY_REPLACE, ['new@example.com'])]}
    :return: True if successful, False otherwise.
    """
    conn = get_ldap_connection()
    if not conn:
        return False
        
    try:
        success = conn.modify(dn, changes)
        if not success:
            print(f"LDAP Modify Failed: {conn.result}")
            if isinstance(conn.result.get('description'), str):
                flash(f"Could not modify entry: {conn.result['description']}", 'danger')
            else:
                flash("An unknown error occurred while modifying the entry.", 'danger')
            return False
        return True
    except LDAPException as e:
        print(f"LDAP modify operation failed: {e}")
        flash('A critical error occurred during the LDAP modify operation.', 'danger')
        return False
    finally:
        if conn:
            conn.unbind()

