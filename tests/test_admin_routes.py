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

#
# Author: Taco Scheltema https://github.com/TacoScheltema/blackbook
#

from app import db
from app.models import User


def login(client, username, password):
    """Helper function to log in a user."""
    return client.post(
        "/login",
        data={"username": username, "password": password, "auth_type": "local"},
        follow_redirects=True,
    )


def test_admin_users_page_as_admin(client, admin_user):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/admin/users' page is requested (GET) by an admin
    THEN check that the response is valid
    """
    login(client, admin_user.username, "password")
    response = client.get("/admin/users")
    assert response.status_code == 200
    assert b"Manage Users" in response.data


def test_admin_users_page_as_non_admin(client, test_user):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/admin/users' page is requested (GET) by a non-admin
    THEN check that access is forbidden
    """
    login(client, test_user.username, "password")
    response = client.get("/admin/users")
    assert response.status_code == 403


def test_admin_cache_page_as_admin(client, admin_user):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/admin/cache' page is requested (GET) by an admin
    THEN check that the response is valid
    """
    login(client, admin_user.username, "password")
    response = client.get("/admin/cache")
    assert response.status_code == 200
    assert b"Cache Status" in response.data


def test_add_local_user(client, admin_user):
    """
    GIVEN a Flask application configured for testing
    WHEN a new local user is added via the admin page (POST)
    THEN check that the user is created in the database
    """
    login(client, admin_user.username, "password")
    form_data = {
        "auth_type": "local",
        "username": "newlocal",
        "email": "newlocal@test.com",
        "password": "password",
    }
    response = client.post("/admin/add_user", data=form_data, follow_redirects=True)
    assert response.status_code == 200
    assert b"Local user added successfully." in response.data
    user = User.query.filter_by(username="newlocal").first()
    assert user is not None
    assert user.email == "newlocal@test.com"


def test_add_ldap_user(client, mocker, admin_user):
    """
    GIVEN a Flask application configured for testing
    WHEN a new LDAP user is added via the admin page (POST)
    THEN check that the user is created in the database and LDAP
    """
    login(client, admin_user.username, "password")
    mock_add_ldap_user = mocker.patch("app.main.admin_routes.add_ldap_user", return_value=True)
    form_data = {
        "auth_type": "ldap",
        "username": "newldap",
        "email": "newldap@test.com",
        "password": "password",
        "given_name": "New",
        "surname": "LDAP",
    }
    response = client.post("/admin/add_user", data=form_data, follow_redirects=True)
    assert response.status_code == 200
    assert b"LDAP user added successfully." in response.data
    user = User.query.filter_by(username="newldap").first()
    assert user is not None
    mock_add_ldap_user.assert_called_once()


def test_delete_user(client, admin_user, test_user):
    """
    GIVEN a Flask application configured for testing
    WHEN a user is deleted via the admin page (POST)
    THEN check that the user is removed from the database
    """
    login(client, admin_user.username, "password")
    response = client.post(f"/admin/delete_user/{test_user.id}", follow_redirects=True)
    assert response.status_code == 200
    assert f"User {test_user.username} deleted successfully.".encode("utf-8") in response.data
    user = db.session.get(User, test_user.id)
    assert user is None


def test_force_reset_password(client, mocker, admin_user, test_user):
    """
    GIVEN a Flask application configured for testing
    WHEN a password reset is forced for a user
    THEN check that a reset email is sent
    """
    login(client, admin_user.username, "password")
    mock_send_email = mocker.patch("app.main.admin_routes.send_password_reset_email")
    response = client.post(f"/admin/force_reset/{test_user.id}", follow_redirects=True)
    assert response.status_code == 200
    assert f"A password reset link has been sent to {test_user.email}.".encode("utf-8") in response.data
    mock_send_email.assert_called_once()


def test_set_roles(client, admin_user, test_user):
    """
    GIVEN a Flask application configured for testing
    WHEN roles are set for a user
    THEN check that the user's roles are updated in the database
    """
    login(client, admin_user.username, "password")
    form_data = {"is_admin": "on", "is_editor": "on"}
    response = client.post(f"/admin/set_roles/{test_user.id}", data=form_data, follow_redirects=True)
    assert response.status_code == 200
    assert f"Roles updated for {test_user.username}.".encode("utf-8") in response.data
    user = db.session.get(User, test_user.id)
    assert user.is_admin
    assert user.is_editor
