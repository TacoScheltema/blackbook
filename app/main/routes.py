import base64
import ldap3
from flask import render_template, current_app, abort, request, flash, redirect, url_for
from app.main import bp
from app.ldap_utils import search_ldap, get_entry_by_dn, add_ldap_entry, modify_ldap_entry

## Removed hardcoded PERSON_ATTRS list. It will now be read from config.
COMPANY_ATTRS = ['o', 'description', 'street', 'l', 'st', 'postalCode']
PAGE_SIZE = 25

def get_config(key):
    """Helper to safely get config values."""
    return current_app.config.get(key, '')

@bp.route('/')
def index():
    """Main index page. Lists all companies and a paginated list of all persons."""
    company_class = get_config('LDAP_COMPANY_OBJECT_CLASS')
    company_filter = f'(objectClass={company_class})'
    companies, _ = search_ldap(company_filter, ['o'], paged_size=200)

    search_query = request.args.get('q', '')
    encoded_cookie = request.args.get('cookie')
    paged_cookie_bytes = None
    if encoded_cookie:
        try:
            paged_cookie_bytes = base64.urlsafe_b64decode(encoded_cookie)
        except (base64.binascii.Error, UnicodeDecodeError):
            flash('Invalid pagination data received.', 'warning')
            return redirect(url_for('main.index'))

    person_class = get_config('LDAP_PERSON_OBJECT_CLASS')
    person_attrs = get_config('LDAP_PERSON_ATTRIBUTES') # Get attributes from config

    if search_query:
        search_filter = f"(&(objectClass={person_class})(|(cn=*{search_query}*)(sn=*{search_query}*)(givenName=*{search_query}*)))"
    else:
        search_filter = f"(objectClass={person_class})"

    people, next_cookie_bytes = search_ldap(search_filter, person_attrs, paged_size=PAGE_SIZE, paged_cookie=paged_cookie_bytes)

    next_encoded_cookie = None
    if next_cookie_bytes:
        next_encoded_cookie = base64.urlsafe_b64encode(next_cookie_bytes).decode('utf-8')

    return render_template('index.html', 
                           title='Address Book', 
                           companies=companies, 
                           people=people,
                           search_query=search_query,
                           next_cookie=next_encoded_cookie,
                           cookie=encoded_cookie)


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
    person_attrs = get_config('LDAP_PERSON_ATTRIBUTES') # Get attributes from config

    if not company_name:
        employees = []
    else:
        person_class = get_config('LDAP_PERSON_OBJECT_CLASS')
        company_link_attr = get_config('LDAP_COMPANY_LINK_ATTRIBUTE')
        employee_filter = f'(& (objectClass={person_class}) ({company_link_attr}={company_name}) )'
        employees, _ = search_ldap(employee_filter, person_attrs, paged_size=200)

    return render_template('company_detail.html', title=company_name, company=company, employees=employees)

@bp.route('/person/<b64_dn>')
def person_detail(b64_dn):
    """Displays details for a single person."""
    try:
        dn = base64.urlsafe_b64decode(b64_dn).decode('utf-8')
    except (base64.binascii.Error, UnicodeDecodeError):
        abort(404)

    person_attrs = get_config('LDAP_PERSON_ATTRIBUTES') # Get attributes from config
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

    person_attrs = get_config('LDAP_PERSON_ATTRIBUTES') # Get attributes from config
    current_person = get_entry_by_dn(dn, person_attrs)
    if not current_person:
        abort(404)

    if request.method == 'POST':
        changes = {}
        # Iterate through the attributes defined in the config to build the changes
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

        return redirect(url_for('main.person_detail', b64_dn=b64_dn))

    company_class = get_config('LDAP_COMPANY_OBJECT_CLASS')
    company_filter = f'(objectClass={company_class})'
    companies, _ = search_ldap(company_filter, ['o'], paged_size=200)

    person_name = current_person.get('cn', ['Unknown'])[0]
    return render_template('edit_person.html', title=f"Edit {person_name}", person=current_person, companies=companies, b64_dn=b64_dn)



