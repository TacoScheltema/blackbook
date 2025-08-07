import os
from dotenv import load_dotenv

## Load environment variables from a .env file
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
    LDAP_SERVER = os.environ.get('LDAP_SERVER')
    LDAP_BASE_DN = os.environ.get('LDAP_BASE_DN')
    LDAP_BIND_DN = os.environ.get('LDAP_BIND_DN')
    LDAP_BIND_PASSWORD = os.environ.get('LDAP_BIND_PASSWORD')
    LDAP_USE_SSL = os.environ.get('LDAP_USE_SSL', 'False').lower() in ('true', '1', 't')

    # --- ObjectClass Configuration ---
    LDAP_PERSON_OBJECT_CLASS = os.environ.get('LDAP_PERSON_OBJECT_CLASS', 'inetOrgPerson')
    LDAP_COMPANY_OBJECT_CLASS = os.environ.get('LDAP_COMPANY_OBJECT_CLASS', 'organization')
    LDAP_COMPANY_LINK_ATTRIBUTE = os.environ.get('LDAP_COMPANY_LINK_ATTRIBUTE', 'o')

    # --- Attribute Configuration ---
    # Attributes to fetch and display for a person.
    # This is read from a comma-separated string in the .env file.
    LDAP_PERSON_ATTRIBUTES_STR = os.environ.get('LDAP_PERSON_ATTRIBUTES')
    if LDAP_PERSON_ATTRIBUTES_STR:
        # If the variable is set, split it into a list
        LDAP_PERSON_ATTRIBUTES = [attr.strip() for attr in LDAP_PERSON_ATTRIBUTES_STR.split(',')]
    else:
        # Otherwise, use a default list of common attributes.
        LDAP_PERSON_ATTRIBUTES = [
            'cn', 'givenName', 'sn', 'mail', 'telephoneNumber', 
            'o', 'street', 'l', 'postalCode'
        ]



