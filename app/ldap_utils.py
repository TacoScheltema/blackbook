
# app/ldap_utils.py
import ldap3
from ldap3.core.exceptions import LDAPException
from flask import current_app

def get_ldap_connection():
    """
    Establishes a connection to the LDAP server using settings from the app config.
    """
    try:
        server = ldap3.Server(current_app.config['LDAP_SERVER'], get_info=ldap3.ALL)
        connection = ldap3.Connection(
            server,
            user=current_app.config['LDAP_BIND_DN'],
            password=current_app.config['LDAP_BIND_PASSWORD'],
            auto_bind=True,
            read_only=True
        )
        return connection
    except LDAPException as e:
        print(f"Failed to connect to LDAP server: {e}")
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
            # Convert ldap3 entry object to a more usable dictionary
            result_dict = {'dn': entry.entry_dn}
            for attr in attributes:
                # ldap3 returns values as a list, get the first one or None
                result_dict[attr] = entry[attr].value if entry[attr] else None
            results.append(result_dict)
        return results
    except LDAPException as e:
        print(f"LDAP search failed: {e}")
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
            search_filter='(objectClass=*)', # Match any object at this DN
            search_scope=ldap3.BASE,
            attributes=attributes
        )
        if conn.entries:
            entry = conn.entries[0]
            result_dict = {'dn': entry.entry_dn}
            for attr in attributes:
                # For single entry, we might want all values of an attribute
                result_dict[attr] = entry[attr].values if entry[attr] else []
            return result_dict
        return None
    except LDAPException as e:
        print(f"Failed to fetch entry by DN '{dn}': {e}")
        return None
    finally:
        if conn:
            conn.unbind()
