import os
import datetime
import src.settings as settings
from celery import Celery
from celery.utils.log import get_task_logger
from pymongo import MongoClient

# Celery worker defined in settings file
app = Celery('challenge_part_1')
app.config_from_object(settings)

# Task logger
logger = get_task_logger(__name__)

# Database connection
connection = MongoClient(
    settings.database_url, 
    connect=False, 
    username=settings.database_user, 
    password=settings.database_password
)

# Task definition
@app.task(name='insert_into_database', bind=True, ignore_result=True)
def insert_into_database(self, payload):
    try:
        # Add insertion datetime
        product = {
            'content': payload,
            'insertion_datetime': datetime.datetime.now().strftime(settings.datetime_format)
        }
        db = connection[settings.database_name]
        col = db[settings.database_collection]
        result = col.insert_one(product)
        logger.info(f'Product successfully inserted with ID: {result.inserted_id}')
    except Exception as e:
        # In case of error, retry after 5 minutes (maximum of 20 retries)  
        logger.error(f'Error message: {e}')
        raise self.retry(countdown=300, max_retries=20)
