import base64
import ldap3
from flask import render_template, current_app, abort, request, flash, redirect, url_for
from app.main import bp
from app.ldap_utils import search_ldap, get_entry_by_dn, add_ldap_entry, modify_ldap_entry

PERSON_ATTRS = ['cn', 'sn', 'givenName', 'mail', 'telephoneNumber', 'o']
COMPANY_ATTRS = ['o', 'description', 'street', 'l', 'st', 'postalCode']

def get_config(key):
    """Helper to safely get config values."""
    return current_app.config.get(key, '')

@bp.route('/')
def index():
    """Main index page. Lists all companies and unassociated individuals."""
    company_class = get_config('LDAP_COMPANY_OBJECT_CLASS')
    person_class = get_config('LDAP_PERSON_OBJECT_CLASS')
    company_link_attr = get_config('LDAP_COMPANY_LINK_ATTRIBUTE')

    company_filter = f'(objectClass={company_class})'
    companies = search_ldap(company_filter, ['o']) # Only need names for the list

    people_filter = f'(& (objectClass={person_class}) (!({company_link_attr}=*)) )'
    people = search_ldap(people_filter, PERSON_ATTRS)
    
    return render_template('index.html', title='Address Book', companies=companies, people=people)

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
    if not company_name:
        employees = []
    else:
        person_class = get_config('LDAP_PERSON_OBJECT_CLASS')
        company_link_attr = get_config('LDAP_COMPANY_LINK_ATTRIBUTE')
        employee_filter = f'(& (objectClass={person_class}) ({company_link_attr}={company_name}) )'
        employees = search_ldap(employee_filter, PERSON_ATTRS)

    return render_template('company_detail.html', title=company_name, company=company, employees=employees)

@bp.route('/person/<b64_dn>')
def person_detail(b64_dn):
    """Displays details for a single person."""
    try:
        dn = base64.urlsafe_b64decode(b64_dn).decode('utf-8')
    except (base64.binascii.Error, UnicodeDecodeError):
        abort(404)
        
    person = get_entry_by_dn(dn, PERSON_ATTRS)
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

    if request.method == 'POST':
        changes = {}
        form_data = {
            'cn': request.form.get('cn'),
            'sn': request.form.get('sn'),
            'givenName': request.form.get('givenName'),
            'mail': request.form.get('mail'),
            'telephoneNumber': request.form.get('telephoneNumber'),
            'o': request.form.get('company')
        }

        for attr, value in form_data.items():
            # If the value is empty, we delete the attribute.
            # Otherwise, we replace it.
            if not value:
                changes[attr] = [(ldap3.MODIFY_DELETE, [])]
            else:
                changes[attr] = [(ldap3.MODIFY_REPLACE, [value])]
        
        if modify_ldap_entry(dn, changes):
            flash('Person details updated successfully!', 'success')
        else:
            flash('Failed to update person details.', 'danger')
        
        return redirect(url_for('main.person_detail', b64_dn=b64_dn))

    # For GET request
    person = get_entry_by_dn(dn, PERSON_ATTRS)
    if not person:
        abort(404)

    # Get all companies for the dropdown
    company_class = get_config('LDAP_COMPANY_OBJECT_CLASS')
    company_filter = f'(objectClass={company_class})'
    companies = search_ldap(company_filter, ['o'])

    person_name = person.get('cn', ['Unknown'])[0]
    return render_template('edit_person.html', title=f"Edit {person_name}", person=person, companies=companies, b64_dn=b64_dn)
