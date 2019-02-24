import os
import json
import redis
import datetime

# Load parameters
output_path = os.environ.get('OUTPUT_PATH')

# Shared Memory server
pool = redis.ConnectionPool(host=os.environ.get('SHARED_MEMORY_HOST'),
                            port=int(os.environ.get('SHARED_MEMORY_PORT')),
                            decode_responses=True,
                            db=0)
shared_memory = redis.StrictRedis(connection_pool=pool)

# Create output file
consolidation_datetime = datetime.datetime.now().strftime('%Y_%m_%d-%H_%M_%S')
filename = consolidation_datetime + '-output-dump'
output_file = open(os.path.join(output_path, filename), 'w')

# Search for stored data in shared memory
for key in shared_memory.scan_iter():
    stored_obj = shared_memory.hgetall(key)
    product = dict(productId=key)
    images = []
    
    # Maximum of 3 images per product
    for image in list(stored_obj):
        if stored_obj[image] == '1' and len(images) < 3:
            images.append(image)
    product['images'] = images

    # Save in output file
    output_file.write(json.dumps(product))
    output_file.write('\n')

# Close file
output_file.close()