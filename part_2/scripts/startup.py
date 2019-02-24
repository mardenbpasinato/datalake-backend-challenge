import os
import shutil
import json
import logging
from celery import Celery

# Load parameters
queue = os.environ.get('BROKER_QUEUE')
task = os.environ.get('CELERY_TASK')
broker_url = os.environ.get('BROKER_ENDPOINT')
input_path = os.environ.get('INPUT_PATH')
processed_path = os.environ.get('PROCESSED_PATH')

# Start celery app
celery = Celery('challenge_part_2', broker=broker_url)

# List all files to be processed
for filename in os.listdir(input_path):
    input_file = open(os.path.join(input_path, filename), 'r')
    for line in input_file:
        try:
            # Load as dict and send for async processing
            payload = json.loads(line)
            celery.send_task(task, args=[payload], queue=queue)
        except Exception as e:
            # If anything goes wrong, log as error 
            logging.error(f'{e}')
    
    # Close input file
    input_file.close()

    # Move file to the processed folder
    shutil.move(os.path.join(input_path, filename), os.path.join(processed_path, filename))
