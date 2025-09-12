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

# Version: 0.36

import base64
import json
import math
import re
import time
import uuid
from datetime import datetime, timezone
from functools import wraps

import ldap3
import requests
from flask import Response, abort, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from app import cache, db, oauth, scheduler
from app.email import send_password_reset_email
from app.jobs import refresh_ldap_cache
from app.ldap_utils import (
    add_ldap_entry,
    add_ldap_user,
    delete_ldap_contact,
    delete_ldap_user,
    ensure_ou_exists,
    get_entry_by_dn,
    modify_ldap_entry,
    move_ldap_entry,
    search_ldap,
)
from app.main import bp
from app.main.avatar_generator import generate_avatar
from app.main.countries import countries
from app.models import User


def get_config(key):
    """Helper to safely get config values."""
    return current_app.config.get(key, "")


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


def _get_index_request_args():
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


def _get_visible_contacts():
    """Gets all contacts visible to the current user (public + their private)."""
    public_contacts = cache.get("all_people") or []
    private_contacts = []

    private_ou_template = get_config("LDAP_PRIVATE_OU_TEMPLATE")
    if private_ou_template:
        user_ou = private_ou_template.format(user_id=current_user.id)
        person_attrs = get_config("LDAP_PERSON_ATTRIBUTES")
        private_contacts = search_ldap("(objectClass=*)", person_attrs, search_base=user_ou)

    # Add a flag to distinguish private contacts in the template
    for contact in private_contacts:
        contact["is_private"] = True

    # Combine and remove duplicates (in case a contact was moved but cache is stale)
    all_contacts_dict = {p["dn"]: p for p in private_contacts + public_contacts}
    return list(all_contacts_dict.values())


def _filter_and_sort_people(all_people, args):
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


@bp.route("/")
@login_required
def index():
    """Main index page. Now only shows a paginated list of all persons."""
    args = _get_index_request_args()
    all_visible_contacts = _get_visible_contacts()
    filtered_people = _filter_and_sort_people(all_visible_contacts, args)

    total_people = len(filtered_people)
    start_index = (args["page"] - 1) * args["page_size"]
    end_index = start_index + args["page_size"]
    people_on_page = filtered_people[start_index:end_index]

    page_numbers, total_pages = get_pagination_params(total_people, args["page"], args["page_size"])
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    return render_template(
        "index.html",
        title="Address Book",
        people=people_on_page,
        search_query=args["search_query"],
        page=args["page"],
        page_size=args["page_size"],
        total_pages=total_pages,
        total_people=total_people,
        page_numbers=page_numbers,
        sort_by=args["sort_by"],
        sort_order=args["sort_order"],
        alphabet=alphabet,
        letter=args["letter"],
    )


@bp.route("/companies")
@login_required
def all_companies():
    """Displays a list of unique company names derived from the contacts."""
    letter = request.args.get("letter", "")
    all_visible_contacts = _get_visible_contacts()
    company_link_attr = get_config("LDAP_COMPANY_LINK_ATTRIBUTE")

    company_names = sorted(
        list(
            set(
                p[company_link_attr][0]
                for p in all_visible_contacts
                if p.get(company_link_attr) and p[company_link_attr]
            )
        )
    )

    if letter:
        company_names = [name for name in company_names if name.upper().startswith(letter)]

    total_companies = len(company_names)

    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1

    page_size = 20
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    companies_on_page = company_names[start_index:end_index]

    page_numbers, total_pages = get_pagination_params(total_companies, page, page_size)
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    return render_template(
        "all_companies.html",
        title="All Companies",
        companies=companies_on_page,
        page=page,
        total_pages=total_pages,
        page_numbers=page_numbers,
        alphabet=alphabet,
        letter=letter,
    )


