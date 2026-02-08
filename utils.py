"""
Utility functions
"""
import yaml
import logging
from pathlib import Path
from datetime import datetime
import json

def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Set defaults
        config.setdefault('mosdac', {})
        config['mosdac'].setdefault('base_url', 'https://mosdac.gov.in')
        config['mosdac'].setdefault('product_json_url', 'https://mosdac.gov.in/gallery/product.json?v=0.24')
        config['mosdac'].setdefault('api_endpoint', 'https://mosdac.gov.in/gallery/getImage.php')
        
        config.setdefault('download', {})
        config['download'].setdefault('count_per_request', 8)
        config['download'].setdefault('lookback_days', 7)
        config['download'].setdefault('max_concurrent', 5)
        config['download'].setdefault('save_previews', True)
        
        config.setdefault('storage', {})
        config['storage'].setdefault('base_dir', 'images')
        config['storage'].setdefault('organize_by', ['satellite', 'sensor', 'product_type', 'date'])
        
        config.setdefault('scheduler', {})
        config['scheduler'].setdefault('interval_minutes', 30)
        config['scheduler'].setdefault('max_runtime', 25)
        
        config.setdefault('filters', {})
        config['filters'].setdefault('satellites', [])
        config['filters'].setdefault('sensors', [])
        config['filters'].setdefault('product_types', [])
        
        config.setdefault('log', {})
        config['log'].setdefault('level', 'INFO')
        config['log'].setdefault('file', 'mosdac_downloader.log')
        config['log'].setdefault('max_size_mb', 10)
        
        return config
        
    except FileNotFoundError:
        # Create default config
        default_config = {
            'mosdac': {
                'base_url': 'https://mosdac.gov.in',
                'product_json_url': 'https://mosdac.gov.in/gallery/product.json?v=0.24',
                'api_endpoint': 'https://mosdac.gov.in/gallery/getImage.php'
            },
            'download': {
                'count_per_request': 8,
                'lookback_days': 7,
                'max_concurrent': 5,
                'save_previews': True
            },
            'storage': {
                'base_dir': 'images',
                'organize_by': ['satellite', 'sensor', 'product_type', 'date']
            },
            'scheduler': {
                'interval_minutes': 30,
                'max_runtime': 25
            },
            'filters': {
                'satellites': [],
                'sensors': [],
                'product_types': []
            },
            'log': {
                'level': 'INFO',
                'file': 'mosdac_downloader.log',
                'max_size_mb': 10
            }
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
        
        return default_config

def setup_logging(config: dict) -> logging.Logger:
    """Setup logging configuration"""
    log_config = config.get('log', {})
    
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_config.get('level', 'INFO')))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_config.get('level', 'INFO')))
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler
    if log_config.get('file'):
        file_handler = logging.FileHandler(log_config['file'])
        file_handler.setLevel(getattr(logging, log_config.get('level', 'INFO')))
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger

def save_image_metadata(image_path: Path, metadata: dict):
    """Save metadata for downloaded image"""
    metadata_file = image_path.with_suffix('.json')
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)

def load_image_metadata(image_path: Path) -> dict:
    """Load metadata for downloaded image"""
    metadata_file = image_path.with_suffix('.json')
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            return json.load(f)
    return {}

def cleanup_old_files(directory: Path, max_age_days: int = 30):
    """Cleanup files older than specified days"""
    current_time = datetime.now().timestamp()
    max_age_seconds = max_age_days * 24 * 60 * 60
    
    for file_path in directory.rglob('*'):
        if file_path.is_file():
            file_age = current_time - file_path.stat().st_mtime
            if file_age > max_age_seconds:
                file_path.unlink()
                # Also remove metadata file if exists
                metadata_file = file_path.with_suffix('.json')
                if metadata_file.exists():
                    metadata_file.unlink()
