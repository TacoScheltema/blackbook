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
import base64


def login(client, username, password):
    """Helper function to log in a user."""
    return client.post(
        "/login",
        data={"username": username, "password": password, "auth_type": "local"},
        follow_redirects=True,
    )


def test_index_page(client, mocker, test_user):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/' page is requested (GET) by a logged in user
    THEN check that the response is valid
    """
    login(client, test_user.username, "password")
    mocker.patch("app.cache.get", return_value=[])

    response = client.get("/")
    assert response.status_code == 200
    assert b"Address Book" in response.data
    assert b"Contacts" in response.data


def test_companies_page(client, mocker, test_user):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/companies' page is requested (GET) by a logged in user
    THEN check that the response is valid and displays companies
    """
    login(client, test_user.username, "password")
    sample_people = [
        {"cn": ["Test User 1"], "o": ["Company A"]},
        {"cn": ["Test User 2"], "o": ["Company B"]},
        {"cn": ["Test User 3"], "o": ["Company A"]},
    ]
    mocker.patch("app.cache.get", return_value=sample_people)

    response = client.get("/companies")
    assert response.status_code == 200
    assert b"All Companies" in response.data
    assert b"Company A" in response.data
    assert b"Company B" in response.data


def test_company_detail_page(client, mocker, test_user):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/company/<b64_company_name>' page is requested (GET) by a logged in user
    THEN check that the response is valid and displays the correct employees
    """
    login(client, test_user.username, "password")
    sample_people = [
        {"dn": "cn=User One,dc=example,dc=com", "cn": ["User One"], "o": ["Company A"], "sn": ["One"]},
        {"dn": "cn=User Two,dc=example,dc=com", "cn": ["User Two"], "o": ["Company B"], "sn": ["Two"]},
        {"dn": "cn=User Three,dc=example,dc=com", "cn": ["User Three"], "o": ["Company A"], "sn": ["Three"]},
    ]
    mocker.patch("app.cache.get", return_value=sample_people)

    company_name = "Company A"
    b64_company_name = base64.urlsafe_b64encode(company_name.encode("utf-8")).decode("utf-8")

    response = client.get(f"/company/{b64_company_name}")
    assert response.status_code == 200
    assert company_name.encode("utf-8") in response.data
    assert b"User One" in response.data
    assert b"User Three" in response.data
    assert b"User Two" not in response.data


def test_company_orgchart_page(client, mocker, test_user):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/company/orgchart/<b64_company_name>' page is requested (GET) by a logged in user
    THEN check that the response is valid and displays the org chart
    """
    login(client, test_user.username, "password")
    sample_people = [
        {"dn": "cn=User One,dc=example,dc=com", "cn": ["User One"], "o": ["Company A"], "sn": ["One"]},
        {"dn": "cn=User Two,dc=example,dc=com", "cn": ["User Two"], "o": ["Company B"], "sn": ["Two"]},
        {"dn": "cn=User Three,dc=example,dc=com", "cn": ["User Three"], "o": ["Company A"], "sn": ["Three"]},
    ]
    mocker.patch("app.cache.get", return_value=sample_people)

    company_name = "Company A"
    b64_company_name = base64.urlsafe_b64encode(company_name.encode("utf-8")).decode("utf-8")

    response = client.get(f"/company/orgchart/{b64_company_name}")
    assert response.status_code == 200
    assert company_name.encode("utf-8") in response.data
    assert b"Organization Chart" in response.data
    assert b"User One" in response.data
    assert b"User Three" in response.data
    assert b"User Two" not in response.data


def test_company_cards_page(client, mocker, test_user):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/company/cards/<b64_company_name>' page is requested (GET) by a logged in user
    THEN check that the response is valid and displays the correct employees
    """
    login(client, test_user.username, "password")
    sample_people = [
        {"dn": "cn=User One,dc=example,dc=com", "cn": ["User One"], "o": ["Company A"], "sn": ["One"]},
        {"dn": "cn=User Two,dc=example,dc=com", "cn": ["User Two"], "o": ["Company B"], "sn": ["Two"]},
        {"dn": "cn=User Three,dc=example,dc=com", "cn": ["User Three"], "o": ["Company A"], "sn": ["Three"]},
    ]
    mocker.patch("app.cache.get", return_value=sample_people)

    company_name = "Company A"
    b64_company_name = base64.urlsafe_b64encode(company_name.encode("utf-8")).decode("utf-8")

    response = client.get(f"/company/cards/{b64_company_name}")
    assert response.status_code == 200
    assert company_name.encode("utf-8") in response.data
    assert b"User One" in response.data
    assert b"User Three" in response.data
    assert b"User Two" not in response.data


def test_person_detail_page(client, mocker, test_user):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/person/<b64_dn>' page is requested (GET) by a logged in user
    THEN check that the response is valid and displays the correct person's details
    """
    login(client, test_user.username, "password")
    sample_person = {
        "dn": "cn=Test User,dc=example,dc=com",
        "cn": ["Test User"],
        "mail": ["test@example.com"],
        "telephoneNumber": ["123-456-7890"],
    }
    mocker.patch("app.main.routes.get_entry_by_dn", return_value=sample_person)

    dn = "cn=Test User,dc=example,dc=com"
    b64_dn = base64.urlsafe_b64encode(dn.encode("utf-8")).decode("utf-8")

    response = client.get(f"/person/{b64_dn}")
    assert response.status_code == 200
    assert b"Test User" in response.data
    assert b"test@example.com" in response.data
    assert b"123-456-7890" in response.data


