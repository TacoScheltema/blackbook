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

    # Get the full list of people directly from the cache.
    # The background job is responsible for keeping this fresh.
    all_people = cache.get('all_people') or []

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

# ... (other routes remain the same) ...

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

# ... (other admin routes remain the same) ...
