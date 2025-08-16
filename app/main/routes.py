import base64
import ldap3
import math
from functools import wraps
from flask import Response, render_template, current_app, abort, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.main import bp
from app.ldap_utils import search_ldap, get_entry_by_dn, add_ldap_entry, modify_ldap_entry
from app.models import User
from app import db, cache, scheduler

def get_config(key):
    """Helper to safely get config values."""
    return current_app.config.get(key, '')

def admin_required(f):
    """Decorator to restrict access to admin users."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.id != 1:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@cache.memoize()
def get_all_people_cached():
    """
    A cached function to get all people from LDAP.
    This will use the ADDRESSBOOK_FILTER from the .env file if it is set.
    """
    print("CACHE MISS: Fetching all people from LDAP server...")
    person_class = get_config('LDAP_PERSON_OBJECT_CLASS')
    person_attrs = get_config('LDAP_PERSON_ATTRIBUTES')
    search_filter = f"(objectClass={person_class})"
    # Use the specific contacts DN from the config for the search base
    contacts_dn = get_config('LDAP_CONTACTS_DN')
    return search_ldap(search_filter, person_attrs, search_base=contacts_dn)

@bp.route('/')
@login_required
def index():
    """Main index page. Now only shows a paginated list of all persons."""
    search_query = request.args.get('q', '')
    sort_by = request.args.get('sort_by', 'sn') # Default sort by Surname
    sort_order = request.args.get('sort_order', 'asc')
    letter = request.args.get('letter', '')

    page_size_options = get_config('PAGE_SIZE_OPTIONS')
    default_page_size = get_config('DEFAULT_PAGE_SIZE')

    # Get page size from request args first.
    page_size_from_request = request.args.get('page_size', type=int)

    if page_size_from_request and page_size_from_request in page_size_options:
        page_size = page_size_from_request
        # If the user's choice is different from what's stored, update it.
        if current_user.page_size != page_size:
            current_user.page_size = page_size
            db.session.commit()
    else:
        # If no valid page size in request, use the one stored for the user.
        page_size = current_user.page_size

    # If, after all that, page_size is still None (e.g., for a pre-existing user),
    # fall back to the application default to prevent errors.
    if page_size is None:
        page_size = default_page_size

    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1

    all_people = get_all_people_cached()

    if search_query:
        query = search_query.lower()
        all_people = [
            p for p in all_people 
            if p.get('cn') and query in p['cn'][0].lower()
        ]

    if letter:
        all_people = [
            p for p in all_people
            if p.get('sn') and p['sn'][0].upper().startswith(letter)
        ]

    # Sort the entire list before pagination
    if sort_by in get_config('LDAP_PERSON_ATTRIBUTES'):
        all_people.sort(
            key=lambda p: (p.get(sort_by)[0] if p.get(sort_by) else '').lower(),
            reverse=(sort_order == 'desc')
        )

    total_people = len(all_people)

    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    people_on_page = all_people[start_index:end_index]

    total_pages = math.ceil(total_people / page_size)

    PAGES_TO_SHOW = 6
    start_page = max(1, page - (PAGES_TO_SHOW // 2))
    end_page = min(total_pages, start_page + PAGES_TO_SHOW - 1)

    if end_page - start_page + 1 < PAGES_TO_SHOW:
        start_page = max(1, end_page - PAGES_TO_SHOW + 1)

    page_numbers = range(start_page, end_page + 1)
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    return render_template('index.html', 
                           title='Address Book', 
                           people=people_on_page,
                           search_query=search_query,
                           page=page,
                           page_size=page_size,
                           total_pages=total_pages,
                           total_people=total_people,
                           page_numbers=page_numbers,
                           sort_by=sort_by,
                           sort_order=sort_order,
                           alphabet=alphabet,
                           letter=letter)

@bp.route('/companies')
@login_required
def all_companies():
    """Displays a list of unique company names derived from the contacts."""
    letter = request.args.get('letter', '')
    all_people = cache.get('all_people') or []
    company_link_attr = get_config('LDAP_COMPANY_LINK_ATTRIBUTE')

    # Create a unique, sorted list of company names
    company_names = sorted(list(set(
        p[company_link_attr][0] for p in all_people if p.get(company_link_attr) and p[company_link_attr]
    )))

    if letter:
        company_names = [name for name in company_names if name.upper().startswith(letter)]

    total_companies = len(company_names)

    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1

    PAGE_SIZE = 20
    start_index = (page - 1) * PAGE_SIZE
    end_index = start_index + PAGE_SIZE
    companies_on_page = company_names[start_index:end_index]
    total_pages = math.ceil(total_companies / PAGE_SIZE)

    PAGES_TO_SHOW = 6
    start_page = max(1, page - (PAGES_TO_SHOW // 2))
    end_page = min(total_pages, start_page + PAGES_TO_SHOW - 1)
    if end_page - start_page + 1 < PAGES_TO_SHOW:
        start_page = max(1, end_page - PAGES_TO_SHOW + 1)
    page_numbers = range(start_page, end_page + 1)
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    return render_template('all_companies.html',
                           title='All Companies',
                           companies=companies_on_page,
                           page=page,
                           total_pages=total_pages,
                           page_numbers=page_numbers,
                           alphabet=alphabet,
                           letter=letter)


@bp.route('/company/<b64_company_name>')
@login_required
def company_detail(b64_company_name):
    """Displays a list of people belonging to a specific company."""
    try:
        company_name = base64.urlsafe_b64decode(b64_company_name).decode('utf-8')
    except (base64.binascii.Error, UnicodeDecodeError):
        abort(404)

    all_people = cache.get('all_people') or []
    company_link_attr = get_config('LDAP_COMPANY_LINK_ATTRIBUTE')

    employees = [
        p for p in all_people 
        if p.get(company_link_attr) and p[company_link_attr][0] == company_name
    ]

    return render_template('company_detail.html', 
                           title=f"Company: {company_name}", 
                           company_name=company_name,
                           employees=employees)

@bp.route('/person/<b64_dn>')
@login_required
def person_detail(b64_dn):
    """Displays details for a single person."""
    try:
        dn = base64.urlsafe_b64decode(b64_dn).decode('utf-8')
    except (base64.binascii.Error, UnicodeDecodeError):
        abort(404)

    person_attrs = get_config('LDAP_PERSON_ATTRIBUTES')
    person = get_entry_by_dn(dn, person_attrs)
    if not person:
        abort(404)

    person_name = person.get('cn', ['Unknown'])[0]

    # Capture all relevant query params to pass them back for the "back" button
    back_params = {
        'page': request.args.get('page'),
        'page_size': request.args.get('page_size'),
        'q': request.args.get('q'),
        'sort_by': request.args.get('sort_by'),
        'sort_order': request.args.get('sort_order')
    }
    back_params = {k: v for k, v in back_params.items() if v is not None}

    return render_template('person_detail.html', 
                           title=person_name, 
                           person=person, 
                           b64_dn=b64_dn,
                           back_params=back_params)

@bp.route('/person/vcard/<b64_dn>')
@login_required
def person_vcard(b64_dn):
    """Generates and returns a vCard file for a person."""
    try:
        dn = base64.urlsafe_b64decode(b64_dn).decode('utf-8')
    except (base64.binascii.Error, UnicodeDecodeError):
        abort(404)

    person_attrs = get_config('LDAP_PERSON_ATTRIBUTES')
    person = get_entry_by_dn(dn, person_attrs)
    if not person:
        abort(404)

    # Helper to safely get the first value of an attribute
    get_val = lambda attr: (person.get(attr) or [''])[0]

    vcard = f"""BEGIN:VCARD
