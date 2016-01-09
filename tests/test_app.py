import pytest

from wikivision.app import app

@pytest.fixture
def test_app():
    return app.test_client()

def test_home_page(test_app):
    response = test_app.get('/')
    assert response._status_code == 200
