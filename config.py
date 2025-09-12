# This file is part of Blackbook.
#
# Blackbook is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Blackbook is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Blackbook.  If not, see <https://www.gnu.org/licenses/>.

#
# Author: Taco Scheltema <github@scheltema.me>
#

import os

from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    """Base config."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "you-will-never-guess")
    FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() in ("true", "1", "t")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///" + os.path.join(basedir, "app.db"))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    READONLY = os.environ.get("READONLY", "False").lower() in ("true", "1", "t")
    APP_TITLE = os.environ.get("APP_TITLE", "Blackbook")

    # --- LDAP Configuration ---
    # The user for binding must have read access to the directory.
    # Write access is required for add/edit/delete features.
    LDAP_SERVER = os.environ.get("LDAP_SERVER", "ldap://localhost:389")
    LDAP_BIND_DN = os.environ.get("LDAP_BIND_DN", "cn=admin,dc=example,dc=com")
    LDAP_BIND_PASSWORD = os.environ.get("LDAP_BIND_PASSWORD", "admin")
    LDAP_BASE_DN = os.environ.get("LDAP_BASE_DN", "dc=example,dc=com")
    LDAP_USER_DN_TEMPLATE = os.environ.get("LDAP_USER_DN_TEMPLATE", "uid={username},ou=users,dc=example,dc=com")
    LDAP_CONTACT_DN_TEMPLATE = os.environ.get("LDAP_CONTACT_DN_TEMPLATE", "cn={cn},ou=contacts,dc=example,dc=com")
    LDAP_USE_SSL = os.environ.get("LDAP_USE_SSL", "False").lower() in ("true", "1", "t")

    # Filter to apply when searching for contacts
    ADDRESSBOOK_FILTER = os.environ.get("ADDRESSBOOK_FILTER")
    LDAP_CONTACTS_DN = ADDRESSBOOK_FILTER if ADDRESSBOOK_FILTER else LDAP_BASE_DN

    # Define the objectClass for a person entry in LDAP.
    # For Active Directory, this is often just 'user'.
    # For OpenLDAP, 'inetOrgPerson' is common.
    LDAP_PERSON_OBJECT_CLASS = os.environ.get("LDAP_PERSON_OBJECT_CLASS", "inetOrgPerson")
    LDAP_COMPANY_LINK_ATTRIBUTE = os.environ.get("LDAP_COMPANY_LINK_ATTRIBUTE", "o")

    # Map technical LDAP attribute names to human-readable names.
    # This also controls which attributes are displayed and editable.
    LDAP_ATTRIBUTE_MAP_STR = os.environ.get(
        "LDAP_ATTRIBUTE_MAP",
        "cn:Full Name,sn:Surname,givenName:Given Name,mail:Email,"
        "telephoneNumber:Phone,o:Company,title:Title,street:Street,"
        "l:City,postalCode:Postal Code,c:Country,manager:Manager,jpegPhoto:Photo",
    )
    LDAP_ATTRIBUTE_MAP = dict(item.split(":") for item in LDAP_ATTRIBUTE_MAP_STR.split(","))
    LDAP_PERSON_ATTRIBUTES = list(LDAP_ATTRIBUTE_MAP.keys())

    # --- Authentication Configuration ---
    ENABLE_LOCAL_LOGIN = os.environ.get("ENABLE_LOCAL_LOGIN", "True").lower() in ("true", "1", "t")
    ENABLE_LDAP_LOGIN = os.environ.get("ENABLE_LDAP_LOGIN", "True").lower() in ("true", "1", "t")

    # --- Feature Toggles ---
    ENABLE_GOOGLE_CONTACTS_IMPORT = os.environ.get("ENABLE_GOOGLE_CONTACTS_IMPORT", "False").lower() in (
        "true",
        "1",
        "t",
    )
    ENABLE_PRIVATE_CONTACTS = os.environ.get("ENABLE_PRIVATE_CONTACTS", "False").lower() in ("true", "1", "t")
    LDAP_OWNER_ATTRIBUTE = os.environ.get("LDAP_OWNER_ATTRIBUTE", "employeeNumber")

    # Ensure the owner attribute is always fetched from LDAP for filtering
    if LDAP_OWNER_ATTRIBUTE not in LDAP_PERSON_ATTRIBUTES:
        LDAP_PERSON_ATTRIBUTES.append(LDAP_OWNER_ATTRIBUTE)

    LDAP_ADMIN_GROUP_DN = os.environ.get("LDAP_ADMIN_GROUP_DN")
    LDAP_EDITOR_GROUP_DN = os.environ.get("LDAP_EDITOR_GROUP_DN")

    # --- SSO Provider Configuration ---
    # Google
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

    # Keycloak
    KEYCLOAK_CLIENT_ID = os.environ.get("KEYCLOAK_CLIENT_ID")
    KEYCLOAK_CLIENT_SECRET = os.environ.get("KEYCLOAK_CLIENT_SECRET")
    KEYCLOAK_SERVER_URL = os.environ.get("KEYCLOAK_SERVER_URL")
    KEYCLOAK_ADMIN_GROUP = os.environ.get("KEYCLOAK_ADMIN_GROUP")
    KEYCLOAK_EDITOR_GROUP = os.environ.get("KEYCLOAK_EDITOR_GROUP")

    # Authentik
    AUTHENTIK_CLIENT_ID = os.environ.get("AUTHENTIK_CLIENT_ID")
    AUTHENTIK_CLIENT_SECRET = os.environ.get("AUTHENTIK_CLIENT_SECRET")
    AUTHENTIK_SERVER_URL = os.environ.get("AUTHENTIK_SERVER_URL")
    AUTHENTIK_ADMIN_GROUP = os.environ.get("AUTHENTIK_ADMIN_GROUP")
    AUTHENTIK_EDITOR_GROUP = os.environ.get("AUTHENTIK_EDITOR_GROUP")

    # --- Caching Configuration ---
    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get("CACHE_DEFAULT_TIMEOUT", 300))
    CACHE_REFRESH_INTERVAL = int(os.environ.get("CACHE_REFRESH_INTERVAL", 300))

    # --- Avatar Generation ---
    ENABLE_GENERATED_AVATARS = os.environ.get("ENABLE_GENERATED_AVATARS", "False").lower() in (
        "true",
        "1",
        "t",
    )
    AVATAR_THEME = os.environ.get("AVATAR_THEME", "all")

    # --- Pagination Configuration ---
    PAGE_SIZE_OPTIONS_STR = os.environ.get("PAGE_SIZE_OPTIONS", "20,30,50")
    try:
        PAGE_SIZE_OPTIONS = [int(s.strip()) for s in PAGE_SIZE_OPTIONS_STR.split(",")]
    except (ValueError, IndexError):
        print("WARNING: PAGE_SIZE_OPTIONS is malformed. Using default.")
        PAGE_SIZE_OPTIONS = [20, 30, 50]

    DEFAULT_PAGE_SIZE = PAGE_SIZE_OPTIONS[0] if PAGE_SIZE_OPTIONS else 20

    # --- Mail Server Configuration ---
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 25))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS") is not None
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_FROM_ADDRESS = os.environ.get("MAIL_FROM_ADDRESS", "no-reply@localhost")
    PASSWORD_RESET_EXPIRATION_HOURS = int(os.environ.get("PASSWORD_RESET_EXPIRATION_HOURS", 24))