VERSION:3.0
FN:{get_val('cn')}
N:{get_val('sn')};{get_val('givenName')};;;
ORG:{get_val('o')}
EMAIL;TYPE=WORK,INTERNET:{get_val('mail')}
TEL;TYPE=WORK,VOICE:{get_val('telephoneNumber')}
ADR;TYPE=WORK:;;{get_val('street')};{get_val('l')};;{get_val('postalCode')};
END:VCARD"""

    filename = f"{get_val('cn').replace(' ', '_')}.vcf"

    return Response(
        vcard,
        mimetype="text/vcard",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )

@bp.route('/person/edit/<b64_dn>', methods=['GET', 'POST'])
@login_required
def edit_person(b64_dn):
    """Handles editing of a person entry."""
    try:
        dn = base64.urlsafe_b64decode(b64_dn).decode('utf-8')
    except (base64.binascii.Error, UnicodeDecodeError):
        abort(404)

    person_attrs = get_config('LDAP_PERSON_ATTRIBUTES')
    current_person = get_entry_by_dn(dn, person_attrs)
    if not current_person:
        abort(404)

    if request.method == 'POST':
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

        if not changes:
            flash('No changes were submitted.', 'info')
        elif modify_ldap_entry(dn, changes):
            flash('Person details updated successfully!', 'success')
            cache.clear() # Clear the cache after a successful modification

        return redirect(url_for('main.person_detail', b64_dn=b64_dn))

    return render_template('edit_person.html', title=f"Edit {person_name}", person=current_person, b64_dn=b64_dn)

# --- Admin Routes ---

@bp.route('/admin/users')
@login_required
@admin_required
def admin_users():
    if not current_app.config['ENABLE_LOCAL_LOGIN']:
        return redirect(url_for('main.index'))
    users = User.query.filter(User.auth_source == 'local').all()
    return render_template('admin/users.html', title='Manage Users', users=users)

@bp.route('/admin/cache')
@login_required
@admin_required
def admin_cache():
    """Displays the status of the background caching job."""
    jobs = scheduler.get_jobs()
    return render_template('admin/cache.html', title='Cache Status', jobs=jobs)

@bp.route('/admin/add_user', methods=['POST'])
@login_required
@admin_required
def add_user():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')

    if not all([username, email, password]):
        flash('All fields are required.', 'warning')
        return redirect(url_for('main.admin_users'))

    if User.query.filter_by(username=username).first():
        flash('Username already exists.', 'danger')
    elif User.query.filter_by(email=email).first():
        flash('Email address already in use.', 'danger')
    else:
        user = User(username=username, email=email, auth_source='local')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('User added successfully.', 'success')
    return redirect(url_for('main.admin_users'))

@bp.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    if user_id == 1: # Prevent deleting admin
        flash('Cannot delete the primary admin user.', 'danger')
        return redirect(url_for('main.admin_users'))
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully.', 'success')
    return redirect(url_for('main.admin_users'))

@bp.route('/admin/force_reset/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def force_reset_password(user_id):
    user = User.query.get_or_404(user_id)
    user.password_reset_required = True
    db.session.commit()
    flash(f'Password reset has been forced for {user.username}.', 'info')
    return redirect(url_for('main.admin_users'))
