# app/main/routes.py
import base64
from flask import render_template, current_app, abort
from app.main import bp
from app.ldap_utils import search_ldap, get_entry_by_dn

# Define attributes to fetch for people and companies
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

    # Search for all companies
    company_filter = f'(objectClass={company_class})'
    companies = search_ldap(company_filter, COMPANY_ATTRS)

    # Search for all people who do NOT have the company link attribute
    # This finds people not linked to any company.
    people_filter = f'(& (objectClass={person_class}) (!({company_link_attr}=*)) )'
    people = search_ldap(people_filter, PERSON_ATTRS)
    
    return render_template('index.html', title='Address Book', companies=companies, people=people)

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

    # The company name is usually in the 'o' attribute.
    # We need the first value from the list.
    company_name = company.get('o', [None])[0]
    if not company_name:
        employees = []
    else:
        # Find all people where their company link attribute matches the company name
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
    return render_template('person_detail.html', title=person_name, person=person)


