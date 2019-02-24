import os
import redis
import json
import hashlib
from src.app import app
from celery import Celery
from flask import request, jsonify, abort

# Load parameters
queue = os.environ.get('BROKER_QUEUE')
task = os.environ.get('CELERY_TASK')
cache_time = int(os.environ.get('CACHE_TIME', 600))

# Load Cache and Celery
cache = redis.Redis.from_url(os.environ.get('CACHE_ENDPOINT'))
celery = Celery('challenge_part_1', broker=os.environ.get('BROKER_ENDPOINT'))

@app.route('/v1/products', methods=['POST'])
def receive_product():
    # Check if payload is in a correct json format
    # And if a fingerprint can be computed from it
    try:
        payload = request.get_json()
        fingerprint = hashlib.sha256(json.dumps(payload).encode('utf-8')).hexdigest()
    except Exception as exc:
        app.logger.error(f'Payload error: {exc}')
        abort(400)
    
    # Check if the fingerprint is already stored in cache
    cached_value = cache.get(fingerprint)
    if cached_value is not None:
        # Fingerprint found in cache, return 403
        app.logger.info(f'Cache hit for fingerprint: {fingerprint}')
        abort(403)
    
    else:
        # Fingerprint not found, receive payload (product)
        # Cache fingerprint as key with just 1 bit as value
        app.logger.info(f'Cache miss for fingerprint: {fingerprint}')
        cache.set(fingerprint, bin(1), cache_time)
        celery.send_task(task, args=[payload], queue=queue)
        return jsonify(msg=f'Product successfully received'), 200


# Error message in case of HTTP 400
@app.errorhandler(400)
def bad_request_response(error):
    msg = f'Invalid json format'
    return jsonify(msg=msg), 400

# Error message in case of HTTP 403 
@app.errorhandler(403)
def forbidden_response(error):
    msg = f'Product already sent in the last {cache_time/60} minutes'
    return jsonify(msg=msg), 403
