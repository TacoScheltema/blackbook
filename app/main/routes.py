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
# Version: 0.38

import base64
import time
import uuid
from datetime import datetime, timezone

import vobject
import requests
from authlib.integrations.base_client.errors import OAuthError
from flask import Response, abort, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from requests.exceptions import RequestException

from app import oauth, scheduler
from app.ldap_utils import (
    add_ldap_entry,
    delete_ldap_contact,
    ensure_ou_exists,
    get_entry_by_dn,
    modify_ldap_entry,
    move_ldap_entry,
)
from app.main import bp
from app.main.avatar_generator import generate_avatar
from app.main.countries import countries
from app.main.helpers import (
    build_ldap_changes,
    editor_required,
    filter_and_sort_people,
    generate_import_stream,
    get_config,
    get_index_request_args,
    get_pagination_params,
    get_visible_contacts,
    refresh_ldap_cache,
)


@bp.route("/")
@login_required
def index():
    """Main index page. Now only shows a paginated list of all persons."""
    args = get_index_request_args()
    all_visible_contacts = get_visible_contacts()
    filtered_people = filter_and_sort_people(all_visible_contacts, args)
    print(f"------\nIs admin: {current_user.is_admin}\n------")
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
        current_user=current_user,
    )


@bp.route("/companies")
@login_required
def all_companies():
    """Displays a list of unique company names derived from the contacts."""
    args = get_index_request_args()
    all_visible_contacts = get_visible_contacts()
    company_link_attr = current_app.config["LDAP_COMPANY_LINK_ATTRIBUTE"]

    company_names = sorted(
        list(
            set(
                p[company_link_attr][0]
                for p in all_visible_contacts
                if p.get(company_link_attr) and p[company_link_attr]
            )
        )
    )

    if args["letter"]:
        company_names = [name for name in company_names if name.upper().startswith(args["letter"])]

    total_companies = len(company_names)
    start_index = (args["page"] - 1) * 20
    end_index = start_index + 20
    companies_on_page = company_names[start_index:end_index]

    page_numbers, total_pages = get_pagination_params(total_companies, args["page"], 20)
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    return render_template(
        "all_companies.html",
        title="All Companies",
        companies=companies_on_page,
        page=args["page"],
        total_pages=total_pages,
        page_numbers=page_numbers,
        alphabet=alphabet,
        letter=args["letter"],
    )


