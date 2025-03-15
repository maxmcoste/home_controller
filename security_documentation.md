# Security Utilities Documentation

## Overview

The Security Utilities module provides functionality for secure token generation and validation in the home temperature control system. It implements a time-based token authentication mechanism to ensure that only authorized commands are executed by the system.

## Class: SecurityUtils

### Purpose

The `SecurityUtils` class handles security operations for the home temperature control system, focusing on token-based authentication to verify command authenticity.

### Initialization

```python
security = SecurityUtils(control_pin="your_secret_pin")
```

**Parameters:**
- `control_pin` (str, optional): A secret PIN used for token generation and validation. If not provided, security features will be non-functional.

### Methods

#### generate_token

```python
token = security.generate_token(timestamp=None)
```

Generates a security token based on the control PIN and timestamp.

**Parameters:**
- `timestamp` (str, optional): A string representation of a UNIX timestamp. If not provided, the current time will be used.

**Returns:**
- A hexadecimal string representing the generated security token, or `None` if no control PIN is configured.

**Example:**
```python
security = SecurityUtils(control_pin="1234")
token = security.generate_token()  # Uses current time
print(f"Generated token: {token}")
```

#### validate_token

```python
is_valid = security.validate_token(token, timestamp_str)
```

Validates a security token against a timestamp and the control PIN.

**Parameters:**
- `token` (str): The security token to validate.
- `timestamp_str` (str): The timestamp string used to generate the token.

**Returns:**
- `True` if the token is valid and the timestamp is within 30 seconds of the current time, `False` otherwise.

**Security Features:**
- Implements constant-time comparison to prevent timing attacks
- Rejects tokens older than 30 seconds to prevent replay attacks
- Logs security events for monitoring and auditing

**Example:**
```python
security = SecurityUtils(control_pin="1234")
timestamp = str(int(time.time()))
token = security.generate_token(timestamp)

# Later verification
is_valid = security.validate_token(token, timestamp)
if is_valid:
    print("Token is valid")
else:
    print("Token is invalid or expired")
```

## Security Considerations

1. **Token Expiration**: Tokens are valid for only 30 seconds to mitigate replay attacks.
2. **Secure PIN Storage**: The control PIN should be securely stored and not hardcoded in application files.
3. **Constant-time Comparison**: Prevents timing attacks by ensuring token comparison takes the same amount of time regardless of where characters differ.
4. **Logging**: Security events are logged for audit purposes.

## Integration Example

```python
import time
from security_utils import SecurityUtils

# Initialize security with a control PIN
security = SecurityUtils(control_pin="secure_pin_123")

# When sending a command
timestamp = str(int(time.time()))
token = security.generate_token(timestamp)

# Include token and timestamp with the command
command_data = {
    "action": "set_temperature",
    "value": 72,
    "timestamp": timestamp,
    "token": token
}

# On the receiving end
def process_command(command_data):
    # Extract security information
    token = command_data.get("token")
    timestamp = command_data.get("timestamp")
    
    # Validate security token
    if not security.validate_token(token, timestamp):
        print("Security validation failed, rejecting command")
        return False
        
    # Process the valid command
    print(f"Setting temperature to {command_data['value']}°F")
    return True
```

## Best Practices

1. Never transmit the control PIN over the network
2. Update the control PIN regularly
3. Use HTTPS for all API communications involving security tokens
4. Monitor logs for unusual validation failures which may indicate attack attempts
