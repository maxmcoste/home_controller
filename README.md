# Home Temperature Control System

A FastAPI-based application for managing home temperature control and topology. The system provides real-time temperature monitoring, automated heater control, and a modern web interface for easy configuration and management.

## Features

- Real-time temperature monitoring and automated heater control
- House topology management (add/edit/delete rooms)
- Modern web UI for configuration
- Secure control API endpoints with PIN protection
- Configurable temperature thresholds and check intervals
- Detailed logging system with file rotation
- Temperature checks in seconds (configurable)
- REST API with Swagger/ReDoc documentation

## Installation

1. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

1. Regular start:
   ```bash
   python home_topology_api.py
   ```

2. Specify custom port:
   ```bash
   python home_topology_api.py --port 8080
   ```

3. Control commands:
   ```bash
   # Stop the application
   python control_client.py stop

   # Restart the application
   python control_client.py restart
   ```

The server will start on `http://localhost:8000` by default.

### API Documentation

Access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### Room Status and Control
- `GET /rooms` - Get status of all rooms
- `GET /room/{room_id}` - Get status of a specific room
- `GET /rooms/by-floor/{floor}` - Get all rooms on a specific floor
- `GET /rooms/by-type/{room_type}` - Get all rooms of a specific type
- `PUT /room/{room_id}/target` - Set target temperature for a room

### House Topology Management
- `GET /topology` - Get current house topology
- `POST /topology/rooms/{room_type}` - Add a new room
- `PUT /topology/rooms/{room_id}` - Update room details
- `DELETE /topology/rooms/{room_id}` - Delete a room

### System Control (PIN Protected)
- `POST /control/stop` - Stop the application
- `POST /control/restart` - Restart the application

## Configuration

The application uses two YAML configuration files:

### 1. House Topology (`house_topology.yaml`)

Defines the structure of your house, including all rooms and their properties:

```yaml
rooms:
  living_rooms:
    - name: "main living"
      id: "living_main"
      floor: 1
      
  bathrooms:
    - name: "floor1 big bath"
      id: "bath_f1_big"
      floor: 1
    - name: "floor1 small bath"
      id: "bath_f1_small"
      floor: 1
    - name: "floor2 bath"
      id: "bath_f2"
      floor: 2
      
  bedrooms:
    - name: "main"
      id: "bedroom_main"
      floor: 2
    - name: "bea"
      id: "bedroom_bea"
      floor: 2
    - name: "boys"
      id: "bedroom_boys"
      floor: 2
```

### 2. Technical Configuration (`config.yaml`)

Manages technical settings and default values:

```yaml
# Temperature check interval in seconds
temperature_check_interval_seconds: 5

# Temperature constraints
min_allowed_temperature: 15.0
max_allowed_temperature: 30.0

# Default temperatures by room type
default_temperatures:
  living_rooms: 21.0
  bathrooms: 22.0
  bedrooms: 20.0

# Sensor and heater URL patterns
device_urls:
  sensor_pattern: "http://sensor-{room_id}.local/temperature"
  heater_pattern: "http://heater-{room_id}.local/control"

# Room specific overrides (optional)
room_overrides:
  bedroom_main:
    target_temperature: 19.0  # override default bedroom temperature

# API configuration
api:
  host: "0.0.0.0"
  port: 8000
  control_pin: "130376"  # PIN for secure control APIs

# Logging configuration
logging:
  file_path: "logs/home_temperature_control.log"
  max_size_kb: 500  # Maximum size of each log file
  backup_count: 4   # Number of backup files to keep
  console_level: "INFO"
  file_level: "DEBUG"
```

To modify your house structure, update the `house_topology.yaml` file. For technical settings and temperature preferences, modify the `config.yaml` file.

## Logging System

The application uses a rotating log system to manage log files efficiently:

- Main log file: `logs/home_temperature_control.log`
- Maximum file size: 500 KB
- Backup files: 4 (named `.log.1` through `.log.4`)
- Log levels:
  - File logging: DEBUG level (detailed information)
  - Console logging: INFO level (important events)

To view logs in real-time:
```bash
tail -f logs/home_temperature_control.log
```

## Troubleshooting

### Common Issues

1. Port already in use:
   ```bash
   lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill
   ```

2. Application not starting:
   - Check if the logs directory exists and is writable
   - Verify configuration files are valid YAML
   - Ensure all dependencies are installed

3. Temperature sensors not responding:
   - Verify sensor URLs are accessible
   - Check network connectivity
   - Review logs for connection errors

4. Control API authentication failures:
   - Verify the correct PIN is being used
   - Check if the token has expired (5-minute validity)
   - Ensure the timestamp in the request is current

### Log File Management

- Old log files are automatically rotated when size limit is reached
- No manual cleanup required
- Total storage used will not exceed 2.5 MB (5 files × 500 KB)

For development and debugging:
- Set `file_level: "DEBUG"` in config.yaml for more detailed logs
- Use the Swagger UI at `/docs` to test API endpoints
- Monitor real-time temperature checks in the logs

## API Response Examples

### Get All Rooms Status
```json
{
    "living_room": {
        "current_temperature": 19.5,
        "target_temperature": 21.0,
        "heater_status": true
    },
    "bedroom": {
        "current_temperature": 20.2,
        "target_temperature": 20.0,
        "heater_status": false
    }
}
```

### Set Target Temperature
Request:
```bash
curl -X PUT "http://localhost:8000/room/living_room/target?temperature=22.0"
```

Response:
```json
{
    "message": "Target temperature for living_room set to 22.0°C"
}
```
