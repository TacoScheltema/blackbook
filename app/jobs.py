from app import cache
from app.ldap_utils import search_ldap


def refresh_ldap_cache(app):
    """
    This function is run by the background scheduler. It performs the slow
    LDAP query and stores the result in the cache.
    """
    with app.app_context():
        print("SCHEDULER: Refreshing LDAP contact cache...")
        person_class = app.config["LDAP_PERSON_OBJECT_CLASS"]
        person_attrs = app.config["LDAP_PERSON_ATTRIBUTES"]
        search_filter = f"(objectClass={person_class})"
        contacts_dn = app.config["LDAP_CONTACTS_DN"]

        people_list = search_ldap(search_filter, person_attrs, search_base=contacts_dn)

        # Manually set the cache value. This overwrites the old data.
        cache.set("all_people", people_list)
        print(f"SCHEDULER: Cache refreshed with {len(people_list)} contacts.")
