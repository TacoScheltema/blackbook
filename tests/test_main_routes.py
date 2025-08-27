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
def test_index_page(client, mocker):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/' page is requested (GET)
    THEN check that the response is valid
    """
    # Mock the cache to return an empty list of people
    mocker.patch("app.cache.get", return_value=[])

    response = client.get("/")
    assert response.status_code == 200
    assert b"Address Book" in response.data
    assert b"Contacts" in response.data


def test_companies_page(client, mocker):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/companies' page is requested (GET)
    THEN check that the response is valid and displays companies
    """
    # Mock the cache to return a list of people with companies
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
