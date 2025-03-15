from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import logging
from logging import handlers
from typing import Dict, Optional, List
from pathlib import Path
import schedule
import time
from threading import Thread
import yaml
from pathlib import Path
from dataclasses import dataclass
import random

def setup_logging(config: dict) -> logging.Logger:
    """Setup logging configuration for both file and console output."""
    log_config = config.get('logging', {})
    log_path = Path(log_config.get('file_path', 'logs/home_temperature_control.log'))
    
    # Create logs directory if it doesn't exist
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger('home_temperature_control')
    logger.setLevel(logging.DEBUG)
    
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
        maxBytes=log_config.get('max_size_mb', 10) * 1024 * 1024,
        backupCount=log_config.get('backup_count', 5)
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

# Initialize logging with default configuration until we load the config file
# Remove duplicate logging configuration
logger = logging.getLogger('home_temperature_control')
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%H:%M:%S'))
logger.addHandler(console_handler)

# Startup message
logger.info("Starting Home Temperature Control System initialization...")

app = FastAPI(title="Home Temperature Control System")

# Add CORS middleware to allow cross-origin requests from the web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", include_in_schema=True)
async def root():
    """Root endpoint - provides basic system information and links."""
    return {
        "name": "Home Temperature Control System",
        "version": "1.0.0",
        "description": "API for monitoring and controlling home temperature",
        "endpoints": {
            "documentation": "/docs",
            "all_rooms": "/rooms",
            "room_by_id": "/room/{room_id}",
            "rooms_by_floor": "/rooms/by-floor/{floor}",
            "rooms_by_type": "/rooms/by-type/{room_type}",
            "house_topology": "/topology"
        },
        "status": "running"
    }

# Alternative approach with redirect to docs
@app.get("/home", include_in_schema=True)
async def home_redirect():
    """Redirect to the API documentation."""
    return RedirectResponse(url="/docs")

@dataclass
class RoomInfo:
    id: str
    name: str
    floor: int
    room_type: str

class Room:
    def __init__(self, room_info: RoomInfo, sensor_url: str, heater_url: str, target_temp: float):
        self.info = room_info
        self.sensor_url = sensor_url
        self.heater_url = heater_url
        self.target_temp = target_temp
        self.current_temp: Optional[float] = None
        self.heater_status: bool = False

class TemperatureReading(BaseModel):
    room_name: str
    temperature: float
    timestamp: str

class HeaterStatus(BaseModel):
    room_name: str
    status: bool

class RoomCreate(BaseModel):
    name: str
    id: str
    floor: int

class RoomUpdate(BaseModel):
    name: Optional[str] = None
    floor: Optional[int] = None

# Store rooms configuration
rooms: Dict[str, Room] = {}

def load_config():
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

def get_room_info(room_data: dict, room_type: str) -> RoomInfo:
    """Create RoomInfo from room data."""
    return RoomInfo(
        id=room_data['id'],
        name=room_data['name'],
        floor=room_data['floor'],
        room_type=room_type
    )

def initialize_rooms():
    """Initialize rooms from configuration and topology files."""
    config, topology = load_config()
    
    # Get URL patterns
    sensor_pattern = config['device_urls']['sensor_pattern']
    heater_pattern = config['device_urls']['heater_pattern']
    
    # Process each room type in the topology
    for room_type, room_list in topology['rooms'].items():
        default_temp = config['default_temperatures'][room_type]
        
        for room_data in room_list:
            room_id = room_data['id']
            room_info = get_room_info(room_data, room_type)
            
            # Get room-specific overrides if they exist
            target_temp = config.get('room_overrides', {}).get(room_id, {}).get(
                'target_temperature', default_temp
            )
            
            # Create room with formatted URLs
            rooms[room_id] = Room(
                room_info=room_info,
                sensor_url=sensor_pattern.format(room_id=room_id),
                heater_url=heater_pattern.format(room_id=room_id),
                target_temp=target_temp
            )
            logger.info(f"Initialized {room_info.name} (ID: {room_id}) with target temperature {target_temp}°C")
    
    return config

def get_temperature(room: Room) -> Optional[float]:
    """Fetch temperature from room sensor."""
    try:
        logger.debug(f"Requesting temperature for {room.info.name} (ID: {room.info.id}) from {room.sensor_url}")
        response = requests.get(room.sensor_url, timeout=5)
        response.raise_for_status()
        temp = response.json()["temperature"]
        logger.info(f"Temperature reading for {room.info.name}: {temp}°C")
        return temp
    except Exception as e:
        logger.error(f"Error reading temperature for {room.info.name} (ID: {room.info.id}): {str(e)}")
        return None

def control_heater(room: Room, status: bool) -> bool:
    """Control room heater."""
    try:
        action = "turn ON" if status else "turn OFF"
        logger.debug(f"Attempting to {action} heater for {room.info.name} (ID: {room.info.id})")
        payload = {"status": status}
        response = requests.post(room.heater_url, json=payload, timeout=5)
        response.raise_for_status()
        success = response.json()["success"]
        if success:
            logger.info(f"Successfully {action}d heater for {room.info.name}")
        else:
            logger.warning(f"Failed to {action} heater for {room.info.name} - API returned success=false")
        return success
    except Exception as e:
        logger.error(f"Error controlling heater for {room.info.name} (ID: {room.info.id}): {str(e)}")
        return False

