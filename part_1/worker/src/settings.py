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

# Database config
database_url =  os.environ.get('DATABASE_ENDPOINT')
database_user = os.environ.get('DATABASE_USER')
database_password = os.environ.get('DATABASE_PASSWORD')
database_name = os.environ.get('DATABASE')
database_collection = os.environ.get('COLLECTION')

# Datetime format
datetime_format = '%Y-%m-%d %H:%M:%S'