import yaml
import logging
import logging.handlers
import os
from pathlib import Path
from typing import Dict, Tuple, Any

logger = logging.getLogger('home_temperature_control')

def setup_logging(config: dict) -> None:
    """Setup logging configuration for both file and console output."""
    # Create logs directory if it doesn't exist
    log_config = config.get('logging', {})
    log_dir = os.path.dirname(log_config['file_path'])
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Configure our module logger
    logger.setLevel(logging.DEBUG)
    
    # Rotating File handler
    max_bytes = log_config.get('max_size_kb', 500) * 1024  # Convert KB to bytes
    backup_count = log_config.get('backup_count', 4)
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_config['file_path'],
        mode='a',
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.getLevelName(log_config.get('file_level', 'DEBUG')))
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(name)s] - %(message)s', 
                                     datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.getLevelName(log_config.get('console_level', 'INFO')))
    console_formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Create logs directory if it doesn't exist
    log_path = Path(log_config.get('file_path', 'logs/home_temperature_control.log'))
    log_path.parent.mkdir(exist_ok=True)
    
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_config.get('console_level', 'INFO'))
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', 
                                        datefmt='%H:%M:%S')
    console_handler.setFormatter(console_formatter)
    handlers.append(console_handler)
    
    # File handler
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(log_config.get('file_level', 'DEBUG'))
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=handlers
    )

def load_config() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Load configuration and topology files."""
    config_path = Path(__file__).parent / 'config.yaml'
    topology_path = Path(__file__).parent / 'house_topology.yaml'
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        with open(topology_path, 'r') as f:
            topology = yaml.safe_load(f)
        return config, topology
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        raise

def save_topology(topology: Dict[str, Any]) -> None:
    """Save topology configuration to file."""
    topology_path = Path(__file__).parent / 'house_topology.yaml'
    try:
        with open(topology_path, 'w') as f:
            yaml.dump(topology, f, default_flow_style=False)
    except Exception as e:
        logger.error(f"Error saving topology: {str(e)}")
        raise
