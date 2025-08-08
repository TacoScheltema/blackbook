import base64
import ldap3
import math
from flask import render_template, current_app, abort, request, flash, redirect, url_for
from app.main import bp
from app.ldap_utils import search_ldap, get_entry_by_dn, add_ldap_entry, modify_ldap_entry
# Import the cache object we created in app/__init__.py
from app import cache

COMPANY_ATTRS = ['o', 'description', 'street', 'l', 'st', 'postalCode']

def get_config(key):
    """Helper to safely get config values."""
    return current_app.config.get(key, '')

@cache.memoize()
def get_all_people_cached():
    """
    A cached function to get all people from LDAP.
    This function's result will be stored in the cache. The cache key is
    the function name. It will only be re-run when the cache times out.
    """
    print("CACHE MISS: Fetching all people from LDAP server...")
    person_class = get_config('LDAP_PERSON_OBJECT_CLASS')
    person_attrs = get_config('LDAP_PERSON_ATTRIBUTES')
    search_filter = f"(objectClass={person_class})"
    return search_ldap(search_filter, person_attrs)

def _get_int_arg(name, default_value):
    """
    A robust helper function to safely get an integer from request arguments.
    It handles missing keys, empty values, and non-numeric values by
    returning a safe default.
    """
    try:
        return int(request.args.get(name, default_value))
    except (ValueError, TypeError):
        return default_value

@bp.route('/')
def index():
    """Main index page. Lists all companies and a paginated list of all persons."""
    # --- Companies List (reverted to non-paginated) ---
    company_class = get_config('LDAP_COMPANY_OBJECT_CLASS')
    company_filter = f'(objectClass={company_class})'
    companies = search_ldap(company_filter, ['o'], size_limit=200)

    # --- Persons List (with caching and configurable pagination) ---
    search_query = request.args.get('q', '')
    
    page_size_options = get_config('PAGE_SIZE_OPTIONS')
    default_page_size = get_config('DEFAULT_PAGE_SIZE')

    page_size = _get_int_arg('page_size', default_page_size)
    if page_size not in page_size_options:
        page_size = default_page_size
        
    page = _get_int_arg('page', 1)

    all_people = get_all_people_cached()

    if search_query:
        query = search_query.lower()
        all_people = [
            p for p in all_people 
            if p.get('cn') and p['cn'] and query in p['cn'][0].lower()
        ]

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
                           companies=companies, 
                           people=people_on_page,
                           search_query=search_query,
                           page=page,
                           page_size=page_size,
                           total_pages=total_pages,
                           total_people=total_people,
                           page_numbers=page_numbers)


@bp.route('/company/add', methods=['GET', 'POST'])
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
def company_detail(b64_dn):
    """Displays details for a single company and its employees."""
    try:
        dn = base64.urlsafe_b64decode(b64_dn).decode('utf-8')
    except (base64.binascii.Error, UnicodeDecodeError):
        abort(404)

    company = get_entry_by_dn(dn, COMPANY_ATTRS)
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