@bp.route("/company/<b64_company_name>")
@login_required
def company_detail(b64_company_name):
    """Displays a list of people belonging to a specific company."""
    try:
        company_name = b64decode_with_padding(b64_company_name)
    except (base64.binascii.Error, UnicodeDecodeError):
        abort(404)

    all_visible_contacts = _get_visible_contacts()
    company_link_attr = get_config("LDAP_COMPANY_LINK_ATTRIBUTE")

    employees = [
        p for p in all_visible_contacts if p.get(company_link_attr) and p[company_link_attr][0] == company_name
    ]
    employees.sort(key=lambda p: (p.get("sn")[0] if p.get("sn") else "").lower())

    return render_template(
        "company_detail.html",
        title=f"Company: {company_name}",
        company_name=company_name,
        employees=employees,
    )


@bp.route("/company/orgchart/<b64_company_name>")
@login_required
def company_orgchart(b64_company_name):
    """Displays an org chart for a specific company."""
    try:
        company_name = b64decode_with_padding(b64_company_name)
    except (base64.binascii.Error, UnicodeDecodeError):
        abort(404)

    all_visible_contacts = _get_visible_contacts()
    company_link_attr = get_config("LDAP_COMPANY_LINK_ATTRIBUTE")

    employees = [
        p for p in all_visible_contacts if p.get(company_link_attr) and p[company_link_attr][0] == company_name
    ]

    employees_for_json = []
    for employee in employees:
        avatar_url = None
        if "jpegPhoto" in employee and employee["jpegPhoto"] and employee["jpegPhoto"][0]:
            photo_data = base64.b64encode(employee["jpegPhoto"][0]).decode("utf-8")
            avatar_url = f"data:image/jpeg;base64,{photo_data}"
        elif get_config("ENABLE_GENERATED_AVATARS"):
            avatar_url = url_for("main.avatar", seed=employee["dn"], _external=True)

        # Create a clean, JSON-serializable dictionary
        clean_employee = {
            "dn": employee["dn"],
            "cn": employee.get("cn"),
            "title": employee.get("title"),
            "manager": employee.get("manager"),
            "avatar_url": avatar_url,
        }
        employees_for_json.append(clean_employee)

    return render_template(
        "company_orgchart.html",
        title=f"Org Chart: {company_name}",
        company_name=company_name,
        employees=employees_for_json,
    )


@bp.route("/company/cards/<b64_company_name>")
@login_required
def company_cards(b64_company_name):
    """Displays a grid of cards for people belonging to a specific company."""
    try:
        company_name = b64decode_with_padding(b64_company_name)
    except (base64.binascii.Error, UnicodeDecodeError):
        abort(404)

    all_visible_contacts = _get_visible_contacts()
    company_link_attr = get_config("LDAP_COMPANY_LINK_ATTRIBUTE")

    employees = [
        p for p in all_visible_contacts if p.get(company_link_attr) and p[company_link_attr][0] == company_name
    ]

    return render_template(
        "company_cards.html",
        title=f"Company: {company_name}",
        company_name=company_name,
        employees=employees,
    )


@bp.route("/person/<b64_dn>")
@login_required
def person_detail(b64_dn):
    """Displays details for a single person."""
    try:
        dn = b64decode_with_padding(b64_dn)
    except (base64.binascii.Error, UnicodeDecodeError):
        abort(404)

    person_attrs = get_config("LDAP_PERSON_ATTRIBUTES")
    person = get_entry_by_dn(dn, person_attrs)
    if not person:
        abort(404)

    # Pre-process the photo for direct use in the template
    if "jpegPhoto" in person and person["jpegPhoto"] and person["jpegPhoto"][0]:
        person["jpegPhoto"][0] = base64.b64encode(person["jpegPhoto"][0]).decode("utf-8")

    person_name = person.get("cn", ["Unknown"])[0]

    manager_name = None
    if "manager" in person and person["manager"]:
        manager_dn = person["manager"][0]
        manager = get_entry_by_dn(manager_dn, ["cn"])
        if manager:
            manager_name = manager.get("cn", [None])[0]

    person_for_json = person.copy()

    back_params = {
        "page": request.args.get("page"),
        "page_size": request.args.get("page_size"),
        "q": request.args.get("q"),
        "sort_by": request.args.get("sort_by"),
        "sort_order": request.args.get("sort_order"),
    }
    back_params = {k: v for k, v in back_params.items() if v is not None}

    private_ou_template = get_config("LDAP_PRIVATE_OU_TEMPLATE")
    is_private = private_ou_template and f"ou=user_{current_user.id}" in dn

    return render_template(
        "person_detail.html",
        title=person_name,
        person=person,
        person_for_json=person_for_json,
        b64_dn=b64_dn,
        back_params=back_params,
        manager_name=manager_name,
        countries=countries,
        is_private=is_private,
    )


