import os
from flask import Flask

app = Flask('challenge_part_1')

# Check if it should run in debug mode
app.config['DEBUG'] = os.environ.get('DEBUG')

# Ignore slashes
app.url_map.strict_slashes = False

# Import routes (just one for now)
import src.routes