#!/usr/bin/env python3
import random
import time
import logging
import requests
from typing import Dict, Any, Optional
import yaml
from dataclasses import dataclass
import threading
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('temperature_test_simulator')

@dataclass
class RoomState:
    room_id: str
    name: str
    target_temp: float
    current_temp: float
    trend: float  # Temperature change direction (-1 to 1)
    last_update: float  # Last update timestamp

class TemperatureTestSimulator:
    def __init__(self):
        self.rooms: Dict[str, RoomState] = {}
        self.config = self.load_config()
        self.topology = self.load_topology()
        self.running = False
        self.api_url = f"http://localhost:{self.config['api']['port']}"
        
    def load_config(self) -> dict:
        """Load configuration from config.yaml."""
        with open('config.yaml', 'r') as f:
            return yaml.safe_load(f)
            
    def load_topology(self) -> dict:
        """Load topology from house_topology.yaml."""
        with open('house_topology.yaml', 'r') as f:
            return yaml.safe_load(f)
    
    def initialize_rooms(self):
        """Initialize room states with random temperatures around target."""
        for room_type, rooms in self.topology['rooms'].items():
            default_temp = self.config['default_temperatures'].get(room_type, 20.0)
            
            for room_id, room_data in rooms.items():
                target_temp = self.config.get('room_overrides', {}).get(room_id, {}).get(
                    'target_temperature', default_temp)
                
                # Initialize with random temperature ±2°C from target
                current_temp = target_temp + random.uniform(-2, 2)
                
                self.rooms[room_id] = RoomState(
                    room_id=room_id,
                    name=room_data['name'],
                    target_temp=target_temp,
                    current_temp=round(current_temp, 1),
                    trend=random.uniform(-1, 1),  # Random initial trend
                    last_update=time.time()
                )
                logger.info(f"Initialized {room_data['name']}: Target={target_temp}°C, Current={current_temp:.1f}°C")

    def update_room_temperature(self, room: RoomState):
        """Update room temperature based on current trend and random factors."""
        now = time.time()
        elapsed = now - room.last_update
        
        # Randomly adjust trend
        room.trend += random.uniform(-0.2, 0.2)
        room.trend = max(-1, min(1, room.trend))  # Keep trend between -1 and 1
        
        # Calculate temperature change
        # Maximum change of 0.5°C per minute
        max_change = 0.5 * (elapsed / 60)
        temp_change = room.trend * max_change
        
        # Update temperature
        room.current_temp += temp_change
        
        # Ensure temperature stays within ±2°C of target
        if abs(room.current_temp - room.target_temp) > 2:
            # Start trending back toward target
            room.trend = -1 if room.current_temp > room.target_temp else 1
            
        room.current_temp = round(room.current_temp, 1)
        room.last_update = now
        
        return room.current_temp

    def send_temperature(self, room: RoomState):
        """Send temperature reading to the control system."""
        try:
            url = f"{self.api_url}/room/{room.room_id}/temperature"
            response = requests.post(url, json={"temperature": room.current_temp})
            if response.status_code == 200:
                logger.info(f"Room {room.name}: Sent temperature {room.current_temp}°C")
            else:
                logger.error(f"Failed to send temperature for {room.name}: {response.status_code}")
        except Exception as e:
            logger.error(f"Error sending temperature for {room.name}: {str(e)}")

    def simulate_temperatures(self):
        """Main simulation loop."""
        while self.running:
            for room in self.rooms.values():
                # Update temperature
                new_temp = self.update_room_temperature(room)
                logger.info(f"Room {room.name}: Temperature={new_temp:.1f}°C (Target={room.target_temp}°C)")
                
                # Send to control system
                self.send_temperature(room)
            
            # Wait before next update
            time.sleep(5)  # Update every 5 seconds

    def start(self):
        """Start the temperature simulation."""
        logger.info("Starting Temperature Test Simulator")
        self.initialize_rooms()
        self.running = True
        
        # Start simulation in a separate thread
        self.simulator_thread = threading.Thread(target=self.simulate_temperatures)
        self.simulator_thread.daemon = True
        self.simulator_thread.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stop the temperature simulation."""
        logger.info("Stopping Temperature Test Simulator")
        self.running = False
        if hasattr(self, 'simulator_thread'):
            self.simulator_thread.join()

def main():
    simulator = TemperatureTestSimulator()
    simulator.start()

if __name__ == "__main__":
    main()
