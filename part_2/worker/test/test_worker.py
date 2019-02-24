import pytest
import mock
import src.settings as settings
from celery.exceptions import Retry
from src.app import verify_image

class TestVerifyImage:

    @mock.patch('src.app.logger')
    def test_payload_without_product_id(self, mock_logger):
        '''
        Case where payload does not have productId key (invalid payload)
        '''
        payload = {'image': 'http://image-server/images/123.png'}
        msg = f'Product id or image name ill formatted'
        
        verify_image(payload)
        mock_logger.error.assert_called_once_with(msg)

    @mock.patch('src.app.logger')
    def test_payload_without_image(self, mock_logger):
        '''
        Case where payload does not have image key (invalid payload)
        '''
        payload = {'productId': 'pid123'}
        msg = f'Product id or image name ill formatted'
        
        verify_image(payload)
        mock_logger.error.assert_called_once_with(msg)

    @mock.patch('src.app.verify_image.retry')
    @mock.patch('src.app.shared_memory.hgetall')
    @mock.patch('src.app.logger')
    def test_failure_in_hgetall_method(self, mock_logger, mock_hgetall, mock_retry):
        '''
        Case where there is a failure in hgetall (shared memory connection)
        '''
        payload = {'productId': 'pid123', 'image': 'http://image-server/images/123.png'}
        msg = 'Failure in hgetall method'
        exc = Exception(msg)
        mock_hgetall.side_effect = exc
        mock_retry.side_effect = Retry()
        
        with pytest.raises(Retry):
            verify_image(payload)
        mock_logger.error.assert_called_once_with(f'Error message: {msg}')
        mock_retry.assert_called_once_with(countdown=300, max_retries=20)

    @mock.patch('src.app.shared_memory.hgetall')
    @mock.patch('src.app.logger')
    def test_image_already_in_memory(self, mock_logger, mock_hgetall):
        '''
        Case where image is already in the shared memory
        '''
        payload = {'productId': 'pid123', 'image': 'http://image-server/images/123.png'}
        product_id = payload['productId']
        image_name = payload['image'].split('/')[-1]
        mock_hgetall.return_value = {'http://image-server/images/123.png': '1'}
        msg = f"Image already sent to server - Product ID: {product_id}, Image Name: {image_name}"

        verify_image(payload)
        mock_hgetall.assert_called_once_with(product_id)
        mock_logger.info.assert_called_once_with(msg)

    @mock.patch('src.app.verify_image.retry')
    @mock.patch('src.app.requests.get')
    @mock.patch('src.app.shared_memory.hgetall')
    @mock.patch('src.app.logger')
    def test_failure_in_image_server(self, mock_logger, mock_hgetall, mock_requests, mock_retry):
        '''
        Case where there is a failure in the call to the image server
        '''
        payload = {'productId': 'pid123', 'image': 'http://image-server/images/123.png'}
        product_id = payload['productId']
        msg = 'Failure in calling the image server'
        settings.image_server = 'http://test-server/'
        image_name = payload['image'].split('/')[-1]
        exc = Exception(msg)
        mock_requests.side_effect = exc
        mock_hgetall.return_value = {}
        mock_retry.side_effect = Retry()
        
        with pytest.raises(Retry):
            verify_image(payload)
        mock_hgetall.assert_called_once_with(product_id)
        mock_requests.assert_called_once_with(settings.image_server + image_name)
        mock_logger.error.assert_called_once_with(f'Error message: {msg}')
        mock_retry.assert_called_once_with(countdown=300, max_retries=20)

    @mock.patch('src.app.verify_image.retry')
    @mock.patch('src.app.shared_memory.hset')
    @mock.patch('src.app.requests.get')
    @mock.patch('src.app.shared_memory.hgetall')
    @mock.patch('src.app.logger')
    def test_response_200_failure_in_set_method(self, mock_logger, mock_hgetall, mock_requests, 
    mock_hset, mock_retry):
        '''
        Case where response is 200 but there is a failure in the hset method (shared memory)
        '''
        payload = {'productId': 'pid123', 'image': 'http://image-server/images/123.png'}
        product_id = payload['productId']
        image = payload['image']
        image_name = payload['image'].split('/')[-1]
        settings.image_server = 'http://test-server/'
        msg = 'Failure in hset method'
        exc = Exception(msg)
        mock_hset.side_effect = exc
        mock_requests.return_value.status_code = 200
        mock_hgetall.return_value = {}
        mock_retry.side_effect = Retry()
        
        with pytest.raises(Retry):
            verify_image(payload)
        mock_hgetall.assert_called_once_with(product_id)
        mock_requests.assert_called_once_with(settings.image_server + image_name)
        mock_hset.assert_called_once_with(product_id, image, 1)
        mock_logger.error.assert_called_once_with(f'Error message: {msg}')
        mock_retry.assert_called_once_with(countdown=300, max_retries=20)

    @mock.patch('src.app.shared_memory.hset')
    @mock.patch('src.app.requests.get')
    @mock.patch('src.app.shared_memory.hgetall')
    @mock.patch('src.app.logger')
    def test_response_200_success_case(self, mock_logger, mock_hgetall, mock_requests, mock_hset):
        '''
        Case where response is 200 and hset is executed (successful case)
        '''
        payload = {'productId': 'pid123', 'image': 'http://image-server/images/123.png'}
        product_id = payload['productId']
        image = payload['image']
        image_name = payload['image'].split('/')[-1]
        settings.image_server = 'http://test-server/'
        mock_hset.return_value = 1
        mock_requests.return_value.status_code = 200
        mock_hgetall.return_value = {}
        
        verify_image(payload)
        mock_hgetall.assert_called_once_with(product_id)
        mock_requests.assert_called_once_with(settings.image_server + image_name)
        mock_hset.assert_called_once_with(product_id, image, 1)
        mock_logger.info.assert_called_once_with(
            f'Image found in server - Product ID: {product_id}, Image Name: {image_name}'
        )

    @mock.patch('src.app.verify_image.retry')
    @mock.patch('src.app.shared_memory.hset')
    @mock.patch('src.app.requests.get')
    @mock.patch('src.app.shared_memory.hgetall')
    @mock.patch('src.app.logger')
    def test_response_404_failure_in_set_method(self, mock_logger, mock_hgetall, mock_requests, 
    mock_hset, mock_retry):
        '''
        Case where response is 404 but there is a failure in the hset method (shared memory)
        '''
        payload = {'productId': 'pid123', 'image': 'http://image-server/images/123.png'}
        product_id = payload['productId']
        image = payload['image']
        image_name = payload['image'].split('/')[-1]
        settings.image_server = 'http://test-server/'
        msg = 'Failure in hset method'
        exc = Exception(msg)
        mock_hset.side_effect = exc
        mock_requests.return_value.status_code = 404
        mock_hgetall.return_value = {}
        mock_retry.side_effect = Retry()
        
        with pytest.raises(Retry):
            verify_image(payload)
        mock_hgetall.assert_called_once_with(product_id)
        mock_requests.assert_called_once_with(settings.image_server + image_name)
        mock_hset.assert_called_once_with(product_id, image, 0)
        mock_logger.error.assert_called_once_with(f'Error message: {msg}')
        mock_retry.assert_called_once_with(countdown=300, max_retries=20)

    @mock.patch('src.app.shared_memory.hset')
    @mock.patch('src.app.requests.get')
    @mock.patch('src.app.shared_memory.hgetall')
    @mock.patch('src.app.logger')
    def test_response_404_success_case(self, mock_logger, mock_hgetall, mock_requests, mock_hset):
        '''
        Case where response is 404 and hset is executed (successful case)
        '''
        payload = {'productId': 'pid123', 'image': 'http://image-server/images/123.png'}
        product_id = payload['productId']
        image = payload['image']
        image_name = payload['image'].split('/')[-1]
        settings.image_server = 'http://test-server/'
        mock_hset.return_value = 1
        mock_requests.return_value.status_code = 404
        mock_hgetall.return_value = {}
        
        verify_image(payload)
        mock_hgetall.assert_called_once_with(product_id)
        mock_requests.assert_called_once_with(settings.image_server + image_name)
        mock_hset.assert_called_once_with(product_id, image, 0)
        mock_logger.info.assert_called_once_with(
            f'Image not found in server - Product ID: {product_id}, Image Name: {image_name}'
        )

    @mock.patch('src.app.verify_image.retry')
    @mock.patch('src.app.requests.get')
    @mock.patch('src.app.shared_memory.hgetall')
    @mock.patch('src.app.logger')
    def test_response_500(self, mock_logger, mock_hgetall, mock_requests, mock_retry):
        '''
        Case where response is other than 200 or 404 (500 for instance)
        '''
        payload = {'productId': 'pid123', 'image': 'http://image-server/images/123.png'}
        product_id = payload['productId']
        image = payload['image']
        image_name = payload['image'].split('/')[-1]
        settings.image_server = 'http://test-server/'
        mock_requests.return_value.status_code = 500
        mock_hgetall.return_value = {}
        mock_retry.side_effect = Retry()
        msg = f'Unexpected response: {mock_requests.return_value.status_code} - Product ID: {product_id}, Image Name: {image_name}'
        
        with pytest.raises(Retry):
            verify_image(payload)
        mock_hgetall.assert_called_once_with(product_id)
        mock_requests.assert_called_once_with(settings.image_server + image_name)
        mock_logger.error.assert_called_once_with(f'Error message: {msg}')
        mock_retry.assert_called_once_with(countdown=300, max_retries=20)

    