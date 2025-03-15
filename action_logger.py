#!/usr/bin/env python3
"""
Action Logger for Home Temperature Control System

This module provides functions to log different types of actions performed by
the temperature control system, such as temperature changes, heater operations,
system events, and user interactions.
"""
import logging
import json
import time
import os
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, Union
from pathlib import Path

class ActionType(Enum):
    """Types of actions that can be logged"""
    TEMPERATURE_CHANGE = "temperature_change"
    HEATER_OPERATION = "heater_operation"
    SYSTEM_EVENT = "system_event"
    USER_INTERACTION = "user_interaction"
    API_REQUEST = "api_request"
    ERROR = "error"
    
class ActionLogger:
    """Logger for system actions with structured data"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the action logger.
        
        Args:
            config: Optional configuration dictionary with logging settings
        """
        self.config = config or {}
        self.logger = logging.getLogger('home_temperature_control.actions')
        
        # Set up file logging for actions
        self._setup_file_logger()
        
        # Track if we're also writing to a database
        self.db_enabled = self.config.get('action_log', {}).get('db_enabled', False)
        
        # Initialize database connection if enabled
        if self.db_enabled:
            try:
                self._setup_db_connection()
            except Exception as e:
                self.db_enabled = False
                self.logger.error(f"Failed to set up database connection for action logging: {e}")
    
    def _setup_file_logger(self):
        """Set up file-based action logging"""
        log_config = self.config.get('action_log', {})
        
        # Create action log directory if needed
        log_dir = Path(log_config.get('file_path', 'logs/actions'))
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # File path with date-based naming
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = log_dir / f"actions_{today}.log"
        
        # Create file handler with rotation
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Create formatter that outputs JSON
        formatter = logging.Formatter('%(message)s')
        file_handler.setFormatter(formatter)
        
        # Add handler to logger
        self.logger.addHandler(file_handler)
    
    def _setup_db_connection(self):
        """Set up database connection for action logging"""
        # This is a placeholder for database setup code
        # In a real implementation, you would connect to your database here
        pass
    
    def log_action(self, action_type: Union[ActionType, str], data: Dict[str, Any], 
                   room_id: Optional[str] = None, user: Optional[str] = None,
                   success: bool = True) -> None:
        """
        Log an action with structured data.
        
        Args:
            action_type: Type of action being logged
            data: Dictionary containing action-specific data
            room_id: Optional room identifier related to the action
            user: Optional user identifier who performed the action
            success: Whether the action was successful
        """
        if isinstance(action_type, ActionType):
            action_type = action_type.value
            
        # Build the action record
        action = {
            "timestamp": datetime.now().isoformat(),
            "unix_time": time.time(),
            "action_type": action_type,
            "data": data,
            "success": success
        }
        
        # Add optional fields if provided
        if room_id:
            action["room_id"] = room_id
        if user:
            action["user"] = user
        
        # Add hostname and process id for debugging
        action["hostname"] = os.uname().nodename
        action["process_id"] = os.getpid()
        
        # Log to file
        self.logger.info(json.dumps(action))
        
        # Log to database if enabled
        if self.db_enabled:
            self._log_to_db(action)
    
    def _log_to_db(self, action: Dict[str, Any]) -> None:
        """Log action to database"""
        # This is a placeholder for database logging code
        # In a real implementation, you would insert the action into your database
        pass
    
    def log_temperature_change(self, room_id: str, old_temp: float, new_temp: float,
                              source: str = "sensor", **kwargs) -> None:
        """
        Log a temperature change event.
        
        Args:
            room_id: ID of the room with temperature change
            old_temp: Previous temperature reading
            new_temp: New temperature reading
            source: Source of the temperature change (e.g., 'sensor', 'manual')
            **kwargs: Additional data to include in the log
        """
        data = {
            "old_temperature": old_temp,
            "new_temperature": new_temp,
            "difference": round(new_temp - old_temp, 2),
            "source": source
        }
        data.update(kwargs)
        
        self.log_action(ActionType.TEMPERATURE_CHANGE, data, room_id=room_id)
    
    def log_heater_operation(self, room_id: str, status: bool, 
                            current_temp: Optional[float] = None,
                            target_temp: Optional[float] = None,
                            user: Optional[str] = None, **kwargs) -> None:
        """
        Log a heater operation event.
        
        Args:
            room_id: ID of the room whose heater changed
            status: New status of heater (True=on, False=off)
            current_temp: Optional current room temperature
            target_temp: Optional target temperature
            user: Optional user who triggered the operation
            **kwargs: Additional data to include in the log
        """
        data = {
            "heater_status": "ON" if status else "OFF"
        }
        
        if current_temp is not None:
            data["current_temperature"] = current_temp
            
        if target_temp is not None:
            data["target_temperature"] = target_temp
        
        data.update(kwargs)
        
        self.log_action(ActionType.HEATER_OPERATION, data, room_id=room_id, user=user)
    
    def log_user_interaction(self, action: str, user: Optional[str] = None,
                           room_id: Optional[str] = None, details: Dict[str, Any] = None,
                           success: bool = True) -> None:
        """
        Log a user interaction with the system.
        
        Args:
            action: Description of the action performed
            user: Optional identifier of the user
            room_id: Optional room ID if the action relates to a specific room
            details: Optional additional details about the action
            success: Whether the interaction was successful
        """
        data = {
            "action": action
        }
        
        if details:
            data.update(details)
        
        self.log_action(ActionType.USER_INTERACTION, data, room_id=room_id, 
                      user=user, success=success)
    
    def log_system_event(self, event: str, details: Dict[str, Any] = None,
                        success: bool = True) -> None:
        """
        Log a system event.
        
        Args:
            event: Description of the system event
            details: Optional additional details about the event
            success: Whether the event was successful
        """
        data = {
            "event": event
        }
        
        if details:
            data.update(details)
        
        self.log_action(ActionType.SYSTEM_EVENT, data, success=success)
    
    def log_api_request(self, endpoint: str, method: str, status_code: int,
                       params: Dict[str, Any] = None, body: Dict[str, Any] = None,
                       user: Optional[str] = None, duration_ms: Optional[float] = None) -> None:
        """
        Log an API request.
        
        Args:
            endpoint: API endpoint that was accessed
            method: HTTP method used (GET, POST, etc.)
            status_code: HTTP status code returned
            params: Optional query parameters
            body: Optional request body
            user: Optional user who made the request
            duration_ms: Optional duration of the request in milliseconds
        """
        data = {
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "success": 200 <= status_code < 300
        }
        
        if params:
            data["params"] = params
        
        if body:
            # Sanitize any sensitive data in the body
            sanitized_body = self._sanitize_data(body)
            data["body"] = sanitized_body
            
        if duration_ms is not None:
            data["duration_ms"] = duration_ms
        
        self.log_action(ActionType.API_REQUEST, data, user=user)
    
    def _sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize sensitive data before logging.
        
        Args:
            data: Dictionary containing potentially sensitive data
            
        Returns:
            Dictionary with sensitive data masked
        """
        # Make a copy of the data to avoid modifying the original
        sanitized = json.loads(json.dumps(data))
        
        # List of fields to sanitize
        sensitive_fields = ["password", "token", "secret", "key", "pin"]
        
        def sanitize_dict(d):
            for k, v in d.items():
                if isinstance(v, dict):
                    sanitize_dict(v)
                elif isinstance(k, str) and any(field in k.lower() for field in sensitive_fields):
                    d[k] = "********"
        
        sanitize_dict(sanitized)
        return sanitized
    
    def log_error(self, error_message: str, exception: Optional[Exception] = None,
                room_id: Optional[str] = None, details: Dict[str, Any] = None) -> None:
        """
        Log an error.
        
        Args:
            error_message: Description of the error
            exception: Optional exception object
            room_id: Optional room ID if the error relates to a specific room
            details: Optional additional details about the error
        """
        data = {
            "message": error_message
        }
        
        if exception:
            data["exception_type"] = type(exception).__name__
            data["exception_message"] = str(exception)
        
        if details:
            data.update(details)
        
        self.log_action(ActionType.ERROR, data, room_id=room_id, success=False)

# Get or create function is useful and could be used by the application
def get_action_logger(config: Dict[str, Any] = None) -> ActionLogger:
    """
    Get or create an action logger instance.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        ActionLogger instance
    """
    # Configure logging if it hasn't been configured already
    if not logging.root.handlers:
        logging.basicConfig(level=logging.INFO)
    
    return ActionLogger(config)
