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

from app import cache
from app.ldap_utils import search_ldap


def refresh_ldap_cache(app):
    """
    This function is run by the background scheduler. It performs the slow
    LDAP query and stores the result in the cache.
    """
    with app.app_context():
        print("SCHEDULER: Refreshing LDAP contact cache...")
        person_classes = app.config["LDAP_PERSON_OBJECT_CLASS"].split(",")
        person_attrs = app.config["LDAP_PERSON_ATTRIBUTES"]
        search_filter = "".join([f"(objectClass={cls.strip()})" for cls in person_classes])
        if len(person_classes) > 1:
            search_filter = f"(&{search_filter})"

        contacts_dn = app.config["LDAP_CONTACTS_DN"]

        people_list = search_ldap(search_filter, person_attrs, search_base=contacts_dn)

        # Manually set the cache value. This overwrites the old data.
        cache.set("all_people", people_list)
        print(f"SCHEDULER: Cache refreshed with {len(people_list)} contacts.")
