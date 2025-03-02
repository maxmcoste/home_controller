import yaml
import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Tuple, Any

logger = logging.getLogger('home_temperature_control')

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
        logger.info("Topology saved successfully")
    except Exception as e:
        logger.error(f"Error saving topology: {str(e)}")
        raise

def setup_logging(config: dict) -> None:
    """Setup logging configuration."""
    log_config = config.get('logging', {})
    log_path = Path(log_config.get('file_path', 'logs/home_temperature_control.log'))
    
    # Create logs directory if it doesn't exist
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    logger = logging.getLogger('home_temperature_control')
    logger.setLevel(logging.DEBUG)
    logger.handlers = []  # Clear existing handlers
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=log_config.get('max_size_kb', 500) * 1024,
        backupCount=log_config.get('backup_count', 4)
    )
    file_handler.setLevel(getattr(logging, log_config.get('file_level', 'DEBUG').upper()))
    file_handler.setFormatter(file_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_config.get('console_level', 'INFO').upper()))
    console_handler.setFormatter(console_formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
