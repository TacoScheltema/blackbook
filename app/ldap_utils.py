import base64
import hashlib
import os

import ldap3
from flask import current_app, flash
from ldap3.core.exceptions import LDAPException


def hash_password_ssha(password):
    """Hashes a password using the SSHA (Salted SHA-1) scheme."""
    salt = os.urandom(4)
    h = hashlib.sha1(password.encode("utf-8"))
    h.update(salt)
    hashed_password = h.digest() + salt
    return b"{SSHA}" + base64.b64encode(hashed_password)


def get_ldap_connection(user_dn=None, password=None, read_only=False):
    """
    Establishes a connection to the LDAP server.
    Can bind with the admin user from config or a specific user for authentication.
    """
    server_uri = current_app.config.get("LDAP_SERVER")
    use_ssl = current_app.config.get("LDAP_USE_SSL", False)

    if user_dn is None:
        user_dn = current_app.config.get("LDAP_BIND_DN")
        password = current_app.config.get("LDAP_BIND_PASSWORD")

    try:
        server = ldap3.Server(server_uri, get_info=ldap3.ALL, use_ssl=use_ssl)
        connection = ldap3.Connection(
            server, user=user_dn, password=password, auto_bind=True, read_only=read_only
        )
        return connection
    except LDAPException as e:
        print(f"Failed to connect or bind to LDAP server: {e}")
        return None


def authenticate_ldap_user(username, password):
    """
    Attempts to bind to the LDAP server with a given username and password.
    Returns a tuple of (is_authenticated, is_admin, is_editor).
    """
    user_dn_template = current_app.config.get("LDAP_USER_DN_TEMPLATE")
    admin_group_dn = current_app.config.get("LDAP_ADMIN_GROUP_DN")
    editor_group_dn = current_app.config.get("LDAP_EDITOR_GROUP_DN")

    if not user_dn_template:
        flash("LDAP user DN template is not configured.", "danger")
        return False, False, False

    user_dn = user_dn_template.format(username=username)

    conn = get_ldap_connection(user_dn=user_dn, password=password)
    if not conn:
        return False, False, False

    is_admin = False
    if admin_group_dn:
        try:
            is_admin = conn.search(admin_group_dn, f"(member={user_dn})", attributes=["cn"])
        except LDAPException as e:
            print(f"Could not check admin group membership: {e}")
            is_admin = False

    is_editor = False
    if editor_group_dn:
        try:
            is_editor = conn.search(editor_group_dn, f"(member={user_dn})", attributes=["cn"])
        except LDAPException as e:
            print(f"Could not check editor group membership: {e}")
            is_editor = False

    conn.unbind()
    return True, is_admin, is_editor


def add_ldap_user(username, password, email, given_name, surname):
    """Adds a new user to the LDAP directory with a hashed password."""
    user_dn_template = current_app.config.get("LDAP_USER_DN_TEMPLATE")
    if not user_dn_template:
        flash("LDAP user DN template is not configured.", "danger")
        return False

    user_dn = user_dn_template.format(username=username)

    object_classes = ["inetOrgPerson", "organizationalPerson", "person", "top"]

    hashed_password = hash_password_ssha(password)

    attributes = {
        "cn": f"{given_name} {surname}",
        "sn": surname,
        "givenName": given_name,
        "mail": email,
        "userPassword": hashed_password,
    }

    conn = get_ldap_connection()
    if not conn:
        return False

    try:
        success = conn.add(user_dn, object_classes, attributes)
        if not success:
            flash(f"LDAP Error: {conn.result['description']}", "danger")
            return False
        return True
    except LDAPException as e:
        flash(f"An exception occurred: {e}", "danger")
        return False
    finally:
        if conn:
            conn.unbind()


def delete_ldap_user(username):
    """Deletes a user from the LDAP directory."""
    user_dn_template = current_app.config.get("LDAP_USER_DN_TEMPLATE")
    if not user_dn_template:
        flash("LDAP user DN template is not configured.", "danger")
        return False

    user_dn = user_dn_template.format(username=username)

    conn = get_ldap_connection()
    if not conn:
        return False

    try:
        success = conn.delete(user_dn)
        if not success:
            flash(f"LDAP Error: {conn.result['description']}", "danger")
            return False
        return True
    except LDAPException as e:
        flash(f"An exception occurred: {e}", "danger")
        return False
    finally:
        if conn:
            conn.unbind()


def set_ldap_password(username, new_password):
    """Sets/resets the password for an LDAP user."""
    user_dn_template = current_app.config.get("LDAP_USER_DN_TEMPLATE")
    if not user_dn_template:
        flash("LDAP user DN template is not configured.", "danger")
        return False

    user_dn = user_dn_template.format(username=username)
    hashed_password = hash_password_ssha(new_password)

    conn = get_ldap_connection()
    if not conn:
        return False

    try:
        success = conn.modify(user_dn, {"userPassword": [(ldap3.MODIFY_REPLACE, [hashed_password])]})
        if not success:
            flash(f"LDAP Error: {conn.result['description']}", "danger")
            return False
        return True
    except LDAPException as e:
        flash(f"An exception occurred while setting LDAP password: {e}", "danger")
        return False
    finally:
        if conn:
            conn.unbind()


def search_ldap(filter_str, attributes, size_limit=0, search_base=None):
    """
    Performs a search on the LDAP directory using the admin credentials.
    """
    conn = get_ldap_connection(read_only=True)
    if not conn:
        return []

    if search_base is None:
        search_base = current_app.config["LDAP_BASE_DN"]

    try:
        conn.search(
            search_base=search_base, search_filter=filter_str, attributes=attributes, size_limit=size_limit
        )
        results = []
        for entry in conn.entries:
            result_dict = {"dn": entry.entry_dn}
            for attr in attributes:
                result_dict[attr] = entry[attr].values if entry[attr] else []
            results.append(result_dict)
        return results
    except LDAPException as e:
        print(f"LDAP search failed: {e}")
        flash("An error occurred while searching the directory.", "warning")
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
            search_base=dn, search_filter="(objectClass=*)", search_scope=ldap3.BASE, attributes=attributes
        )
        if conn.entries:
            entry = conn.entries[0]
            result_dict = {"dn": entry.entry_dn}
            for attr in attributes:
                result_dict[attr] = entry[attr].values if entry[attr] else []
            return result_dict
        return None
    except LDAPException as e:
        print(f"Failed to fetch entry by DN '{dn}': {e}")
        flash("Could not retrieve the specified entry.", "warning")
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
            if conn.result.get("description") == "entryAlreadyExists":
                flash(f"An entry with DN '{dn}' already exists.", "danger")
            elif conn.result.get("description") == "invalidDNSyntax":
                flash(f"The generated DN '{dn}' is invalid. Check your Base DN and the entry name.", "danger")
            else:
                flash(f"Could not add entry: {conn.result.get('message', 'Unknown error')}", "danger")
            return False
        return True
    except LDAPException as e:
        print(f"LDAP add operation failed: {e}")
        flash(f"A critical error occurred during the LDAP add operation: {e}", "danger")
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
            if conn.result.get("description") == "noSuchAttribute":
                error_details = conn.result.get("message", "N/A")
                flash(
                    f"Could not modify entry. The server reports a missing attribute. Details: {error_details}",
                    "danger",
                )
            else:
                flash(f"Could not modify entry: {conn.result.get('message', 'Unknown error')}", "danger")
            return False
        return True
    except LDAPException as e:
        print(f"LDAP modify operation failed: {e}")
        flash(f"A critical error occurred during the LDAP modify operation: {e}", "danger")
        return False
    finally:
        if conn:
            conn.unbind()