def check_and_control_temperature():
    """Check temperatures and control heaters for all rooms."""
    logger.debug("Starting temperature check and control cycle")
    for room in rooms.values():
        logger.debug(f"Processing room: {room.info.name} (ID: {room.info.id})")
        temp = get_temperature(room)
        if temp is not None:
            room.current_temp = temp
            
            # Control heater based on temperature
            should_heat = temp < room.target_temp
            if should_heat != room.heater_status:
                logger.debug(
                    f"{room.info.name}: Current temp {temp}°C is {'below' if should_heat else 'above'} "
                    f"target temp {room.target_temp}°C. Adjusting heater."
                )
                if control_heater(room, should_heat):
                    room.heater_status = should_heat
    logger.debug("Completed temperature check and control cycle")

def run_scheduler():
    """Run the scheduler in a separate thread."""
    while True:
        schedule.run_pending()
        time.sleep(1)

@app.on_event("startup")
async def startup_event():
    """Initialize the application."""
    global logger  # We'll update the logger with the configuration
    
    try:
        config = initialize_rooms()
        # Setup logging with configuration
        logger = setup_logging(config)
        logger.info("=== Home Temperature Control System Starting ===")
        logger.info(f"Initialized {len(rooms)} rooms")
        
        # Schedule temperature checks based on configuration
        # Get interval in seconds and convert to minutes for scheduling
        interval_seconds = config.get('temperature_check_interval_seconds', 300)
        interval_minutes = max(1, interval_seconds // 60)  # Ensure at least 1 minute
        
        logger.info(f"Scheduling temperature checks every {interval_minutes} minute(s) " +
                   f"({interval_seconds} seconds)")
        schedule.every(interval_minutes).minutes.do(check_and_control_temperature)
        
        # Start the scheduler in a separate thread
        Thread(target=run_scheduler, daemon=True).start()
        logger.info("Temperature control scheduler started")
        logger.info("System initialization completed successfully")
    except Exception as e:
        logger.critical(f"Failed to initialize system: {str(e)}")
        raise

@app.get("/rooms")
async def get_rooms():
    """Get status of all rooms."""
    return {
        room.info.id: {
            "name": room.info.name,
            "type": room.info.room_type,
            "floor": room.info.floor,
            "current_temperature": room.current_temp,
            "target_temperature": room.target_temp,
            "heater_status": room.heater_status
        }
        for room in rooms.values()
    }

@app.get("/rooms/by-floor/{floor}")
async def get_rooms_by_floor(floor: int):
    """Get status of all rooms on a specific floor."""
    floor_rooms = {room.info.id: room for room in rooms.values() if room.info.floor == floor}
    if not floor_rooms:
        raise HTTPException(status_code=404, detail=f"No rooms found on floor {floor}")
    
    return {
        room_id: {
            "name": room.info.name,
            "type": room.info.room_type,
            "current_temperature": room.current_temp,
            "target_temperature": room.target_temp,
            "heater_status": room.heater_status
        }
        for room_id, room in floor_rooms.items()
    }

@app.get("/rooms/by-type/{room_type}")
async def get_rooms_by_type(room_type: str):
    """Get status of all rooms of a specific type."""
    type_rooms = {room.info.id: room for room in rooms.values() if room.info.room_type == room_type}
    if not type_rooms:
        raise HTTPException(status_code=404, detail=f"No rooms found of type {room_type}")
    
    return {
        room_id: {
            "name": room.info.name,
            "floor": room.info.floor,
            "current_temperature": room.current_temp,
            "target_temperature": room.target_temp,
            "heater_status": room.heater_status
        }
        for room_id, room in type_rooms.items()
    }

@app.get("/topology")
def get_topology():
    """Get the current house topology."""
    try:
        _, topology = load_config()
        return topology
    except Exception as e:
        logger.error(f"Error getting topology: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/topology/rooms/{room_type}")
def add_room(room_type: str, room: RoomCreate):
    """Add a new room to the specified room type."""
    try:
        _, topology = load_config()
        
        # Validate room type
        if room_type not in topology['rooms']:
            raise HTTPException(status_code=400, detail=f"Invalid room type: {room_type}")
        
        # Check for duplicate room ID
        for rt in topology['rooms'].values():
            for existing_room in rt:
                if existing_room['id'] == room.id:
                    raise HTTPException(status_code=400, detail=f"Room ID already exists: {room.id}")
        
        # Add the new room
        new_room = {
            'name': room.name,
            'id': room.id,
            'floor': room.floor
        }
        topology['rooms'][room_type].append(new_room)
        
        # Save the updated topology
        topology_path = Path(__file__).parent / 'house_topology.yaml'
        with open(topology_path, 'w') as f:
            yaml.dump(topology, f, default_flow_style=False)
        
        # Reinitialize rooms
        initialize_rooms()
        
        return {"message": "Room added successfully", "room": new_room}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding room: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/topology/rooms/{room_id}")
def update_room(room_id: str, room_update: RoomUpdate):
    """Update an existing room's details."""
    try:
        _, topology = load_config()
        
        # Find and update the room
        room_found = False
        for room_type in topology['rooms']:
            for room in topology['rooms'][room_type]:
                if room['id'] == room_id:
                    if room_update.name is not None:
                        room['name'] = room_update.name
                    if room_update.floor is not None:
                        room['floor'] = room_update.floor
                    room_found = True
                    break
            if room_found:
                break
        
        if not room_found:
            raise HTTPException(status_code=404, detail=f"Room not found: {room_id}")
        
        # Save the updated topology
        topology_path = Path(__file__).parent / 'house_topology.yaml'
        with open(topology_path, 'w') as f:
            yaml.dump(topology, f, default_flow_style=False)
        
        # Reinitialize rooms
        initialize_rooms()
        
        return {"message": "Room updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating room: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/topology/rooms/{room_id}")
def delete_room(room_id: str):
    """Delete a room from the topology."""
    try:
        _, topology = load_config()
        
        # Find and delete the room
        room_found = False
        for room_type in topology['rooms']:
            for i, room in enumerate(topology['rooms'][room_type]):
                if room['id'] == room_id:
                    del topology['rooms'][room_type][i]
                    room_found = True
                    break
            if room_found:
                break
        
        if not room_found:
            raise HTTPException(status_code=404, detail=f"Room not found: {room_id}")
        
        # Save the updated topology
        topology_path = Path(__file__).parent / 'house_topology.yaml'
        with open(topology_path, 'w') as f:
            yaml.dump(topology, f, default_flow_style=False)
        
        # Reinitialize rooms
        initialize_rooms()
        
        return {"message": "Room deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting room: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/room/{room_id}")
async def get_room(room_id: str):
    """Get status of a specific room."""
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    room = rooms[room_id]
    return {
        "name": room.info.name,
        "type": room.info.room_type,
        "floor": room.info.floor,
        "current_temperature": room.current_temp,
        "target_temperature": room.target_temp,
        "heater_status": room.heater_status
    }

@app.put("/room/{room_id}/target")
async def set_target_temperature(room_id: str, temperature: float):
    """Set target temperature for a room."""
    config, _ = load_config()
    min_temp = config.get('min_allowed_temperature', 15)
    max_temp = config.get('max_allowed_temperature', 30)
    
    if room_id not in rooms:
        logger.warning(f"Attempt to set temperature for non-existent room ID: {room_id}")
        raise HTTPException(status_code=404, detail="Room not found")
    if not min_temp <= temperature <= max_temp:
        logger.warning(
            f"Invalid temperature setting attempted for {room_id}: {temperature}°C "
            f"(allowed range: {min_temp}-{max_temp}°C)"
        )
        raise HTTPException(
            status_code=400, 
            detail=f"Temperature must be between {min_temp} and {max_temp}°C"
        )
    
    room = rooms[room_id]
    old_temp = room.target_temp
    room.target_temp = temperature
    logger.info(
        f"Temperature target changed for {room.info.name} (ID: {room_id}): "
        f"{old_temp}°C -> {temperature}°C"
    )
    return {
        "message": f"Target temperature for {room.info.name} set to {temperature}°C",
        "room_id": room_id,
        "room_name": room.info.name,
        "new_temperature": temperature,
        "old_temperature": old_temp
    }

@app.get("/room/{room_id}/temperature")
async def get_room_temperature(room_id: str):
    """API endpoint for temperature sensors to report their readings."""
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Simulate temperature reading (in a real system, this would be from actual sensors)
    # Using this endpoint for testing and development
    current_temp = rooms[room_id].current_temp
    if current_temp is None:
        current_temp = rooms[room_id].target_temp + random.uniform(-2.0, 2.0)
        current_temp = round(current_temp, 1)
    
    return {
        "room_id": room_id,
        "temperature": current_temp,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

@app.post("/room/{room_id}/heater")
async def control_room_heater(room_id: str, data: dict):
    """API endpoint for controlling heaters."""
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # In a real system, this would control actual heater hardware
    # Using this endpoint for testing and development
    status = data.get("status", False)
    return {
        "room_id": room_id,
        "status": status,
        "success": True,
        "message": f"Heater {'activated' if status else 'deactivated'}"
    }

if __name__ == "__main__":
    import uvicorn
    import atexit
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Home Temperature Control System')
    parser.add_argument('--port', type=int, default=8000, help='Port to run the server on')
    args = parser.parse_args()
    
    def shutdown_handler():
        """Handle graceful shutdown logging."""
        logger.info("=== Home Temperature Control System Shutting Down ===")
    
    # Register shutdown handler
    atexit.register(shutdown_handler)
    
    # Start the application
    config, _ = load_config()
    api_config = config.get('api', {})
    host = api_config.get('host', '0.0.0.0')
    # Command line port takes precedence over config file
    uvicorn.run(app, host=host, port=args.port)
