import os
from dotenv import load_dotenv
from collections import OrderedDict

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
    # A mapping of LDAP attribute names to human-readable display names.
    # This is parsed from a string like "attr1:Name 1,attr2:Name 2"
    LDAP_ATTRIBUTE_MAP_STR = os.environ.get('LDAP_ATTRIBUTE_MAP')
    if LDAP_ATTRIBUTE_MAP_STR:
        try:
            # Use OrderedDict to preserve the order from the .env file.
            LDAP_ATTRIBUTE_MAP = OrderedDict(
                (pair.split(':')[0].strip(), pair.split(':')[1].strip())
                for pair in LDAP_ATTRIBUTE_MAP_STR.split(',')
            )
        except IndexError:
            # Handle malformed string by falling back to a default.
            print("WARNING: LDAP_ATTRIBUTE_MAP is malformed. Using default.")
            LDAP_ATTRIBUTE_MAP = OrderedDict()
    else:
        LDAP_ATTRIBUTE_MAP = OrderedDict()

    # If the map is empty (not set or malformed), use a default.
    if not LDAP_ATTRIBUTE_MAP:
        LDAP_ATTRIBUTE_MAP = OrderedDict([
            ('cn', 'Full Name'),
            ('givenName', 'Given Name'),
            ('sn', 'Surname'),
            ('mail', 'Email'),
            ('telephoneNumber', 'Telephone'),
            ('o', 'Company'),
            ('street', 'Street'),
            ('l', 'City'),
            ('postalCode', 'Postal Code')
        ])

    # The attributes to fetch are the keys from our map.
    LDAP_PERSON_ATTRIBUTES = list(LDAP_ATTRIBUTE_MAP.keys())



