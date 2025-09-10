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
# Author: Taco Scheltema <github@scheltema.me>
#

from unittest.mock import MagicMock

from app.models import User


def login(client, username, password, auth_type="local"):
    """Helper function to log in a user."""
    return client.post(
        "/login",
        data={"username": username, "password": password, "auth_type": auth_type},
        follow_redirects=True,
    )


def test_login_page_get(client):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/login' page is requested (GET)
    THEN check that the response is valid
    """
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Sign In" in response.data


def test_local_login_successful(client, test_user):
    """
    GIVEN a Flask application and a test user
    WHEN the user logs in with correct credentials
    THEN check that the login is successful
    """
    response = login(client, test_user.username, "password")
    assert response.status_code == 200
    assert b"Address Book" in response.data


def test_local_login_failed(client, test_user):
    """
    GIVEN a Flask application and a test user
    WHEN the user logs in with incorrect credentials
    THEN check that the login fails
    """
    response = login(client, test_user.username, "wrongpassword")
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data


def test_ldap_login_successful(client, mocker):
    """
    GIVEN a Flask application with mocked LDAP
    WHEN a user logs in with correct LDAP credentials
    THEN check that the login is successful
    """
    mocker.patch("app.auth.routes.authenticate_ldap_user", return_value=(True, False, True))
    response = login(client, "ldapuser", "password", auth_type="ldap")
    assert response.status_code == 200
    assert b"Address Book" in response.data
    user = User.query.filter_by(username="ldapuser").first()
    assert user is not None
    assert user.is_editor


def test_logout(client, test_user):
    """
    GIVEN a logged in user
    WHEN the '/logout' page is requested (GET)
    THEN check that the user is logged out
    """
    login(client, test_user.username, "password")
    response = client.get("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"Sign In" in response.data


def test_request_password_reset(client, mocker, test_user):
    """
    GIVEN a Flask application and a test user
    WHEN a password reset is requested
    THEN check that a reset email is sent
    """
    mock_send_email = mocker.patch("app.auth.routes.send_password_reset_email")
    response = client.post("/request-password-reset", data={"email": test_user.email}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Check your email for the instructions" in response.data
    mock_send_email.assert_called_once()


def test_reset_password_token(client, test_user):
    """
    GIVEN a Flask application and a user with a reset token
    WHEN the reset password page is accessed with the token
    THEN check that the response is valid
    """
    token = test_user.get_reset_password_token()
    response = client.get(f"/reset-password/{token}")
    assert response.status_code == 200
    assert b"Reset Your Password" in response.data


def test_sso_login(client):
    """
    GIVEN a Flask application with SSO configured
    WHEN the SSO login route is accessed
    THEN check that it redirects to the provider
    """
    # This test assumes Google SSO is configured in TestConfig
    response = client.get("/login/google")
    assert response.status_code == 302
    assert "accounts.google.com" in response.location


def test_sso_authorize(client, mocker):
    """
    GIVEN a Flask application with SSO configured
    WHEN the SSO provider authorizes the user
    THEN check that the user is created and logged in
    """
    mock_oauth_client = MagicMock()
    mock_oauth_client.authorize_access_token.return_value = {"userinfo": {"sub": "12345", "email": "sso@test.com"}}
    mocker.patch("app.oauth.create_client", return_value=mock_oauth_client)

    response = client.get("/authorize/google", follow_redirects=True)
    assert response.status_code == 200
    assert b"Address Book" in response.data
    user = User.query.filter_by(username="12345").first()
    assert user is not None
    assert user.email == "sso@test.com"
