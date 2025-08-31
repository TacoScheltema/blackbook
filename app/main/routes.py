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
# Version: 0.16

import base64
import math
import uuid
from datetime import datetime, timezone
from functools import wraps

import ldap3
from flask import Response, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import cache, db, scheduler
from app.email import send_password_reset_email
from app.jobs import refresh_ldap_cache
from app.ldap_utils import (
    add_ldap_entry,
    add_ldap_user,
    delete_ldap_contact,
    delete_ldap_user,
    get_entry_by_dn,
    modify_ldap_entry,
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
    all_people = cache.get("all_people") or []
    filtered_people = _filter_and_sort_people(all_people, args)

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
    all_people = cache.get("all_people") or []
    company_link_attr = get_config("LDAP_COMPANY_LINK_ATTRIBUTE")

    company_names = sorted(
        list(set(p[company_link_attr][0] for p in all_people if p.get(company_link_attr) and p[company_link_attr]))
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

    all_people = cache.get("all_people") or []
    company_link_attr = get_config("LDAP_COMPANY_LINK_ATTRIBUTE")

    employees = [p for p in all_people if p.get(company_link_attr) and p[company_link_attr][0] == company_name]
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

    all_people = cache.get("all_people") or []
    company_link_attr = get_config("LDAP_COMPANY_LINK_ATTRIBUTE")

    employees = [p for p in all_people if p.get(company_link_attr) and p[company_link_attr][0] == company_name]

    # Create a clean list of dicts for JSON serialization
    employees_for_json = []
    for employee in employees:
        avatar_url = None
        if employee.get("jpegPhoto") and employee["jpegPhoto"][0]:
            encoded_photo = base64.b64encode(employee["jpegPhoto"][0]).decode("utf-8")
            avatar_url = f"data:image/jpeg;base64,{encoded_photo}"
        elif get_config("ENABLE_GENERATED_AVATARS"):
            avatar_url = url_for("main.avatar", seed=employee["dn"])

        employees_for_json.append(
            {
                "dn": employee["dn"],
                "cn": employee.get("cn"),
                "title": employee.get("title"),
                "manager": employee.get("manager"),
                "avatar_url": avatar_url,
            }
        )

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

    all_people = cache.get("all_people") or []
    company_link_attr = get_config("LDAP_COMPANY_LINK_ATTRIBUTE")

    employees = [p for p in all_people if p.get(company_link_attr) and p[company_link_attr][0] == company_name]

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

    person_name = person.get("cn", ["Unknown"])[0]

    manager_name = None
    if "manager" in person and person["manager"]:
        manager_dn = person["manager"][0]
        manager = get_entry_by_dn(manager_dn, ["cn"])
        if manager:
            manager_name = manager.get("cn", [None])[0]

    person_for_json = person.copy()
    if "jpegPhoto" in person_for_json and person_for_json["jpegPhoto"]:
        person_for_json["jpegPhoto"] = [base64.b64encode(p).decode("utf-8") for p in person_for_json["jpegPhoto"]]

    back_params = {
        "page": request.args.get("page"),
        "page_size": request.args.get("page_size"),
        "q": request.args.get("q"),
        "sort_by": request.args.get("sort_by"),
        "sort_order": request.args.get("sort_order"),
    }
    back_params = {k: v for k, v in back_params.items() if v is not None}

    return render_template(
        "person_detail.html",
        title=person_name,
        person=person,
        person_for_json=person_for_json,
        b64_dn=b64_dn,
        back_params=back_params,
        manager_name=manager_name,
        countries=countries,
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
        changes = {}
        for attr in person_attrs:
            form_value = request.form.get(attr)

            if form_value is not None:
                attr_exists = current_person.get(attr)
                current_value = (attr_exists or [None])[0]

                if form_value and form_value != current_value:
                    changes[attr] = [(ldap3.MODIFY_REPLACE, [form_value])]
                elif not form_value and attr_exists:
                    changes[attr] = [(ldap3.MODIFY_DELETE, [])]

        if "jpegPhoto" in request.form and request.form["jpegPhoto"]:
            photo_data = base64.b64decode(request.form["jpegPhoto"])
            changes["jpegPhoto"] = [(ldap3.MODIFY_REPLACE, [photo_data])]

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


# --- Admin Routes ---


@bp.route("/admin/users")
@login_required
@admin_required
def admin_users():
    local_users = User.query.filter(User.auth_source == "local").all()
    ldap_users = User.query.filter(User.auth_source == "ldap").all()
    return render_template(
        "admin/users.html",
        title="Manage Users",
        local_users=local_users,
        ldap_users=ldap_users,
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