@bp.route("/company/<b64_company_name>")
@login_required
def company_detail(b64_company_name):
    """Displays a list of people belonging to a specific company."""
    company_name = base64.urlsafe_b64decode(b64_company_name).decode()
    all_visible_contacts = get_visible_contacts()
    company_link_attr = current_app.config["LDAP_COMPANY_LINK_ATTRIBUTE"]

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
    company_name = base64.urlsafe_b64decode(b64_company_name).decode()
    all_visible_contacts = get_visible_contacts()
    company_link_attr = current_app.config["LDAP_COMPANY_LINK_ATTRIBUTE"]

    employees = [
        p for p in all_visible_contacts if p.get(company_link_attr) and p[company_link_attr][0] == company_name
    ]

    employees_for_json = []
    for employee in employees:
        avatar_url = None
        if "jpegPhoto" in employee and employee["jpegPhoto"] and employee["jpegPhoto"][0]:
            photo_data = base64.b64encode(employee["jpegPhoto"][0]).decode("utf-8")
            avatar_url = f"data:image/jpeg;base64,{photo_data}"
        elif current_app.config["ENABLE_GENERATED_AVATARS"]:
            avatar_url = url_for("main.avatar", seed=employee["dn"], _external=True)

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
    company_name = base64.urlsafe_b64decode(b64_company_name).decode()
    all_visible_contacts = get_visible_contacts()
    company_link_attr = current_app.config["LDAP_COMPANY_LINK_ATTRIBUTE"]

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
    dn = base64.urlsafe_b64decode(b64_dn).decode()
    person_attrs = current_app.config["LDAP_PERSON_ATTRIBUTES"]
    person = get_entry_by_dn(dn, person_attrs)
    if not person:
        abort(404)

    if "jpegPhoto" in person and person["jpegPhoto"] and person["jpegPhoto"][0]:
        person["jpegPhoto"][0] = base64.b64encode(person["jpegPhoto"][0]).decode("utf-8")

    person_name = person.get("cn", ["Unknown"])[0]

    manager_name = None
    if "manager" in person and person["manager"]:
        manager = get_entry_by_dn(person["manager"][0], ["cn"])
        if manager:
            manager_name = manager.get("cn", [None])[0]

    person_for_json = person.copy()

    back_params = {k: v for k, v in request.args.items() if v is not None}

    private_ou_template = current_app.config["LDAP_PRIVATE_OU_TEMPLATE"]
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
    dn = base64.urlsafe_b64decode(b64_dn).decode()
    person = get_entry_by_dn(dn, ["cn", "street", "l", "postalCode", "c"])
    if not person:
        abort(404)

    latitude, longitude = None, None
    address_parts = [(person.get(k) or [""])[0] for k in ["street", "l", "postalCode", "c"]]
    full_address = ", ".join(filter(None, address_parts))

    if full_address:
        try:
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
    dn = base64.urlsafe_b64decode(b64_dn).decode()
    person = get_entry_by_dn(dn, current_app.config["LDAP_PERSON_ATTRIBUTES"])
    if not person:
        abort(404)

    def get_val(attr):
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
    return Response(vcard, mimetype="text/vcard", headers={"Content-disposition": f"attachment; filename={filename}"})


@bp.route("/person/add", methods=["GET", "POST"])
@login_required
@editor_required
def add_person():
    """Handles creation of a new person entry."""
    all_people = get_visible_contacts() or []
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
            attr: request.form.get(attr)
            for attr in current_app.config["LDAP_PERSON_ATTRIBUTES"]
            if request.form.get(attr)
        }
        if not attributes.get("cn"):
            flash("Full Name (cn) is a required field.", "danger")
            return redirect(url_for("main.add_person"))

        attributes[current_app.config["LDAP_OWNER_ATTRIBUTE"]] = str(current_user.id)
        attributes["uid"] = str(uuid.uuid4())
        new_dn = current_app.config["LDAP_CONTACT_DN_TEMPLATE"].format(uid=attributes["uid"], cn=attributes["cn"])
        object_classes = current_app.config["LDAP_PERSON_OBJECT_CLASS"].split(",")

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
        "add_person.html", title="Add New Contact", company_employees=company_employees, countries=countries
    )


@bp.route("/person/edit/<b64_dn>", methods=["GET", "POST"])
@login_required
@editor_required
def edit_person(b64_dn):
    """Handles editing of a person entry."""
    dn = base64.urlsafe_b64decode(b64_dn).decode()
    person_attrs = current_app.config["LDAP_PERSON_ATTRIBUTES"]
    current_person = get_entry_by_dn(dn, person_attrs)
    if not current_person:
        abort(404)

    potential_managers = []
    company_link_attr = get_config("LDAP_COMPANY_LINK_ATTRIBUTE")
    person_company = (current_person.get(company_link_attr) or [None])[0]
    if person_company:
        all_people = get_visible_contacts() or []
        potential_managers = [
            p
            for p in all_people
            if p.get(company_link_attr) and p[company_link_attr][0] == person_company and p["dn"] != dn
        ]

    if request.method == "POST":
        changes = build_ldap_changes(request.form, current_person, person_attrs)
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
        potential_managers=potential_managers,
        b64_dn=b64_dn,
        countries=countries,
    )


@bp.route("/person/delete/<b64_dn>", methods=["POST"])
@login_required
@editor_required
def delete_person(b64_dn):
    """Handles deletion of a person entry."""
    dn = base64.urlsafe_b64decode(b64_dn).decode()
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
    return Response(generate_avatar(seed=seed, theme=current_app.config["AVATAR_THEME"]), mimetype="image/svg+xml")