def test_person_vcard_generation(client, mocker, test_user):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/person/vcard/<b64_dn>' page is requested (GET) by a logged in user
    THEN check that a valid vCard is generated and returned
    """
    login(client, test_user.username, "password")
    sample_person = {
        "dn": "cn=Test User,dc=example,dc=com",
        "cn": ["Test User"],
        "sn": ["User"],
        "givenName": ["Test"],
        "o": ["Test Corp"],
        "mail": ["test@example.com"],
        "telephoneNumber": ["123-456-7890"],
        "street": ["123 Main St"],
        "l": ["Anytown"],
        "postalCode": ["12345"],
    }
    mocker.patch("app.main.routes.get_entry_by_dn", return_value=sample_person)

    dn = "cn=Test User,dc=example,dc=com"
    b64_dn = base64.urlsafe_b64encode(dn.encode("utf-8")).decode("utf-8")

    response = client.get(f"/person/vcard/{b64_dn}")
    assert response.status_code == 200
    assert response.mimetype == "text/vcard"
    assert "attachment; filename=Test_User.vcf" in response.headers["Content-Disposition"]

    vcard_data = response.data.decode("utf-8")
    assert "BEGIN:VCARD" in vcard_data
    assert "FN:Test User" in vcard_data
    assert "EMAIL;TYPE=WORK,INTERNET:test@example.com" in vcard_data
    assert "END:VCARD" in vcard_data


def test_add_person_page_get(client, mocker, editor_user):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/person/add' page is requested (GET) by an editor
    THEN check that the response is valid
    """
    login(client, editor_user.username, "password")
    mocker.patch("app.cache.get", return_value=[])
    response = client.get("/person/add")
    assert response.status_code == 200
    assert b"Add New Contact" in response.data


def test_add_person_page_post(client, mocker, editor_user):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/person/add' page is submitted (POST) by an editor
    THEN check that the new contact is added and the cache is refreshed
    """
    login(client, editor_user.username, "password")
    mock_add_ldap_entry = mocker.patch("app.main.routes.add_ldap_entry", return_value=True)
    mock_scheduler_add_job = mocker.patch("app.scheduler.add_job")

    form_data = {
        "cn": "New Contact",
        "sn": "Contact",
        "givenName": "New",
        "mail": "new@example.com",
    }

    response = client.post("/person/add", data=form_data, follow_redirects=True)
    assert response.status_code == 200
    assert b"Contact added successfully!" in response.data
    mock_add_ldap_entry.assert_called_once()
    mock_scheduler_add_job.assert_called_once()


def test_edit_person_page_get(client, mocker, editor_user):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/person/edit/<b64_dn>' page is requested (GET) by an editor
    THEN check that the response is valid
    """
    login(client, editor_user.username, "password")
    sample_person = {
        "dn": "cn=Test User,dc=example,dc=com",
        "cn": ["Test User"],
    }
    mocker.patch("app.main.routes.get_entry_by_dn", return_value=sample_person)
    mocker.patch("app.cache.get", return_value=[])

    dn = "cn=Test User,dc=example,dc=com"
    b64_dn = base64.urlsafe_b64encode(dn.encode("utf-8")).decode("utf-8")

    response = client.get(f"/person/edit/{b64_dn}")
    assert response.status_code == 200
    assert b"Edit Test User" in response.data


def test_edit_person_page_post(client, mocker, editor_user):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/person/edit/<b64_dn>' page is submitted (POST) by an editor
    THEN check that the contact is updated and the cache is refreshed
    """
    login(client, editor_user.username, "password")
    sample_person = {
        "dn": "cn=Test User,dc=example,dc=com",
        "cn": ["Test User"],
    }
    mocker.patch("app.main.routes.get_entry_by_dn", return_value=sample_person)
    mock_modify_ldap_entry = mocker.patch("app.main.routes.modify_ldap_entry", return_value=True)
    mock_scheduler_add_job = mocker.patch("app.scheduler.add_job")

    form_data = {"cn": "Updated Name"}
    dn = "cn=Test User,dc=example,dc=com"
    b64_dn = base64.urlsafe_b64encode(dn.encode("utf-8")).decode("utf-8")

    response = client.post(f"/person/edit/{b64_dn}", data=form_data, follow_redirects=True)
    assert response.status_code == 200
    assert b"Person details updated successfully!" in response.data
    mock_modify_ldap_entry.assert_called_once()
    mock_scheduler_add_job.assert_called_once()


def test_delete_person_post(client, mocker, editor_user):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/person/delete/<b64_dn>' page is submitted (POST) by an editor
    THEN check that the contact is deleted and the cache is refreshed
    """
    login(client, editor_user.username, "password")
    mock_delete_ldap_contact = mocker.patch("app.main.routes.delete_ldap_contact", return_value=True)
    mock_scheduler_add_job = mocker.patch("app.scheduler.add_job")

    dn = "cn=Test User,dc=example,dc=com"
    b64_dn = base64.urlsafe_b64encode(dn.encode("utf-8")).decode("utf-8")

    response = client.post(f"/person/delete/{b64_dn}", follow_redirects=True)
    assert response.status_code == 200
    assert b"Contact deleted successfully!" in response.data
    mock_delete_ldap_contact.assert_called_once_with(dn)
    mock_scheduler_add_job.assert_called_once()
