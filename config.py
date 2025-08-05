# config.py
import os
from dotenv import load_dotenv

# Load environment variables from a .env file
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    """
    Main configuration class.
    
    Loads settings from environment variables for security and flexibility.
    """
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-very-secret-key-that-you-should-change'
    FLASK_DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')

    # --- LDAP Configuration ---
    # The URL of your LDAP server (e.g., 'ldaps://ldap.example.com:636')
    LDAP_SERVER = os.environ.get('LDAP_SERVER')

    # The Base DN (Distinguished Name) to use for searching.
    # This is the starting point in the LDAP tree. e.g., 'dc=example,dc=com'
    LDAP_BASE_DN = os.environ.get('LDAP_BASE_DN')

    # The DN for binding (authenticating) to the LDAP server.
    # This user needs read access to the directory.
    # e.g., 'cn=admin,dc=example,dc=com'
    LDAP_BIND_DN = os.environ.get('LDAP_BIND_DN')

    # The password for the bind user.
    LDAP_BIND_PASSWORD = os.environ.get('LDAP_BIND_PASSWORD')
    
    # Set to True if your LDAP server uses SSL (e.g., for port 636)
    LDAP_USE_SSL = os.environ.get('LDAP_USE_SSL', 'False').lower() in ('true', '1', 't')

    # --- ObjectClass Configuration ---
    # The objectClass used to identify a person in your LDAP schema.
    # Common values are 'inetOrgPerson', 'person', or 'posixAccount'.
    LDAP_PERSON_OBJECT_CLASS = os.environ.get('LDAP_PERSON_OBJECT_CLASS', 'inetOrgPerson')

    # The objectClass used to identify a company/organization.
    # Common value is 'organization'.
    LDAP_COMPANY_OBJECT_CLASS = os.environ.get('LDAP_COMPANY_OBJECT_CLASS', 'organization')

    # The attribute on a person's entry that links them to a company.
    # This is typically 'o' (organizationName).
    LDAP_COMPANY_LINK_ATTRIBUTE = os.environ.get('LDAP_COMPANY_LINK_ATTRIBUTE', 'o')


