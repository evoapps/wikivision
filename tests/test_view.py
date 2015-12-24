import pytest

import wikivision

@pytest.fixture
def app():
    return wikivision.app.test_client()

def test_home_page(app):
    response = app.get('/')
    assert response._status_code == 200
