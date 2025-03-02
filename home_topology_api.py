from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import logging
import argparse
from typing import Optional, Dict
import sys
import os
from security_utils import SecurityUtils
from config_loader import load_config, setup_logging, save_topology
from temperature_control import TemperatureController
from contextlib import asynccontextmanager

# Initialize logging with default configuration until we load the config file
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('home_temperature_control')

@asynccontextmanager
async def lifespan(app: FastAPI):
    global security, controller
    try:
        logger.info("=== Home Temperature Control System Starting ===")
        # Load configuration and setup logging
        config, topology = load_config()
        setup_logging(config)
        # Initialize security
        control_pin = config.get('api', {}).get('control_pin')
        if not control_pin:
            logger.warning("No control PIN configured. Control APIs will be disabled.")
        security = SecurityUtils(control_pin)
        # Initialize temperature controller
        controller = TemperatureController(config)
        controller.initialize_rooms(topology)
        logger.info(f"Initialized {len(controller.rooms)} rooms")
        # Start temperature control scheduler
        controller.start_scheduler()
        logger.info("System initialization completed successfully")
        
        yield
    finally:
        logger.info("=== Home Temperature Control System Shutting Down ===")
        # ...optional cleanup code...

# Initialize FastAPI app
app = FastAPI(title="Home Temperature Control System", lifespan=lifespan)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    """Redirect root to static index.html"""
    return RedirectResponse(url="/static/index.html")

# Global instances
controller: Optional[TemperatureController] = None
security: Optional[SecurityUtils] = None

class TemperatureReading(BaseModel):
    temperature: float

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
        save_topology(topology)
        
        # Reinitialize rooms
        config, _ = load_config()
        controller.initialize_rooms(topology)
        
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
        save_topology(topology)
        
        # Reinitialize rooms
        config, _ = load_config()
        controller.initialize_rooms(topology)
        
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
        save_topology(topology)
        
        # Reinitialize rooms
        config, _ = load_config()
        controller.initialize_rooms(topology)
        
        return {"message": "Room deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting room: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/rooms")
def get_rooms():
    """Get status of all rooms."""
    return {
        room_id: {
            "name": room.info.name,
            "floor": room.info.floor,
            "room_type": room.info.room_type,
            "current_temperature": room.current_temp,
            "target_temperature": room.target_temp,
            "heater_status": room.heater_status
        }
        for room_id, room in controller.rooms.items()
    }

@app.get("/rooms/floor/{floor}")
def get_rooms_by_floor(floor: int):
    """Get status of all rooms on a specific floor."""
    floor_rooms = {room.info.id: room for room in controller.rooms.values() if room.info.floor == floor}
    if not floor_rooms:
        raise HTTPException(status_code=404, detail=f"No rooms found on floor {floor}")
    
    return {
        room_id: {
            "name": room.info.name,
            "room_type": room.info.room_type,
            "current_temperature": room.current_temp,
            "target_temperature": room.target_temp,
            "heater_status": room.heater_status
        }
        for room_id, room in floor_rooms.items()
    }

@app.get("/rooms/type/{room_type}")
def get_rooms_by_type(room_type: str):
    """Get status of all rooms of a specific type."""
    type_rooms = {room.info.id: room for room in controller.rooms.values() if room.info.room_type == room_type}
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

class ControlRequest(BaseModel):
    timestamp: str
    token: str

@app.post("/control/stop")
def stop_application(request: ControlRequest):
    """Stop the application securely."""
    if not security:
        raise HTTPException(status_code=503, detail="Control APIs are not configured")
    
    if not security.validate_token(request.token, request.timestamp):
        raise HTTPException(status_code=401, detail="Invalid security token")
    
    logger.info("Received stop signal. Shutting down...")
    os._exit(0)

@app.post("/control/restart")
def restart_application(request: ControlRequest):
    """Restart the application securely."""
    if not security:
        raise HTTPException(status_code=503, detail="Control APIs are not configured")
    
    if not security.validate_token(request.token, request.timestamp):
        raise HTTPException(status_code=401, detail="Invalid security token")
    
    logger.info("Received restart signal. Restarting...")
    os.execv(sys.executable, ['python'] + sys.argv)

@app.post("/room/{room_id}/temperature")
def update_room_temperature(room_id: str, reading: TemperatureReading):
    """Receive temperature reading from test simulator."""
    logger.debug(f"Received temperature update request for room {room_id}: {reading.temperature}°C")
    
    if not controller:
        logger.error("Temperature controller not initialized")
        raise HTTPException(status_code=500, detail="Temperature controller not initialized")
    
    if room_id not in controller.rooms:
        logger.error(f"Room {room_id} not found in controller rooms: {list(controller.rooms.keys())}")
        raise HTTPException(status_code=404, detail=f"Room {room_id} not found")
    
    room = controller.rooms[room_id]
    room.current_temp = reading.temperature
    logger.info(f"Updated temperature for {room.info.name} (ID: {room_id}): {reading.temperature}°C")
    
    return {"status": "success", "room_id": room_id, "temperature": room.current_temp}


@app.get("/room/{room_id}")
def get_room(room_id: str):
    """Get status of a specific room."""
    if room_id not in controller.rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = controller.rooms[room_id]
    return {
        "name": room.info.name,
        "floor": room.info.floor,
        "room_type": room.info.room_type,
        "current_temperature": room.current_temp,
        "target_temperature": room.target_temp,
        "heater_status": room.heater_status
    }

@app.put("/rooms/{room_id}/temperature")
def set_target_temperature(room_id: str, temperature: float):
    """Set target temperature for a room."""
    if room_id not in controller.rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if not (controller.min_temp <= temperature <= controller.max_temp):
        raise HTTPException(
            status_code=400,
            detail=f"Temperature must be between {controller.min_temp}°C and {controller.max_temp}°C"
        )
    
    controller.rooms[room_id].target_temp = temperature
    return {"message": f"Target temperature set to {temperature}°C"}

if __name__ == "__main__":
    import uvicorn
    import atexit
    
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