@bp.route("/person/map/<b64_dn>")
@login_required
def person_map(b64_dn):
    """Displays the location of a person on a map."""
    try:
        dn = b64decode_with_padding(b64_dn)
    except (base64.binascii.Error, UnicodeDecodeError):
        abort(404)

    person_attrs = ["cn", "street", "l", "postalCode", "c"]
    person = get_entry_by_dn(dn, person_attrs)
    if not person:
        abort(404)

    latitude, longitude = None, None
    address_parts = [
        (person.get("street") or [""])[0],
        (person.get("l") or [""])[0],
        (person.get("postalCode") or [""])[0],
        (countries.get((person.get("c") or [""])[0]) or ""),
    ]
    full_address = ", ".join(filter(None, address_parts))

    if full_address:
        try:
            # Using Nominatim for geocoding
            url = f"https://nominatim.openstreetmap.org/search?format=json&q={full_address}"
            headers = {"User-Agent": "BlackbookAddressBook/1.0"}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data:
                latitude = data[0]["lat"]
                longitude = data[0]["lon"]
        except requests.exceptions.RequestException as e:
            print(f"Could not connect to OpenStreetMap API: {e}")

    return render_template(
        "person_map.html",
        title=f"Map for {person.get('cn', ['Unknown'])[0]}",
        person=person,
        b64_dn=b64_dn,
        latitude=latitude,
        longitude=longitude,
    )


@bp.route("/person/vcard/<b64_dn>")
@login_required
def person_vcard(b64_dn):
    """Generates and returns a vCard file for a person."""
    try:
        dn = b64decode_with_padding(b64_dn)
    except (base64.binascii.Error, UnicodeDecodeError):
        abort(404)

    person_attrs = get_config("LDAP_PERSON_ATTRIBUTES")
    person = get_entry_by_dn(dn, person_attrs)
    if not person:
        abort(404)

    def get_val(attr):
        """Helper to safely get the first value of an attribute."""
        return (person.get(attr) or [""])[0]

    vcard = f"""BEGIN:VCARD
VERSION:3.0
FN:{get_val("cn")}
N:{get_val("sn")};{get_val("givenName")};;;
ORG:{get_val("o")}
EMAIL;TYPE=WORK,INTERNET:{get_val("mail")}
TEL;TYPE=WORK,VOICE:{get_val("telephoneNumber")}
ADR;TYPE=WORK:;;{get_val("street")};{get_val("l")};;{get_val("postalCode")};
END:VCARD"""

    filename = f"{get_val('cn').replace(' ', '_')}.vcf"

    return Response(
        vcard,
        mimetype="text/vcard",
        headers={"Content-disposition": f"attachment; filename={filename}"},
    )


