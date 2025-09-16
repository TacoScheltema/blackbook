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

from unittest.mock import MagicMock

import pytest

from app import create_app, db
from app.models import User
from config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    LDAP_CONTACT_DN_TEMPLATE = "cn={cn},ou=contacts,dc=example,dc=com"
    GOOGLE_CLIENT_ID = "test"
    GOOGLE_CLIENT_SECRET = "test"


@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = create_app(TestConfig)

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def test_user(app):
    """Create a test user."""
    user = User(username="testuser", email="test@test.com", is_editor=False)
    user.set_password("password")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def editor_user(app):
    """Create an editor user."""
    user = User(username="editoruser", email="editor@test.com", is_editor=True)
    user.set_password("password")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def admin_user(app):
    """Create an admin user."""
    user = User(username="adminuser", email="admin@test.com", is_admin=True)
    user.set_password("password")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def mock_ldap_connection(mocker):
    """Fixture to mock the LDAP connection."""
    mock_conn = MagicMock()
    mocker.patch("app.ldap_utils.get_ldap_connection", return_value=mock_conn)
    return mock_conn
