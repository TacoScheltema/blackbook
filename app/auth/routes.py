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
import pprint
from urllib.parse import urlparse

from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app import db, oauth
from app.auth import bp
from app.email import send_password_reset_email
from app.ldap_utils import authenticate_ldap_user, set_ldap_password
from app.models import User


def _handle_local_login(username, password):
    """Handles the logic for a local user login."""
    user = User.query.filter_by(username=username).first()
    if user is None or not user.check_password(password):
        flash("Invalid username or password for local account", "danger")
        return None
    return user


def _handle_ldap_login(username, password):
    """Handles the logic for an LDAP user login."""
    is_authenticated, is_admin, is_editor = authenticate_ldap_user(username, password)
    if not is_authenticated:
        flash("Invalid username or password for LDAP account", "danger")
        return None

    user = User.query.filter_by(username=username, auth_source="ldap").first()
    if user is None:
        user = User(username=username, auth_source="ldap", is_admin=is_admin, is_editor=is_editor)
        db.session.add(user)
    else:
        user.is_admin = is_admin
        user.is_editor = is_editor
    db.session.commit()
    return user


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Handles user login."""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        auth_type = request.form.get("auth_type")
        user = None

        if auth_type == "local":
            user = _handle_local_login(username, password)
        elif auth_type == "ldap":
            user = _handle_ldap_login(username, password)

        if user:
            login_user(user, remember=True)
            next_page = request.args.get("next")
            if not next_page or urlparse(next_page).netloc != "":
                next_page = url_for("main.index")
            return redirect(next_page)

    return render_template("auth/login.html", title="Sign In")


@bp.route("/logout")
def logout():
    """Handles user logout."""
    logout_user()
    return redirect(url_for("auth.login"))


@bp.route("/request-password-reset", methods=["GET", "POST"])
def request_password_reset():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()
        if user:
            send_password_reset_email(user)
            db.session.commit()
        flash("Check your email for the instructions to reset your password", "info")
        return redirect(url_for("auth.login"))
    return render_template("auth/request_reset_password.html", title="Reset Password")


@bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password_token(token):
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for("main.index"))
    if request.method == "POST":
        password = request.form.get("password")
        password2 = request.form.get("password2")
        if password != password2:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("auth.reset_password_token", token=token))
        if user.auth_source == "ldap":
            if not set_ldap_password(user.username, password):
                flash("Failed to update LDAP password.", "danger")
                return redirect(url_for("auth.login"))
        user.set_password(password)
        user.password_reset_token = None
        user.password_reset_expiration = None
        db.session.commit()
        flash("Your password has been reset.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/reset_password_token.html", title="Reset Password")


@bp.route("/reset-password", methods=["GET", "POST"])
@login_required
def reset_password():
    if not current_user.password_reset_required:
        return redirect(url_for("main.index"))
    if request.method == "POST":
        password = request.form.get("password")
        password2 = request.form.get("password2")
        if password != password2:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("auth.reset_password"))
        if current_user.auth_source == "ldap":
            if not set_ldap_password(current_user.username, password):
                flash("Failed to update LDAP password.", "danger")
                return redirect(url_for("auth.reset_password"))
        current_user.set_password(password)
        current_user.password_reset_required = False
        db.session.commit()
        flash("Your password has been reset.", "success")
        return redirect(url_for("main.index"))
    return render_template("auth/reset_password.html", title="Reset Password")


@bp.route("/login/<provider>")
def sso_login(provider):
    if not current_user.is_anonymous:
        return redirect(url_for("main.index"))
    redirect_uri = url_for("auth.authorize", provider=provider, _external=True)
    return oauth.create_client(provider).authorize_redirect(redirect_uri)


@bp.route("/authorize/<provider>")
def authorize(provider):
    if not current_user.is_anonymous:
        return redirect(url_for("main.index"))

    client = oauth.create_client(provider)
    token = client.authorize_access_token()
    user_info = token.get("userinfo")

    if user_info:
        if current_app.config["DEBUG"]:
            print("--- SSO User Info Claim ---")
            pprint.pprint(user_info)
            print("---------------------------")

        sso_user_id = user_info["sub"]
        user = User.query.filter_by(username=sso_user_id, auth_source=provider).first()

        is_admin = False
        is_editor = False

        # For non-Google providers, check for group membership to assign roles
        if provider != "google":
            admin_group = current_app.config.get(f"{provider.upper()}_ADMIN_GROUP")
            if admin_group and "groups" in user_info and admin_group in user_info["groups"]:
                is_admin = True

            editor_group = current_app.config.get(f"{provider.upper()}_EDITOR_GROUP")
            if editor_group and "groups" in user_info and editor_group in user_info["groups"]:
                is_editor = True

        if not user:
            user = User(
                username=sso_user_id,
                email=user_info.get("email"),
                auth_source=provider,
                is_admin=is_admin,
                is_editor=is_editor,
            )
            db.session.add(user)
        else:
            # For non-Google users, sync their roles on every login
            if provider != "google":
                user.is_admin = is_admin
                user.is_editor = is_editor

        db.session.commit()
        login_user(user, remember=True)

    return redirect(url_for("main.index"))