@bp.route("/person/add", methods=["GET", "POST"])
@login_required
@editor_required
def add_person():
    """Handles creation of a new person entry."""
    all_people = cache.get("all_people") or []
    company_link_attr = get_config("LDAP_COMPANY_LINK_ATTRIBUTE")

    company_employees = {}
    for person in all_people:
        company = (person.get(company_link_attr) or [None])[0]
        if company:
            if company not in company_employees:
                company_employees[company] = []
            company_employees[company].append({"cn": person["cn"][0], "dn": person["dn"]})

    if request.method == "POST":
        attributes = {
            attr: request.form.get(attr) for attr in get_config("LDAP_PERSON_ATTRIBUTES") if request.form.get(attr)
        }

        if not attributes.get("cn"):
            flash("Full Name (cn) is a required field.", "danger")
            return redirect(url_for("main.add_person"))

        dn_template = get_config("LDAP_CONTACT_DN_TEMPLATE")
        if not dn_template:
            flash("LDAP contact DN template is not configured.", "danger")
            return redirect(url_for("main.add_person"))

        owner_attr = get_config("LDAP_OWNER_ATTRIBUTE")
        attributes[owner_attr] = str(current_user.id)

        new_uid = str(uuid.uuid4())
        attributes["uid"] = new_uid
        new_dn = dn_template.format(uid=new_uid, cn=attributes["cn"])
        object_classes = get_config("LDAP_PERSON_OBJECT_CLASS").split(",")

        if add_ldap_entry(new_dn, object_classes, attributes):
            flash("Contact added successfully! The list will refresh shortly.", "success")
            scheduler.add_job(
                func=refresh_ldap_cache,
                args=[current_app._get_current_object()],  # pylint: disable=protected-access
                id="manual_refresh_add",
                replace_existing=True,
            )
            return redirect(url_for("main.index"))

        return redirect(url_for("main.add_person"))

    return render_template(
        "add_person.html",
        title="Add New Contact",
        company_employees=company_employees,
        countries=countries,
    )


def _build_ldap_changes(form_data, current_person, person_attrs):
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


@bp.route("/person/edit/<b64_dn>", methods=["GET", "POST"])
@login_required
@editor_required
def edit_person(b64_dn):
    """Handles editing of a person entry."""
    try:
        dn = b64decode_with_padding(b64_dn)
    except (base64.binascii.Error, UnicodeDecodeError):
        abort(404)

    person_attrs = get_config("LDAP_PERSON_ATTRIBUTES")
    current_person = get_entry_by_dn(dn, person_attrs)
    if not current_person:
        abort(404)

    potential_managers = []
    company_link_attr = get_config("LDAP_COMPANY_LINK_ATTRIBUTE")
    person_company = (current_person.get(company_link_attr) or [None])[0]
    if person_company:
        all_people = cache.get("all_people") or []
        potential_managers = [
            p
            for p in all_people
            if p.get(company_link_attr) and p[company_link_attr][0] == person_company and p["dn"] != dn
        ]

    if request.method == "POST":
        changes = _build_ldap_changes(request.form, current_person, person_attrs)

        if not changes:
            flash("No changes were submitted.", "info")
        elif modify_ldap_entry(dn, changes):
            flash("Person details updated successfully! The list will refresh shortly.", "success")
            scheduler.add_job(
                func=refresh_ldap_cache,
                args=[current_app._get_current_object()],  # pylint: disable=protected-access
                id="manual_refresh_edit",
                replace_existing=True,
            )

        return redirect(url_for("main.person_detail", b64_dn=b64_dn))

    person_name = current_person.get("cn", ["Unknown"])[0]
    return render_template(
        "edit_person.html",
        title=f"Edit {person_name}",
        person=current_person,
        b64_dn=b64_dn,
        potential_managers=potential_managers,
        countries=countries,
    )


@bp.route("/person/delete/<b64_dn>", methods=["POST"])
@login_required
@editor_required
def delete_person(b64_dn):
    """Handles deletion of a person entry."""
    try:
        dn = b64decode_with_padding(b64_dn)
    except (base64.binascii.Error, UnicodeDecodeError):
        abort(404)

    if delete_ldap_contact(dn):
        flash("Contact deleted successfully! The list will refresh shortly.", "success")
        scheduler.add_job(
            func=refresh_ldap_cache,
            args=[current_app._get_current_object()],  # pylint: disable=protected-access
            id="manual_refresh_delete",
            replace_existing=True,
        )
    else:
        flash("Failed to delete contact.", "danger")

    return redirect(url_for("main.index"))


