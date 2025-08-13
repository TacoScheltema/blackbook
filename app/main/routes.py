import base64
import ldap3
import math
from functools import wraps
from flask import render_template, current_app, abort, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.main import bp
from app.ldap_utils import search_ldap, get_entry_by_dn, add_ldap_entry, modify_ldap_entry
from app.models import User
from app import db, cache

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
    """
    print("CACHE MISS: Fetching all people from LDAP server...")
    person_class = get_config('LDAP_PERSON_OBJECT_CLASS')
    person_attrs = get_config('LDAP_PERSON_ATTRIBUTES')
    search_filter = f"(objectClass={person_class})"
    return search_ldap(search_filter, person_attrs)

@bp.route('/')
@login_required
def index():
    """Main index page. Now only shows a paginated list of all persons."""
    search_query = request.args.get('q', '')
    sort_by = request.args.get('sort_by', 'sn') # Default sort by Surname
    sort_order = request.args.get('sort_order', 'asc')

    page_size_options = get_config('PAGE_SIZE_OPTIONS')
    default_page_size = get_config('DEFAULT_PAGE_SIZE')

    try:
        page_size = int(request.args.get('page_size', default_page_size))
        if page_size not in page_size_options:
            page_size = default_page_size
    except ValueError:
        page_size = default_page_size

    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1

    all_people = get_all_people_cached()

    # Create a map from company name to its DN for linking from the person list
    company_class = get_config('LDAP_COMPANY_OBJECT_CLASS')
    company_filter = f'(objectClass={company_class})'
    all_companies = search_ldap(company_filter, ['o'])
    company_dn_map = {c['o'][0]: c['dn'] for c in all_companies if c.get('o') and c['o'][0]}

    if search_query:
        query = search_query.lower()
        all_people = [
            p for p in all_people 
            if p.get('cn') and query in p['cn'][0].lower()
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

    return render_template('index.html', 
                           title='Address Book', 
                           people=people_on_page,
                           search_query=search_query,
                           page=page,
                           page_size=page_size,
                           total_pages=total_pages,
                           total_people=total_people,
                           page_numbers=page_numbers,
                           company_dn_map=company_dn_map,
                           sort_by=sort_by,
                           sort_order=sort_order)

@bp.route('/companies')
@login_required
def all_companies():
    """New page to display a paginated list of all companies."""
    sort_by = request.args.get('sort_by', 'o') # Default sort by Company name
    sort_order = request.args.get('sort_order', 'asc')

    company_class = get_config('LDAP_COMPANY_OBJECT_CLASS')
    company_attrs = get_config('LDAP_COMPANY_ATTRIBUTES')
    company_filter = f'(objectClass={company_class})'
    all_companies = search_ldap(company_filter, company_attrs)

    # Sort the entire list before pagination
    if sort_by in company_attrs:
        all_companies.sort(
            key=lambda c: (c.get(sort_by)[0] if c.get(sort_by) else '').lower(),
            reverse=(sort_order == 'desc')
        )

    total_companies = len(all_companies)

    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1

    PAGE_SIZE = 20
    start_index = (page - 1) * PAGE_SIZE
    end_index = start_index + PAGE_SIZE
    companies_on_page = all_companies[start_index:end_index]
    total_pages = math.ceil(total_companies / PAGE_SIZE)

    PAGES_TO_SHOW = 6
    start_page = max(1, page - (PAGES_TO_SHOW // 2))
    end_page = min(total_pages, start_page + PAGES_TO_SHOW - 1)
    if end_page - start_page + 1 < PAGES_TO_SHOW:
        start_page = max(1, end_page - PAGES_TO_SHOW + 1)
    page_numbers = range(start_page, end_page + 1)

    return render_template('all_companies.html',
                           title='All Companies',
                           companies=companies_on_page,
                           page=page,
                           total_pages=total_pages,
                           page_numbers=page_numbers,
                           sort_by=sort_by,
                           sort_order=sort_order)


@bp.route('/company/add', methods=['GET', 'POST'])
@login_required
def add_company():
    """Handles creation of a new company entry."""
    if request.method == 'POST':
        company_name = request.form.get('company_name')
        if not company_name:
            flash('Company Name is a required field.', 'warning')
            return redirect(url_for('main.add_company'))

        base_dn = get_config('LDAP_BASE_DN')
        new_dn = f"o={company_name},{base_dn}"
        object_classes = ['top', 'organization']

        attributes = {
            'o': company_name,
            'description': request.form.get('description'),
            'street': request.form.get('street'),
            'l': request.form.get('city'),
            'st': request.form.get('state'),
            'postalCode': request.form.get('postal_code')
        }
        attributes = {k: v for k, v in attributes.items() if v}

        if add_ldap_entry(new_dn, object_classes, attributes):
            flash(f'Company "{company_name}" added successfully!', 'success')
            cache.clear() # Clear the cache after adding a company
            b64_dn = base64.urlsafe_b64encode(new_dn.encode('utf-8')).decode('utf-8')
            return redirect(url_for('main.company_detail', b64_dn=b64_dn))
        else:
            return redirect(url_for('main.add_company'))

    return render_template('add_company.html', title='Add New Company')


@bp.route('/company/<b64_dn>')
@login_required
def company_detail(b64_dn):
    """Displays details for a single company and its employees."""
    try:
        dn = base64.urlsafe_b64decode(b64_dn).decode('utf-8')
    except (base64.binascii.Error, UnicodeDecodeError):
        abort(404)

    company_attrs = get_config('LDAP_COMPANY_ATTRIBUTES')
    company = get_entry_by_dn(dn, company_attrs)
    if not company:
        abort(404)

    company_name = company.get('o', [None])[0]
    person_attrs = get_config('LDAP_PERSON_ATTRIBUTES')

    if not company_name:
        employees = []
    else:
        person_class = get_config('LDAP_PERSON_OBJECT_CLASS')
        company_link_attr = get_config('LDAP_COMPANY_LINK_ATTRIBUTE')
        employee_filter = f'(& (objectClass={person_class}) ({company_link_attr}={company_name}) )'
        employees = search_ldap(employee_filter, person_attrs, size_limit=200)

    return render_template('company_detail.html', title=company_name, company=company, employees=employees)

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
    return render_template('person_detail.html', title=person_name, person=person, b64_dn=b64_dn)

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

    company_class = get_config('LDAP_COMPANY_OBJECT_CLASS')
    company_filter = f'(objectClass={company_class})'
    companies = search_ldap(company_filter, ['o'], size_limit=200)

    person_name = current_person.get('cn', ['Unknown'])[0]
    return render_template('edit_person.html', title=f"Edit {person_name}", person=current_person, companies=companies, b64_dn=b64_dn)

# --- Admin Routes ---

@bp.route('/admin/users')
@login_required
@admin_required
def admin_users():
    if not current_app.config['ENABLE_LOCAL_LOGIN']:
        return redirect(url_for('main.index'))
    users = User.query.filter(User.auth_source == 'local').all()
    return render_template('admin/users.html', title='Manage Users', users=users)

@bp.route('/admin/add_user', methods=['POST'])
@login_required
@admin_required
def add_user():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    if User.query.filter_by(username=username).first():
        flash('Username already exists.', 'danger')
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
