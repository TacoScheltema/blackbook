import os
from dotenv import load_dotenv
from collections import OrderedDict

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

    # --- Authentication Method Toggles ---
    ENABLE_LOCAL_LOGIN = os.environ.get('ENABLE_LOCAL_LOGIN', 'True').lower() in ('true', '1', 't')
    ENABLE_LDAP_LOGIN = os.environ.get('ENABLE_LDAP_LOGIN', 'True').lower() in ('true', '1', 't')

    # --- Database Configuration ---
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Caching Configuration ---
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('LDAP_CACHE_TIMEOUT', 300))
    CACHE_REFRESH_INTERVAL = int(os.environ.get('CACHE_REFRESH_INTERVAL', 300))


    # --- LDAP Configuration ---
    LDAP_SERVER = os.environ.get('LDAP_SERVER')
    LDAP_BASE_DN = os.environ.get('LDAP_BASE_DN')
    LDAP_BIND_DN = os.environ.get('LDAP_BIND_DN')
    LDAP_BIND_PASSWORD = os.environ.get('LDAP_BIND_PASSWORD')
    LDAP_USE_SSL = os.environ.get('LDAP_USE_SSL', 'False').lower() in ('true', '1', 't')

    # --- Contact Filter ---
    LDAP_CONTACTS_DN = os.environ.get('ADDRESSBOOK_FILTER') or LDAP_BASE_DN

    # --- SSO/OAuth Configuration ---
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')

    KEYCLOAK_CLIENT_ID = os.environ.get('KEYCLOAK_CLIENT_ID')
    KEYCLOAK_CLIENT_SECRET = os.environ.get('KEYCLOAK_CLIENT_SECRET')
    KEYCLOAK_SERVER_URL = os.environ.get('KEYCLOAK_SERVER_URL')

    AUTHENTIK_CLIENT_ID = os.environ.get('AUTHENTIK_CLIENT_ID')
    AUTHENTIK_CLIENT_SECRET = os.environ.get('AUTHENTIK_CLIENT_SECRET')
    AUTHENTIK_SERVER_URL = os.environ.get('AUTHENTIK_SERVER_URL')

    # --- ObjectClass Configuration ---
    LDAP_PERSON_OBJECT_CLASS = os.environ.get('LDAP_PERSON_OBJECT_CLASS', 'inetOrgPerson')
    LDAP_COMPANY_LINK_ATTRIBUTE = os.environ.get('LDAP_COMPANY_LINK_ATTRIBUTE', 'o')

    # --- Attribute Configuration ---
    LDAP_ATTRIBUTE_MAP_STR = os.environ.get('LDAP_ATTRIBUTE_MAP')
    if LDAP_ATTRIBUTE_MAP_STR:
        try:
            LDAP_ATTRIBUTE_MAP = OrderedDict(
                (pair.split(':')[0].strip(), pair.split(':')[1].strip())
                for pair in LDAP_ATTRIBUTE_MAP_STR.split(',')
            )
        except IndexError:
            print("WARNING: LDAP_ATTRIBUTE_MAP is malformed. Using default.")
            LDAP_ATTRIBUTE_MAP = OrderedDict()
    else:
        LDAP_ATTRIBUTE_MAP = OrderedDict()

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

    LDAP_PERSON_ATTRIBUTES = list(LDAP_ATTRIBUTE_MAP.keys())

    # --- Company Attribute Configuration ---
    LDAP_COMPANY_ATTRIBUTE_MAP_STR = os.environ.get('LDAP_COMPANY_ATTRIBUTE_MAP')
    if LDAP_COMPANY_ATTRIBUTE_MAP_STR:
        try:
            LDAP_COMPANY_ATTRIBUTE_MAP = OrderedDict(
                (pair.split(':')[0].strip(), pair.split(':')[1].strip())
                for pair in LDAP_COMPANY_ATTRIBUTE_MAP_STR.split(',')
            )
        except IndexError:
            print("WARNING: LDAP_COMPANY_ATTRIBUTE_MAP is malformed. Using default.")
            LDAP_COMPANY_ATTRIBUTE_MAP = OrderedDict()
    else:
        LDAP_COMPANY_ATTRIBUTE_MAP = OrderedDict()

    if not LDAP_COMPANY_ATTRIBUTE_MAP:
        LDAP_COMPANY_ATTRIBUTE_MAP = OrderedDict([
            ('o', 'Company'),
            ('street', 'Street'),
            ('postalCode', 'Postcode'),
            ('l', 'City')
        ])

    LDAP_COMPANY_ATTRIBUTES = list(LDAP_COMPANY_ATTRIBUTE_MAP.keys())


    # --- Pagination Configuration ---
    PAGE_SIZE_OPTIONS_STR = os.environ.get('PAGE_SIZE_OPTIONS', '20,30,50')
    try:
        PAGE_SIZE_OPTIONS = [int(s.strip()) for s in PAGE_SIZE_OPTIONS_STR.split(',')]
    except (ValueError, IndexError):
        print("WARNING: PAGE_SIZE_OPTIONS is malformed. Using default.")
        PAGE_SIZE_OPTIONS = [20, 30, 50]

    DEFAULT_PAGE_SIZE = PAGE_SIZE_OPTIONS[0] if PAGE_SIZE_OPTIONS else 20
