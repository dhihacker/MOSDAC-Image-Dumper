import json
import logging
import os

# Load configuration from a JSON file

def load_config(config_file):
    with open(config_file, 'r') as file:
        return json.load(file)

# Setup logging configuration

def setup_logging(log_file='app.log'):
    logging.basicConfig(filename=log_file,
                        level=logging.INFO,
                        format='%(asctime)s:%(levelname)s:%(message)s')
    logging.info('Logging is set up. \n')

# Handle metadata operations

def read_metadata(metadata_file):
    with open(metadata_file, 'r') as file:
        return json.load(file)

# Clean up files older than a specified number of days

def cleanup_old_files(directory, days):
    cutoff = time.time() - (days * 86400)  # seconds in a day
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            if os.path.getmtime(file_path) < cutoff:
                os.remove(file_path)
                logging.info(f'Deleted {file_path}')