#!/usr/bin/env python3
import random
import time
import logging
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
import uvicorn
from pathlib import Path
import yaml
import threading
from config_loader import load_config, load_topology

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('temperature_simulator')

app = FastAPI(title="Temperature Sensor Simulator")

# Global state
room_temperatures: Dict[str, float] = {}
base_port = 8100  # Starting port for sensor endpoints

def load_room_configs() -> Dict[str, Any]:
    """Load room configurations and initialize temperatures."""
    config = load_config()
    topology = load_topology()
    
    room_configs = {}
    for room_type, rooms in topology['rooms'].items():
        default_temp = config['default_temperatures'].get(room_type, 20.0)
        for room_id, room_data in rooms.items():
            target_temp = config.get('room_overrides', {}).get(room_id, {}).get(
                'target_temperature', default_temp)
            room_configs[room_id] = {
                'target_temperature': target_temp,
                'port': None  # Will be assigned dynamically
            }
    return room_configs

def generate_temperature(target_temp: float) -> float:
    """Generate a random temperature within ±2 degrees of target."""
    variation = random.uniform(-2.0, 2.0)
    return round(target_temp + variation, 1)

def update_temperatures():
    """Periodically update temperatures for all rooms."""
    while True:
        for room_id, config in room_configs.items():
            room_temperatures[room_id] = generate_temperature(config['target_temperature'])
            logger.info(f"Room {room_id}: Temperature updated to {room_temperatures[room_id]}°C "
                       f"(Target: {config['target_temperature']}°C)")
        time.sleep(5)  # Update every 5 seconds

def create_room_app(room_id: str) -> FastAPI:
    """Create a FastAPI application for a specific room's sensor."""
    room_app = FastAPI()
    
    @room_app.get("/temperature")
    async def get_temperature():
        if room_id not in room_temperatures:
            raise HTTPException(status_code=404, detail="Room temperature not found")
        return {"temperature": room_temperatures[room_id]}
    
    @room_app.get("/health")
    async def health_check():
        return {"status": "healthy"}
    
    return room_app

def start_room_sensor(room_id: str, port: int):
    """Start a sensor endpoint for a specific room."""
    room_app = create_room_app(room_id)
    config = uvicorn.Config(room_app, host="0.0.0.0", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run)
    thread.daemon = True
    thread.start()
    logger.info(f"Started sensor for room {room_id} on port {port}")

@app.on_event("startup")
async def startup_event():
    """Initialize and start all room sensors."""
    logger.info("Starting Temperature Simulator")
    
    # Start temperature update thread
    update_thread = threading.Thread(target=update_temperatures)
    update_thread.daemon = True
    update_thread.start()
    
    # Start individual sensor endpoints
    for i, (room_id, config) in enumerate(room_configs.items()):
        port = base_port + i
        config['port'] = port
        start_room_sensor(room_id, port)

@app.get("/sensors")
async def get_sensor_status():
    """Get status of all simulated sensors."""
    return {
        room_id: {
            "current_temperature": room_temperatures.get(room_id),
            "target_temperature": config['target_temperature'],
            "port": config['port']
        }
        for room_id, config in room_configs.items()
    }

if __name__ == "__main__":
    # Load configurations
    room_configs = load_room_configs()
    
    # Start the main control API
    uvicorn.run(app, host="0.0.0.0", port=8090)