@bp.route("/avatar/<seed>.svg")
def avatar(seed):
    """Generates and returns an avatar SVG."""
    theme = get_config("AVATAR_THEME")
    svg_data = generate_avatar(seed=seed, theme=theme)
    return Response(svg_data, mimetype="image/svg+xml")


# --- Import Routes ---


@bp.route("/import/google")
@login_required
@editor_required
def import_google_contacts():
    """Renders the import options page."""
    if not get_config("ENABLE_GOOGLE_CONTACTS_IMPORT"):
        abort(404)
    return render_template("import_options.html", title="Import Options")


@bp.route("/import/google/authorize")
@login_required
@editor_required
def authorize_google_import():
    """Initiates the Google Contacts import process."""
    if not get_config("ENABLE_GOOGLE_CONTACTS_IMPORT"):
        abort(404)
    privacy = request.args.get("privacy", "public")
    session["import_privacy"] = privacy
    redirect_uri = url_for("main.google_import_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@bp.route("/import/google/callback")
@login_required
@editor_required
def google_import_callback():
    """Callback route for Google Contacts import. Redirects to the progress page."""
    if not get_config("ENABLE_GOOGLE_CONTACTS_IMPORT"):
        abort(404)

    try:
        token = oauth.google.authorize_access_token()
        session["google_import_token"] = token
    except Exception as e:
        flash(f"Authorization with Google failed: {e}", "danger")
        return redirect(url_for("main.index"))

    return redirect(url_for("main.import_status"))


@bp.route("/import/google/status")
@login_required
@editor_required
def import_status():
    """Renders the page that will show the import progress."""
    if "google_import_token" not in session:
        flash("No active import session found.", "warning")
        return redirect(url_for("main.index"))
    return render_template("import_progress.html", title="Importing Contacts")


def generate_import_stream(token, app, user_id, privacy):  # pylint: disable=too-many-locals,too-many-statements
    """A generator function that performs the import and yields progress."""
    if not token:
        payload = {"status": "error", "message": "No token found in session."}
        yield f"data: {json.dumps(payload)}\n\n"
        return

    access_token = token.get("access_token")
    headers = {"Authorization": f"Bearer {access_token}"}
    all_connections = []
    next_page_token = None

    try:
        while True:
            params = {"personFields": "names,emailAddresses,phoneNumbers,organizations,addresses", "pageSize": 1000}
            if next_page_token:
                params["pageToken"] = next_page_token

            resp = requests.get(
                "https://people.googleapis.com/v1/people/me/connections", headers=headers, params=params, timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            all_connections.extend(data.get("connections", []))
            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break
    except requests.exceptions.RequestException as e:
        payload = {"status": "error", "message": str(e)}
        yield f"data: {json.dumps(payload)}\n\n"
        return

    total_contacts = len(all_connections)
    if total_contacts == 0:
        payload = {"status": "complete", "message": "No contacts found to import."}
        yield f"data: {json.dumps(payload)}\n\n"
        return

    imported_count = 0
    skipped_count = 0
    owner_attr = app.config["LDAP_OWNER_ATTRIBUTE"]
    object_classes = app.config["LDAP_PERSON_OBJECT_CLASS"].split(",")

    if privacy == "private":
        private_ou_template = app.config["LDAP_PRIVATE_OU_TEMPLATE"]
        search_base = private_ou_template.format(user_id=user_id)
        with app.app_context():
            ensure_ou_exists(search_base)
    else:
        search_base = app.config["LDAP_CONTACTS_DN"]

    with app.app_context():
        existing_contacts = search_ldap("(objectClass=*)", ["cn", "mail"], search_base=search_base)
        existing_emails = {p["mail"][0].lower() for p in existing_contacts if p.get("mail") and p["mail"][0]}
        existing_names = {p["cn"][0].lower() for p in existing_contacts if p.get("cn") and p["cn"][0]}

    for i, person in enumerate(all_connections):
        with app.app_context():
            attributes = {}
            if person.get("names"):
                attributes["cn"] = person["names"][0].get("displayName")
                attributes["givenName"] = person["names"][0].get("givenName")
                attributes["sn"] = person["names"][0].get("familyName")
                if not attributes["sn"] and attributes["cn"]:
                    attributes["sn"] = attributes["cn"]
            if not attributes.get("cn"):
                skipped_count += 1
                payload = {
                    "status": "progress",
                    "current": i + 1,
                    "total": total_contacts,
                    "message": "Skipping contact with no name.",
                }
                yield f"data: {json.dumps(payload)}\n\n"
                continue

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

            email = (attributes.get("mail") or "").lower()
            name = (attributes.get("cn") or "").lower()
            if (email and email in existing_emails) or (name and name in existing_names):
                skipped_count += 1
                payload = {
                    "status": "progress",
                    "current": i + 1,
                    "total": total_contacts,
                    "message": f"Skipping duplicate: {name}",
                }
                yield f"data: {json.dumps(payload)}\n\n"
                continue

            attributes[owner_attr] = str(user_id)
            new_uid = str(uuid.uuid4())
            attributes["uid"] = new_uid

            rdn = f"uid={new_uid}"
            new_dn = f"{rdn},{search_base}"

            if add_ldap_entry(new_dn, object_classes, {k: v for k, v in attributes.items() if v}):
                imported_count += 1
                if email:
                    existing_emails.add(email)
                if name:
                    existing_names.add(name)
                message = f"Successfully imported: {name}"
            else:
                message = f"Failed to import: {name}"

            payload = {"status": "progress", "current": i + 1, "total": total_contacts, "message": message}
            yield f"data: {json.dumps(payload)}\n\n"

    if imported_count > 0:
        with app.app_context():
            scheduler.add_job(
                func=refresh_ldap_cache,
                args=[app],
                id="manual_refresh_import",
                replace_existing=True,
            )

    final_message = f"Import complete. Added {imported_count} new contacts and skipped {skipped_count} duplicates."
    payload = {"status": "complete", "message": final_message}
    yield f"data: {json.dumps(payload)}\n\n"


@bp.route("/import/google/stream")
@login_required
@editor_required
def import_stream():
    """The server-sent event stream for the import process."""
    token = session.pop("google_import_token", None)
    app = current_app._get_current_object()  # pylint: disable=protected-access
    privacy = session.pop("import_privacy", "public")
    return Response(generate_import_stream(token, app, current_user.id, privacy), mimetype="text/event-stream")


# --- Admin Routes ---


@bp.route("/admin/users")
@login_required
@admin_required
def admin_users():
    local_users = User.query.filter_by(auth_source="local").all()
    ldap_users = User.query.filter_by(auth_source="ldap").all()
    google_users = User.query.filter_by(auth_source="google").all()
    return render_template(
        "admin/users.html",
        title="Manage Users",
        local_users=local_users,
        ldap_users=ldap_users,
        google_users=google_users,
        current_time=datetime.now(timezone.utc),
    )


@bp.route("/admin/cache")
@login_required
@admin_required
def admin_cache():
    """Displays the status of the background caching job."""
    jobs = scheduler.get_jobs()
    return render_template("admin/cache.html", title="Cache Status", jobs=jobs)


def _add_local_user(username, email, password):
    """Helper function to add a local user."""
    if not email:
        flash("Email is required for local users.", "warning")
        return False
    if User.query.filter_by(email=email).first():
        flash("Email address already in use.", "danger")
        return False

    user = User(username=username, email=email, auth_source="local")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    flash("Local user added successfully.", "success")
    return True


def _add_ldap_user(username, password, email, given_name, surname):
    """Helper function to add an LDAP user."""
    if not all([given_name, surname, email]):
        flash("Given Name, Surname, and Email are required for LDAP users.", "warning")
        return False

    if User.query.filter_by(email=email).first():
        flash("Email address already in use by another user.", "danger")
        return False

    if add_ldap_user(username, password, email, given_name, surname):
        user = User(username=username, email=email, auth_source="ldap")
        db.session.add(user)
        db.session.commit()
        flash("LDAP user added successfully.", "success")
        return True
    return False


@bp.route("/admin/add_user", methods=["POST"])
@login_required
@admin_required
def add_user():
    auth_type = request.form.get("auth_type")
    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")

    if not all([username, password]):
        flash("Username and password are required.", "warning")
        return redirect(url_for("main.admin_users"))

    if User.query.filter_by(username=username).first():
        flash("Username already exists in the local database.", "danger")
        return redirect(url_for("main.admin_users"))

    if auth_type == "local":
        _add_local_user(username, email, password)
    elif auth_type == "ldap":
        given_name = request.form.get("given_name")
        surname = request.form.get("surname")
        _add_ldap_user(username, password, email, given_name, surname)

    return redirect(url_for("main.admin_users"))


@bp.route("/admin/delete_user/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    if user_id == 1:
        flash("Cannot delete the primary admin user.", "danger")
        return redirect(url_for("main.admin_users"))

    user = db.get_or_404(User, user_id)

    if user.auth_source == "ldap":
        if not delete_ldap_user(user.username):
            flash("Failed to delete user from LDAP. Aborting.", "danger")
            return redirect(url_for("main.admin_users"))

    db.session.delete(user)
    db.session.commit()
    flash(f"User {user.username} deleted successfully.", "success")
    return redirect(url_for("main.admin_users"))


@bp.route("/admin/force_reset/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def force_reset_password(user_id):
    user = db.get_or_404(User, user_id)

    if not user.email:
        flash(f"Cannot send reset link: User {user.username} has no email address.", "danger")
        return redirect(url_for("main.admin_users"))

    send_password_reset_email(user)
    db.session.commit()
    flash(f"A password reset link has been sent to {user.email}.", "info")
    return redirect(url_for("main.admin_users"))


@bp.route("/admin/set_roles/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def set_roles(user_id):
    if user_id == 1:
        flash("Cannot change roles for the primary admin user.", "danger")
        return redirect(url_for("main.admin_users"))

    user = db.get_or_404(User, user_id)
    user.is_admin = "is_admin" in request.form
    user.is_editor = "is_editor" in request.form
    db.session.commit()
    flash(f"Roles updated for {user.username}.", "success")
    return redirect(url_for("main.admin_users"))


@bp.route("/person/toggle_privacy/<b64_dn>", methods=["POST"])
@login_required
@editor_required
def toggle_contact_privacy(b64_dn):
    """Moves a contact between the public and the user's private OU."""
    try:
        old_dn = b64decode_with_padding(b64_dn)
    except (base64.binascii.Error, UnicodeDecodeError):
        abort(404)

    public_ou = get_config("LDAP_CONTACTS_DN")
    private_ou_template = get_config("LDAP_PRIVATE_OU_TEMPLATE")
    private_ou = private_ou_template.format(user_id=current_user.id)

    if private_ou in old_dn:
        # Move from private to public
        new_parent_dn = public_ou
    else:
        # Move from public to private
        ensure_ou_exists(private_ou)
        new_parent_dn = private_ou

    if move_ldap_entry(old_dn, new_parent_dn):
        flash("Contact privacy updated successfully. The list will refresh shortly.", "success")
        scheduler.add_job(
            func=refresh_ldap_cache,
            args=[current_app._get_current_object()],
            id=f"manual_refresh_move_{uuid.uuid4()}",
            replace_existing=False,
        )
        # Give the cache a moment to update
        time.sleep(1)
        rdn = old_dn.split(",")[0]
        new_dn = f"{rdn},{new_parent_dn}"
        return redirect(url_for("main.person_detail", b64_dn=base64.urlsafe_b64encode(new_dn.encode()).decode()))

    return redirect(url_for("main.person_detail", b64_dn=b64_dn))
