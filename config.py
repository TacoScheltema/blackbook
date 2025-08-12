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

    # --- Caching Configuration ---
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('LDAP_CACHE_TIMEOUT', 300))

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

    # --- Pagination Configuration ---
    PAGE_SIZE_OPTIONS_STR = os.environ.get('PAGE_SIZE_OPTIONS', '20,30,50')
    try:
        PAGE_SIZE_OPTIONS = [int(s.strip()) for s in PAGE_SIZE_OPTIONS_STR.split(',')]
    except (ValueError, IndexError):
        print("WARNING: PAGE_SIZE_OPTIONS is malformed. Using default.")
        PAGE_SIZE_OPTIONS = [20, 30, 50]

    # The default page size will be the first option in the list.
    DEFAULT_PAGE_SIZE = PAGE_SIZE_OPTIONS[0] if PAGE_SIZE_OPTIONS else 20

