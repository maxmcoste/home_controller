#!/usr/bin/env python3
"""
Temperature Simulator for Home Temperature Control System

This simulator creates mock temperature sensors and heaters for testing the system.
It simulates temperature changes based on heater status and environmental factors.
"""
import argparse
import logging
import time
import random
import threading
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from contextlib import asynccontextmanager
import yaml
from pathlib import Path
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [Simulator] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('temperature_simulator')

class HeaterRequest(BaseModel):
    status: bool

class RoomSimulator:
    def __init__(self, room_id, room_name, room_type, floor, target_temp, variation=1.0):
        self.room_id = room_id
        self.room_name = room_name
        self.room_type = room_type
        self.floor = floor
        self.target_temp = target_temp
        self.variation = variation
        self.current_temp = self._generate_initial_temp()
        self.heater_on = False
        self.last_update = time.time()
    
    def _generate_initial_temp(self):
        """Generate an initial temperature near the target temperature"""
        return self.target_temp - self.variation + (random.random() * self.variation * 2)
    
    def update_temperature(self, elapsed_seconds):
        """
        Update temperature based on elapsed time, heater status, and random factors
        
        If heater is on: temperature rises at ~1°C per minute
        If heater is off: temperature falls at ~0.5°C per minute
        Adding random variation for realism
        """
        minutes = elapsed_seconds / 60
        
        # Base rate of change per minute (heating or cooling)
        if self.heater_on:
            # Heating rate decreases as we approach or exceed target temp
            rate = max(0.1, 1.0 * (1 - (self.current_temp - self.target_temp + 2) / 10))
            change = rate * minutes
        else:
            # Cooling rate increases as we get further below target temp
            below_factor = max(0.1, min(1.5, (self.target_temp - self.current_temp) / 5))
            rate = 0.5 * below_factor
            change = -rate * minutes
        
        # Add random variation
        random_factor = random.uniform(-0.1, 0.1) * minutes
        
        self.current_temp += change + random_factor
        self.last_update = time.time()
        
        return self.current_temp

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("=== Temperature Simulator Starting ===")
        yield
    finally:
        logger.info("=== Temperature Simulator Shutting Down ===")

app = FastAPI(title="Temperature Simulator", lifespan=lifespan)
rooms = {}  # Store room simulators

def load_topology():
    """Load room topology from file"""
    try:
        config_path = Path(__file__).parent / 'config.yaml'
        topology_path = Path(__file__).parent / 'house_topology.yaml'
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        with open(topology_path, 'r') as f:
            topology = yaml.safe_load(f)
        
        # Create room simulators
        for room_type, room_list in topology['rooms'].items():
            default_temp = config['default_temperatures'][room_type]
            variation = config.get('simulator', {}).get('temperature_variation', 2.0)
            
            for room in room_list:
                room_id = room['id']
                target_temp = config.get('room_overrides', {}).get(room_id, {}).get(
                    'target_temperature', default_temp
                )
                
                rooms[room_id] = RoomSimulator(
                    room_id=room_id,
                    room_name=room['name'],
                    room_type=room_type,
                    floor=room['floor'],
                    target_temp=target_temp,
                    variation=variation
                )
                logger.info(f"Initialized room simulator for {room['name']} (ID: {room_id})")
        
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        sys.exit(1)

def update_temperatures():
    """Periodically update temperatures and report to the control system"""
    while True:
        try:
            for room_id, room in rooms.items():
                elapsed = time.time() - room.last_update
                temp = room.update_temperature(elapsed)
                logger.debug(f"{room.room_name}: {temp:.2f}°C (Heater: {'ON' if room.heater_on else 'OFF'})")
                
                # Report temperature to control system
                try:
                    response = requests.post(
                        f"http://localhost:8000/room/{room_id}/temperature",
                        json={"temperature": temp},
                        timeout=2
                    )
                    if response.status_code == 200:
                        logger.debug(f"Reported temperature for {room.room_name}: {temp:.2f}°C")
                except Exception as e:
                    if "Connection refused" in str(e):
                        logger.debug("Control system not available")
                    else:
                        logger.error(f"Error reporting temperature: {e}")
            
            # Sleep until next update
            time.sleep(update_interval)
        except Exception as e:
            logger.error(f"Error in temperature update thread: {e}")
            time.sleep(5)  # Wait before retrying

@app.get("/")
def read_root():
    """Simulator root endpoint"""
    return {
        "status": "running",
        "rooms": len(rooms),
        "message": "Temperature simulator is running"
    }

@app.get("/rooms")
def get_rooms():
    """Get all simulated rooms"""
    return {
        room_id: {
            "name": room.room_name,
            "type": room.room_type,
            "floor": room.floor,
            "current_temperature": round(room.current_temp, 2),
            "target_temperature": room.target_temp,
            "heater_status": room.heater_on
        }
        for room_id, room in rooms.items()
    }

@app.get("/room/{room_id}")
def get_room(room_id: str):
    """Get a specific room's simulated data"""
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = rooms[room_id]
    return {
        "name": room.room_name,
        "type": room.room_type,
        "floor": room.floor,
        "current_temperature": round(room.current_temp, 2),
        "target_temperature": room.target_temp,
        "heater_status": room.heater_on
    }

@app.get("/room/{room_id}/temperature")
def get_temperature(room_id: str):
    """Get the current temperature for a room"""
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    return {"temperature": round(rooms[room_id].current_temp, 2)}

@app.post("/room/{room_id}/heater")
def control_heater(room_id: str, request: HeaterRequest):
    """Control the heater status for a room"""
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = rooms[room_id]
    room.heater_on = request.status
    status_text = "ON" if request.status else "OFF"
    logger.info(f"Heater for {room.room_name} turned {status_text}")
    
    return {"success": True, "status": request.status}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Temperature Simulator")
    parser.add_argument("--port", type=int, default=8100, help="Port to run the simulator on")
    parser.add_argument("--log-level", default="INFO", 
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
                        help="Log level")
    args = parser.parse_args()
    
    # Set log level
    logger.setLevel(getattr(logging, args.log_level))
    
    # Load configuration
    config = load_topology()
    update_interval = config.get("simulator", {}).get("update_interval_seconds", 5)
    
    # Start temperature update thread
    threading.Thread(target=update_temperatures, daemon=True).start()
    logger.info(f"Temperature update thread started (interval: {update_interval}s)")
    
    # Start the API
    logger.info(f"Starting simulator API on port {args.port}")
    uvicorn.run(app, host="0.0.0.0", port=args.port)
