import pytest

from importlib import import_module


@pytest.fixture
def app():
    mod = import_module('src.app')
    return mod.create_app()


def test_index_returns_html(app):
    client = app.test_client()
    res = client.get('/')
    assert res.status_code == 200
    ct = res.headers.get('Content-Type', '')
    assert 'html' in ct.lower()


def test_health_endpoint(app):
    client = app.test_client()
    res = client.get('/health')
    assert res.status_code == 200
    json_data = res.get_json()
    assert isinstance(json_data, dict)
    assert 'status' in json_data
    assert 'db_path' in json_data
