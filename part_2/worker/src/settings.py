import os

# Broker config
broker_url = os.environ.get('BROKER_ENDPOINT')

# Celery Config
timezone = 'America/Sao_Paulo'
enable_utc = True
task_serializer = 'json'

# Assign queue to task
task_routes = {
    'insert_into_database':
        {
            'queue': os.environ.get('QUEUE')
        }
}

# Image server (mock)
image_server = os.environ.get('IMAGE_SERVER')
