# filename: app/main/helpers.py
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

import base64
import json
import math
import re
import uuid
from functools import wraps

import ldap3
import requests
from flask import abort, current_app, request
from flask_login import current_user

from app import cache, db, scheduler
from app.jobs import refresh_ldap_cache
from app.ldap_utils import add_ldap_entry, ensure_ou_exists, search_ldap


def get_config(key):
    """Helper to safely get config values."""
    return current_app.config.get(key, "")


def b64decode_with_padding(s):
    """Helper to decode a URL-safe base64 string, adding padding if necessary."""
    missing_padding = len(s) % 4
    if missing_padding:
        s += "=" * (4 - missing_padding)
    return base64.urlsafe_b64decode(s).decode("utf-8")


def get_pagination_params(total_items, page, page_size):
    """Helper function to calculate pagination parameters."""
    total_pages = math.ceil(total_items / page_size)
    pages_to_show = 6
    start_page = max(1, page - (pages_to_show // 2))
    end_page = min(total_pages, start_page + pages_to_show - 1)
    if end_page - start_page + 1 < pages_to_show:
        start_page = max(1, end_page - pages_to_show + 1)
    return range(start_page, end_page + 1), total_pages


def get_index_request_args():
    """Helper to get and process request arguments for the index page."""
    args = {
        "search_query": request.args.get("q", ""),
        "sort_by": request.args.get("sort_by", "sn"),
        "sort_order": request.args.get("sort_order", "asc"),
        "letter": request.args.get("letter", ""),
    }

    page_size_options = get_config("PAGE_SIZE_OPTIONS")
    default_page_size = get_config("DEFAULT_PAGE_SIZE")
    page_size_from_request = request.args.get("page_size", type=int)

    page_size = default_page_size
    if current_user.is_authenticated:
        if page_size_from_request and page_size_from_request in page_size_options:
            page_size = page_size_from_request
            if current_user.page_size != page_size:
                current_user.page_size = page_size
                db.session.commit()
        else:
            page_size = current_user.page_size or default_page_size
    elif page_size_from_request and page_size_from_request in page_size_options:
        page_size = page_size_from_request

    args["page_size"] = page_size

    try:
        args["page"] = int(request.args.get("page", 1))
    except ValueError:
        args["page"] = 1

    return args


def filter_and_sort_people(all_people, args):
    """Helper to filter and sort the list of people."""
    if args["search_query"]:
        query = args["search_query"].lower()
        all_people = [p for p in all_people if p.get("cn") and p["cn"] and query in p["cn"][0].lower()]

    if args["letter"]:
        all_people = [
            p for p in all_people if p.get("sn") and p["sn"] and p["sn"][0].upper().startswith(args["letter"])
        ]

    if args["sort_by"] in get_config("LDAP_PERSON_ATTRIBUTES"):
        all_people.sort(
            key=lambda p: (p.get(args["sort_by"])[0] if p.get(args["sort_by"]) else "").lower(),
            reverse=(args["sort_order"] == "desc"),
        )
    return all_people


def build_ldap_changes(form_data, current_person, person_attrs):
    """Builds the dictionary of changes for an LDAP modification."""
    changes = {}
    editable_attrs = [attr for attr in person_attrs if attr != "jpegPhoto"]

    for attr in editable_attrs:
        form_value = form_data.get(attr)
        if form_value is not None:
            attr_exists = current_person.get(attr)
            current_value = (attr_exists or [None])[0]

            if form_value and form_value != current_value:
                changes[attr] = [(ldap3.MODIFY_REPLACE, [form_value])]
            elif not form_value and attr_exists:
                changes[attr] = [(ldap3.MODIFY_DELETE, [])]

    delete_photo_flag = form_data.get("delete_photo") == "true"
    new_photo_data_b64 = form_data.get("jpegPhoto")

    if delete_photo_flag:
        if "jpegPhoto" in current_person:
            changes["jpegPhoto"] = [(ldap3.MODIFY_DELETE, [])]
    elif new_photo_data_b64:
        photo_data_bytes = base64.b64decode(new_photo_data_b64)
        changes["jpegPhoto"] = [(ldap3.MODIFY_REPLACE, [photo_data_bytes])]

    return changes


def admin_required(f):
    """Decorator to restrict access to admin users."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)

    return decorated_function


def editor_required(f):
    """Decorator to restrict access to admin or editor users."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_app.config["READONLY"]:
            abort(403)
        if not current_user.is_authenticated or not (current_user.is_admin or current_user.is_editor):
            abort(403)
        return f(*args, **kwargs)

    return decorated_function


def get_visible_contacts():
    """Gets all contacts visible to the current user (public + their private)."""
    public_contacts = cache.get("all_people") or []
    private_contacts = []

    private_ou_template = get_config("LDAP_PRIVATE_OU_TEMPLATE")
    if private_ou_template:
        user_ou = private_ou_template.format(user_id=current_user.id)
        person_attrs = get_config("LDAP_PERSON_ATTRIBUTES")
        private_contacts = search_ldap("(objectClass=*)", person_attrs, search_base=user_ou)

    for contact in private_contacts:
        contact["is_private"] = True

    all_contacts_dict = {p["dn"]: p for p in private_contacts + public_contacts}
    return list(all_contacts_dict.values())


def _map_google_contact_to_ldap(person):
    """Maps a Google People API person object to an LDAP attribute dictionary."""
    attributes = {}
    if person.get("names"):
        attributes["cn"] = person["names"][0].get("displayName")
        attributes["givenName"] = person["names"][0].get("givenName")
        attributes["sn"] = person["names"][0].get("familyName")
        if not attributes["sn"] and attributes["cn"]:
            attributes["sn"] = attributes["cn"]
    if not attributes.get("cn"):
        return None

    if person.get("emailAddresses"):
        attributes["mail"] = person["emailAddresses"][0].get("value")
    if person.get("phoneNumbers"):
        phone = person["phoneNumbers"][0].get("value")
        if phone:
            attributes["telephoneNumber"] = re.sub(r"[^0-9+]", "", phone)
    if person.get("organizations"):
        attributes["o"] = person["organizations"][0].get("name")
        attributes["title"] = person["organizations"][0].get("title")
    if person.get("addresses"):
        attributes["street"] = person["addresses"][0].get("streetAddress")
        attributes["l"] = person["addresses"][0].get("city")
        attributes["postalCode"] = person["addresses"][0].get("postalCode")
        attributes["c"] = person["addresses"][0].get("countryCode")

    return attributes


def _process_and_add_contact(attributes, existing_names, existing_emails, search_base, app_config, user_id):
    """Shared logic to check for duplicates and add a contact to LDAP."""
    name = (attributes.get("cn") or "").lower()
    email = (attributes.get("mail") or "").lower()

    if (email and email in existing_emails) or (name and name in existing_names):
        return "skipped", f"Skipping duplicate: {attributes.get('cn')}"

    attributes[app_config["LDAP_OWNER_ATTRIBUTE"]] = str(user_id)
    attributes["uid"] = str(uuid.uuid4())
    rdn = f"uid={attributes['uid']}"
    new_dn = f"{rdn},{search_base}"
    object_classes = app_config["LDAP_PERSON_OBJECT_CLASS"].split(",")

    if add_ldap_entry(new_dn, object_classes, {k: v for k, v in attributes.items() if v}):
        if email:
            existing_emails.add(email)
        if name:
            existing_names.add(name)
        return "imported", f"Successfully imported: {attributes.get('cn')}"

    return "failed", f"Failed to import: {attributes.get('cn')}"


def generate_import_stream(token, app, user_id, privacy):
    """A generator function that performs the import and yields progress."""
    if not token:
        yield f"data: {json.dumps({'status': 'error', 'message': 'No token found.'})}\n\n"
        return

    try:
        connections = _fetch_google_connections(token.get("access_token"))
    except requests.exceptions.RequestException as e:
        yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
        return

    total = len(connections)
    if total == 0:
        yield f"data: {json.dumps({'status': 'complete', 'message': 'No contacts found.'})}\n\n"
        return

    imported_count, skipped_count = 0, 0

    with app.app_context():
        if privacy == "private":
            base = app.config["LDAP_PRIVATE_OU_TEMPLATE"].format(user_id=user_id)
            ensure_ou_exists(base)
        else:
            base = app.config["LDAP_CONTACTS_DN"]
        existing = search_ldap("(objectClass=*)", ["cn", "mail"], search_base=base)
        existing_emails = {p["mail"][0].lower() for p in existing if p.get("mail") and p["mail"][0]}
        existing_names = {p["cn"][0].lower() for p in existing if p.get("cn") and p["cn"][0]}

    for i, person in enumerate(connections):
        with app.app_context():
            attributes = _map_google_contact_to_ldap(person)
            if not attributes:
                skipped_count += 1
                msg = "Skipping contact with no name."
            else:
                status, msg = _process_and_add_contact(
                    attributes, existing_names, existing_emails, base, app.config, user_id
                )
                if status == "imported":
                    imported_count += 1
                else:
                    skipped_count += 1

            payload = {"status": "progress", "current": i + 1, "total": total, "message": msg}
            yield f"data: {json.dumps(payload)}\n\n"

    if imported_count > 0:
        with app.app_context():
            scheduler.add_job(func=refresh_ldap_cache, args=[app], id="manual_refresh_import", replace_existing=True)

    final_msg = f"Import complete. Added {imported_count}, skipped {skipped_count}."
    yield f"data: {json.dumps({'status': 'complete', 'message': final_msg})}\n\n"
# end file
