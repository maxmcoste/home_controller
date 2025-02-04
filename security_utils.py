import hashlib
import hmac
import time
from typing import Optional

class SecurityUtils:
    def __init__(self, pin: str):
        self.pin = pin
        self._token_cache = {}
        self._token_expiry = 300  # 5 minutes

    def generate_token(self, timestamp: str) -> str:
        """Generate a secure token using PIN and timestamp."""
        message = f"{self.pin}:{timestamp}".encode('utf-8')
        return hmac.new(self.pin.encode('utf-8'), message, hashlib.sha256).hexdigest()

    def validate_token(self, token: str, timestamp: str) -> bool:
        """Validate a token against PIN and timestamp."""
        # Check if token has been used before (prevent replay attacks)
        if token in self._token_cache:
            return False

        # Clean expired tokens from cache
        current_time = time.time()
        self._token_cache = {t: ts for t, ts in self._token_cache.items() 
                           if current_time - ts < self._token_expiry}

        # Verify timestamp is within acceptable range (prevent replay attacks)
        try:
            token_time = float(timestamp)
            if abs(current_time - token_time) > self._token_expiry:
                return False
        except ValueError:
            return False

        # Verify token
        expected_token = self.generate_token(timestamp)
        is_valid = hmac.compare_digest(token, expected_token)

        # If valid, add to cache
        if is_valid:
            self._token_cache[token] = current_time

        return is_valid
