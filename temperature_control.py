import requests
import logging
from typing import Dict, Optional
from dataclasses import dataclass
import schedule
import time
from threading import Thread

logger = logging.getLogger('home_temperature_control')

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

def get_room_info(room_data: dict, room_type: str) -> RoomInfo:
    """Create RoomInfo from room data."""
    return RoomInfo(
        id=room_data['id'],
        name=room_data['name'],
        floor=room_data['floor'],
        room_type=room_type
    )

def get_temperature(room: Room) -> Optional[float]:
    """Fetch temperature from room sensor."""
    try:
        response = requests.get(room.sensor_url)
        if response.status_code == 200:
            return float(response.text)
        logger.error(f"Error getting temperature for {room.info.name}: {response.status_code}")
        return None
    except Exception as e:
        logger.error(f"Error getting temperature for {room.info.name}: {str(e)}")
        return None

def control_heater(room: Room, status: bool) -> bool:
    """Control room heater."""
    try:
        response = requests.post(room.heater_url, json={'status': status})
        if response.status_code == 200:
            return True
        logger.error(f"Error controlling heater for {room.info.name}: {response.status_code}")
        return False
    except Exception as e:
        logger.error(f"Error controlling heater for {room.info.name}: {str(e)}")
        return False

class TemperatureController:
    def __init__(self, config: dict):
        self.rooms: Dict[str, Room] = {}
        self.min_temp = config.get('min_allowed_temperature', 15.0)
        self.max_temp = config.get('max_allowed_temperature', 30.0)
        self.check_interval_seconds = config.get('temperature_check_interval_seconds', 300)
        self.default_temps = config.get('default_temperatures', {})
        self.device_urls = config.get('device_urls', {})
        self.scheduler_thread: Optional[Thread] = None

    def initialize_rooms(self, topology: dict) -> None:
        """Initialize rooms from topology."""
        room_overrides = topology.get('room_overrides', {})
        
        for room_type, rooms_data in topology['rooms'].items():
            default_temp = self.default_temps.get(room_type, 20.0)
            
            for room_data in rooms_data:
                room_id = room_data['id']
                target_temp = room_overrides.get(room_id, {}).get('target_temperature', default_temp)
                
                room_info = get_room_info(room_data, room_type)
                sensor_url = self.device_urls['sensor_pattern'].format(room_id=room_id)
                heater_url = self.device_urls['heater_pattern'].format(room_id=room_id)
                
                self.rooms[room_id] = Room(room_info, sensor_url, heater_url, target_temp)
                logger.info(f"Initialized {room_info.name} (ID: {room_id}) with target temperature {target_temp}°C")

    def check_and_control_temperature(self) -> None:
        """Check temperatures and control heaters for all rooms."""
        logger.info("Starting temperature check cycle")
        for room in self.rooms.values():
            try:
                current_temp = get_temperature(room)
                if current_temp is not None:
                    room.current_temp = current_temp
                    should_heat = current_temp < room.target_temp
                    
                    if control_heater(room, should_heat):
                        room.heater_status = should_heat
                    
                    logger.info(f"Room {room.info.name}: Current={current_temp:.1f}°C, Target={room.target_temp:.1f}°C, Heater={'ON' if room.heater_status else 'OFF'}")
                else:
                    logger.warning(f"Could not get temperature for room {room.info.name}")
            except Exception as e:
                logger.error(f"Error checking room {room.info.name}: {e}")
        logger.info("Completed temperature check cycle")

    def start_scheduler(self) -> None:
        """Start the temperature control scheduler."""
        schedule.every(self.check_interval_seconds).seconds.do(self.check_and_control_temperature)
        logger.info(f"Scheduling temperature checks every {self.check_interval_seconds} seconds")
        
        def run_scheduler():
            """Run the scheduler in a separate thread."""
            while True:
                schedule.run_pending()
                time.sleep(1)
        
        self.scheduler_thread = Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("Temperature control scheduler started")
