from flask import render_template, flash, redirect, url_for, request, current_app
from flask_login import login_user, logout_user, current_user, login_required
from urllib.parse import urlparse
from app import db, oauth
from app.auth import bp
from app.models import User
from app.ldap_utils import authenticate_ldap_user

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        auth_type = request.form.get('auth_type')
        username = request.form.get('username')
        password = request.form.get('password')

        # Check if the selected login method is disabled
        if auth_type == 'local' and not current_app.config['ENABLE_LOCAL_LOGIN']:
            flash('Local login is disabled.', 'warning')
            return redirect(url_for('auth.login'))
        if auth_type == 'ldap' and not current_app.config['ENABLE_LDAP_LOGIN']:
            flash('LDAP login is disabled.', 'warning')
            return redirect(url_for('auth.login'))

        user = None

        if auth_type == 'local':
            user = User.query.filter_by(username=username).first()
            if user is None or not user.check_password(password):
                flash('Invalid username or password for local account', 'danger')
                return redirect(url_for('auth.login'))

        elif auth_type == 'ldap':
            if authenticate_ldap_user(username, password):
                user = User.query.filter_by(username=username, auth_source='ldap').first()
                if not user:
                    user = User(username=username, auth_source='ldap')
                    db.session.add(user)
                    db.session.commit()
            else:
                flash('Invalid username or password for LDAP account', 'danger')
                return redirect(url_for('auth.login'))

        if user:
            login_user(user, remember=True)
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('main.index')
            return redirect(next_page)

    return render_template('auth/login.html', title='Sign In')

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/reset-password', methods=['GET', 'POST'])
@login_required
def reset_password():
    if not current_user.password_reset_required:
        # Don't allow access if a reset is not required
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        password = request.form.get('password')
        password2 = request.form.get('password2')

        if not password or password != password2:
            flash('Passwords do not match or are empty.', 'warning')
            return redirect(url_for('auth.reset_password'))

        current_user.set_password(password)
        current_user.password_reset_required = False
        db.session.commit()
        flash('Your password has been reset successfully.', 'success')
        return redirect(url_for('main.index'))

    return render_template('auth/reset_password.html', title='Reset Password')


# --- SSO Login Routes ---

@bp.route('/login/<provider>')
def sso_login(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))
    redirect_uri = url_for('auth.authorize', provider=provider, _external=True)
    return oauth.create_client(provider).authorize_redirect(redirect_uri)

@bp.route('/authorize/<provider>')
def authorize(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))

    client = oauth.create_client(provider)
    token = client.authorize_access_token()
    user_info = token.get('userinfo')

    if user_info:
        sso_user_id = user_info['sub']
        user = User.query.filter_by(username=sso_user_id, auth_source='sso').first()

        if not user:
            user = User(
                username=sso_user_id, 
                email=user_info.get('email'),
                auth_source='sso'
            )
            db.session.add(user)
            db.session.commit()

        login_user(user, remember=True)

    return redirect(url_for('main.index'))