@bp.route("/import/google")
@login_required
@editor_required
def import_google_contacts():
    """Renders the import options page."""
    return render_template("import_options.html", title="Import Options")


@bp.route("/import/google/authorize")
@login_required
@editor_required
def authorize_google_import():
    """Initiates the Google Contacts import process."""
    session["import_privacy"] = request.args.get("privacy", "public")
    redirect_uri = url_for("main.google_import_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@bp.route("/import/google/callback")
@login_required
@editor_required
def google_import_callback():
    """Callback route for Google Contacts import."""
    try:
        session["google_import_token"] = oauth.google.authorize_access_token()
    except OAuthError as e:
        # This catches errors specific to the OAuth2 flow,
        # like an invalid grant or the user denying permission.
        flash(f"Authorization error with Google: {e.description}", "danger")
        return redirect(url_for("main.index"))
    except RequestException as e:
        # This catches network-related errors, like a timeout or DNS failure.
        flash(f"Could not connect to Google's servers. Please try again later. Error: {e}", "danger")
        return redirect(url_for("main.index"))

    return redirect(url_for("main.import_status"))


@bp.route("/import/google/status")
@login_required
@editor_required
def import_status():
    """Renders the page that will show the import progress."""
    return render_template("import_progress.html", title="Importing Contacts")


@bp.route("/import/google/stream")
@login_required
@editor_required
def import_stream():
    """The server-sent event stream for the import process."""
    token = session.pop("google_import_token", None)
    app = current_app._get_current_object()  # pylint: disable=protected-access
    privacy = session.pop("import_privacy", "public")
    return Response(generate_import_stream(token, app, current_user.id, privacy), mimetype="text/event-stream")


@bp.route("/import/vcard", methods=["GET", "POST"])
@login_required
@editor_required
def import_vcard():
    """Handles the vCard file upload and import process."""
    if request.method == "POST":
        if "vcard_file" not in request.files:
            flash("No file part", "warning")
            return redirect(request.url)
        file = request.files["vcard_file"]
        if file.filename == "":
            flash("No selected file", "warning")
            return redirect(request.url)
        if file and file.filename.endswith(".vcf"):
            privacy = request.form.get("privacy", "public")
            content = file.read().decode("utf-8")
            # Process the vCard content here
            flash(f"vCard file uploaded. Privacy: {privacy}", "success")
            return redirect(url_for("main.index"))

    return render_template("import_vcard.html", title="Import from vCard")


@bp.route("/person/toggle_privacy/<b64_dn>", methods=["POST"])
@login_required
@editor_required
def toggle_contact_privacy(b64_dn):
    """Moves a contact between public and private OUs."""
    old_dn = base64.urlsafe_b64decode(b64_dn).decode()
    public_ou = current_app.config["LDAP_CONTACTS_DN"]
    private_ou = current_app.config["LDAP_PRIVATE_OU_TEMPLATE"].format(user_id=current_user.id)

    new_parent_dn = public_ou if private_ou in old_dn else private_ou
    if new_parent_dn == private_ou:
        ensure_ou_exists(private_ou)

    if move_ldap_entry(old_dn, new_parent_dn):
        flash("Contact privacy updated. The list will refresh shortly.", "success")
        scheduler.add_job(
            func=refresh_ldap_cache,
            args=[current_app._get_current_object()],  # pylint: disable=protected-access
            id=f"manual_refresh_move_{uuid.uuid4()}",
            replace_existing=False,
        )
        time.sleep(1)
        rdn = old_dn.split(",")[0]
        new_dn = f"{rdn},{new_parent_dn}"
        return redirect(url_for("main.person_detail", b64_dn=base64.urlsafe_b64encode(new_dn.encode()).decode()))
    return redirect(url_for("main.person_detail", b64_dn=b64_dn))
