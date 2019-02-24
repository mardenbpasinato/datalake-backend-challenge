import pytest
import mock
import json
import src.routes as settings
from src.app import app

@pytest.fixture
def client():
    '''
    Flask app fixture
    '''
    app.testing = True
    client = app.test_client()
    yield client

def test_access_route_with_get_method(client):
    '''
    Case where the route is called with HTTP GET method
    '''
    result = client.get('/v1/products')
    assert result.status_code == 405

def test_access_route_with_put_method(client):
    '''
    Case where the route is called with HTTP PUT method
    '''
    result = client.put('/v1/products')
    assert result.status_code == 405

def test_access_route_with_delete_method(client):
    '''
    Case where the route is called with HTTP DELETE method
    '''
    result = client.delete('/v1/products')
    assert result.status_code == 405

@mock.patch('src.routes.request')
@mock.patch('src.routes.app.logger.error')
def test_invalid_payload(mock_logger, mock_request, client):
    '''
    Case where an invalid payload is sent
    '''
    exc = Exception('Invalid payload')
    mock_request.get_json.side_effect = exc
    payload = None
    expected_result = {'msg': 'Invalid json format'}
    result = client.post('/v1/products', json=payload)

    assert result.status_code == 400
    assert expected_result == result.get_json()
    mock_logger.assert_called_once_with(f'Payload error: {exc}')

@mock.patch('src.routes.hashlib.sha256')
@mock.patch('src.routes.app.logger.error')
def test_failure_creating_fingerprint(mock_logger, mock_hash, client):
    '''
    Case where there is a failure in generating the fingerprint
    '''
    exc = Exception('Failure in fingerprint generation')
    mock_hash.side_effect = exc
    payload = None
    expected_result = {'msg': 'Invalid json format'}
    result = client.post('/v1/products', json=payload)

    assert result.status_code == 400
    assert expected_result == result.get_json()
    mock_logger.assert_called_once_with(f'Payload error: {exc}')

@mock.patch('src.routes.cache')
@mock.patch('src.routes.app.logger.info')
def test_payload_found_in_cache(mock_logger, mock_cache, client):
    '''
    Case where the payload sent is found in cache (rejected)
    '''
    settings.cache_time = 300
    mock_cache.get.return_value = bin(1)
    payload = [{'id': '123', 'name': 'mesa'}]
    fingerprint = '28b291f06e32b9e0eb2dc9595e5b13b4317a4278a29486e4553150f98c0055bf'
    expected_result = {'msg': f'Product already sent in the last {settings.cache_time/60} minutes'}
    result = client.post('/v1/products', json=payload)
    
    assert result.status_code == 403
    assert expected_result == result.get_json()
    mock_logger.assert_called_once_with(f'Cache hit for fingerprint: {fingerprint}')

@mock.patch('src.routes.celery')
@mock.patch('src.routes.cache')
@mock.patch('src.routes.app.logger.info')
def test_payload_not_found_in_cache(mock_logger, mock_cache, mock_celery, client):
    '''
    Case where the payload sent is not found in cache (accepted)
    '''
    settings.queue = 'test_queue'
    settings.task = 'test_task'
    settings.cache_time = 300
    mock_cache.get.return_value = None
    payload = [{'id': '123', 'name': 'mesa'}]
    fingerprint = '28b291f06e32b9e0eb2dc9595e5b13b4317a4278a29486e4553150f98c0055bf'
    expected_result = {'msg': f'Product successfully received'}
    result = client.post('/v1/products', json=payload)
    
    assert result.status_code == 200
    assert expected_result == result.get_json()
    mock_cache.set.assert_called_once_with(fingerprint, bin(1), settings.cache_time)
    mock_celery.send_task(settings.task, args=[payload], queue=settings.queue)
    mock_logger.assert_called_once_with(f'Cache miss for fingerprint: {fingerprint}')
