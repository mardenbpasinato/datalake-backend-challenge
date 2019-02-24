import os
import redis
import requests
import src.settings as settings
import src.exceptions as exceptions
from celery import Celery
from celery.utils.log import get_task_logger

# Celery worker defined in settings file
app = Celery('challenge_part_2')
app.config_from_object(settings)

# Task logger
logger = get_task_logger(__name__)

# Shared Memory server
pool = redis.ConnectionPool(host=os.environ.get('SHARED_MEMORY_HOST'),
                            port=int(os.environ.get('SHARED_MEMORY_PORT')),
                            decode_responses=True,
                            db=0)
shared_memory = redis.StrictRedis(connection_pool=pool)

# Task definition
@app.task(name='verify_image', bind=True, ignore_result=True)
def verify_image(self, payload):
    try:
        product_id = payload['productId']
        image = payload['image']
        image_name = payload['image'].split('/')[-1]
        
        # Check if image was already sent to the server
        images = list(shared_memory.hgetall(product_id))
        if image in images:
            msg = f'Image already sent to server - Product ID: {product_id}, Image Name: {image_name}'
            raise exceptions.ImageAlreadySent(msg)

        # Check image in image server
        res = requests.get(settings.image_server + image_name)

        if res.status_code == 200:
            # Server has the image. Store this info in memory.
            shared_memory.hset(product_id, image, 1)
            msg = f'Image found in server - Product ID: {product_id}, Image Name: {image_name}'
            logger.info(msg)

        elif res.status_code == 404:
            # Server does not have image. Store this info in memory.
            shared_memory.hset(product_id, image, 0)
            msg = f'Image not found in server - Product ID: {product_id}, Image Name: {image_name}'
            logger.info(msg)

        else:
            # Some problem happened to image server. Try again latter.
            msg = f'Unexpected response: {res.status_code} - Product ID: {product_id}, Image Name: {image_name}'
            raise Exception(msg)

    except (KeyError, IndexError) as e:
        # Product id or image name ill formatted. No need to retry.
        logger.error(f'Product id or image name ill formatted')
        return
    
    except exceptions.ImageAlreadySent as e:
        # Image already sent to server. No need to retry.
        logger.info(f'{e}')
        return

    except Exception as e:
        # In case of error, retry after 5 minutes (maximum of 20 retries)  
        logger.error(f'Error message: {e}')
        raise self.retry(countdown=300, max_retries=20)
