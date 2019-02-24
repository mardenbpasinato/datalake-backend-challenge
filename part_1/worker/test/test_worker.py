import pytest
import mock
import src.settings as settings
from celery.exceptions import Retry
from src.app import insert_into_database

class TestInsertIntoDatabase:

    @mock.patch('src.app.insert_into_database.retry')
    @mock.patch('src.app.datetime.datetime')
    @mock.patch('src.app.connection')
    @mock.patch('src.app.logger')
    def test_failure_case(self, mock_logger, mock_db, mock_datetime, mock_retry):
        '''
        Case where a failure in database connection occurs
        '''
        settings.database_name = 'test_database'
        settings.database_collection = 'test_collection'
        exc = Exception('Failure in db connection')
        mock_db.insert_one.side_effect = exc
        mock_db.__getitem__.return_value = mock_db
        mock_retry.side_effect = Retry()
        payload = [{"id": "123", "name": "mesa"}]
        
        # Built-in type
        frozen_time = '2019-02-20 18:30:15'
        class CustomizedDateTime:
            def strftime(self, format):
                return frozen_time
        mock_datetime.now.return_value = CustomizedDateTime()

        expect_product = {
            'content': payload,
            'insertion_datetime': frozen_time
        }

        with pytest.raises(Retry):
            insert_into_database(payload)

        mock_db.has_calls([mock.call('test_database'), mock.call('test_collection')])
        mock_db.insert_one.assert_called_once_with(expect_product)
        mock_logger.error.assert_called_once_with(f'Error message: {exc}')
        mock_retry.assert_called_once_with(countdown=300, max_retries=20)

    @mock.patch('src.app.datetime.datetime')
    @mock.patch('src.app.connection')
    @mock.patch('src.app.logger')
    def test_success_case(self, mock_logger, mock_db, mock_datetime):
        '''
        Case where product is successfully inserted into database
        '''
        settings.database_name = 'test_database'
        settings.database_collection = 'test_collection'
        id_database = 'ID-123abc'
        mock_db.insert_one.return_value.inserted_id = id_database
        mock_db.__getitem__.return_value = mock_db
        payload = [{"id": "123", "name": "mesa"}]
        
        # Built-in type
        frozen_time = '2019-02-20 18:30:15'
        class CustomizedDateTime:
            def strftime(self, format):
                return frozen_time
        mock_datetime.now.return_value = CustomizedDateTime()

        expect_product = {
            'content': payload,
            'insertion_datetime': frozen_time
        }
        insert_into_database(payload)

        mock_db.has_calls([mock.call('test_database'), mock.call('test_collection')])
        mock_db.insert_one.assert_called_once_with(expect_product)
        mock_logger.info.assert_called_once_with(
            f'Product successfully inserted with ID: {id_database}'
        )
