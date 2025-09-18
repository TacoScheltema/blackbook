from datetime import datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app import db, scheduler
from app.email import send_password_reset_email
from app.ldap_utils import add_ldap_user, delete_ldap_user
from app.main.helpers import admin_required
from app.models import User

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# --- Admin Routes ---


@admin_bp.route("/users")
@login_required
@admin_required
def admin_users():
    local_users = User.query.filter_by(auth_source="local").all()
    ldap_users = User.query.filter_by(auth_source="ldap").all()
    google_users = User.query.filter_by(auth_source="google").all()
    return render_template(
        "admin/users.html",
        title="Manage Users",
        local_users=local_users,
        ldap_users=ldap_users,
        google_users=google_users,
        current_time=datetime.now(timezone.utc),
    )


@admin_bp.route("/cache")
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


@admin_bp.route("/add_user", methods=["POST"])
@login_required
@admin_required
def add_user():
    auth_type = request.form.get("auth_type")
    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")

    if not all([username, password]):
        flash("Username and password are required.", "warning")
        return redirect(url_for("admin.admin_users"))

    if User.query.filter_by(username=username).first():
        flash("Username already exists in the local database.", "danger")
        return redirect(url_for("admin.admin_users"))

    if auth_type == "local":
        _add_local_user(username, email, password)
    elif auth_type == "ldap":
        given_name = request.form.get("given_name")
        surname = request.form.get("surname")
        _add_ldap_user(username, password, email, given_name, surname)

    return redirect(url_for("admin.admin_users"))


@admin_bp.route("/delete_user/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    if user_id == 1:
        flash("Cannot delete the primary admin user.", "danger")
        return redirect(url_for("admin.admin_users"))

    user = db.get_or_404(User, user_id)

    if user.auth_source == "ldap":
        if not delete_ldap_user(user.username):
            flash("Failed to delete user from LDAP. Aborting.", "danger")
            return redirect(url_for("admin.admin_users"))

    db.session.delete(user)
    db.session.commit()
    flash(f"User {user.username} deleted successfully.", "success")
    return redirect(url_for("admin.admin_users"))


@admin_bp.route("/force_reset/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def force_reset_password(user_id):
    user = db.get_or_404(User, user_id)

    if not user.email:
        flash(f"Cannot send reset link: User {user.username} has no email address.", "danger")
        return redirect(url_for("admin.admin_users"))

    send_password_reset_email(user)
    db.session.commit()
    flash(f"A password reset link has been sent to {user.email}.", "info")
    return redirect(url_for("admin.admin_users"))


@admin_bp.route("/set_roles/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def set_roles(user_id):
    if user_id == 1:
        flash("Cannot change roles for the primary admin user.", "danger")
        return redirect(url_for("admin.admin_users"))

    user = db.get_or_404(User, user_id)
    user.is_admin = "is_admin" in request.form
    user.is_editor = "is_editor" in request.form
    db.session.commit()
    flash(f"Roles updated for {user.username}.", "success")
    return redirect(url_for("admin.admin_users"))
