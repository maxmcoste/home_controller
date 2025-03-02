import hashlib
import hmac
import time
import logging
from typing import Optional

logger = logging.getLogger('home_temperature_control')

class SecurityUtils:
    """Utility class for security operations like token validation."""
    
    def __init__(self, control_pin=None):
        """Initialize with optional control PIN."""
        self.control_pin = control_pin
    
    def validate_token(self, token, timestamp_str):
        """
        Validate a security token against a timestamp and the control PIN.
        
        The token is expected to be a hash of timestamp + control_pin.
        """
        if not self.control_pin:
            logger.warning("Control PIN not configured. Security validation failed.")
            return False
            
        try:
            # Verify the timestamp is recent (within 30 seconds)
            current_time = int(time.time())
            timestamp = int(timestamp_str)
            if abs(current_time - timestamp) > 30:
                logger.warning(f"Token timestamp expired: {abs(current_time - timestamp)}s old")
                return False
                
            # Compute expected token
            expected = hashlib.sha256(f"{timestamp_str}{self.control_pin}".encode()).hexdigest()
            
            # Constant-time comparison to prevent timing attacks
            is_valid = len(token) == len(expected) and all(
                a == b for a, b in zip(token, expected)
            )
            
            if not is_valid:
                logger.warning("Invalid security token provided")
                
            return is_valid
            
        except Exception as e:
            logger.error(f"Error validating token: {str(e)}")
            return False
    
    def generate_token(self):
        """
        Generate a token for testing purposes.
        Returns token and timestamp.
        """
        if not self.control_pin:
            return None, None
            
        timestamp = str(int(time.time()))
        token = hashlib.sha256(f"{timestamp}{self.control_pin}".encode()).hexdigest()
        return token, timestamp
