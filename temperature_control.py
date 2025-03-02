import logging
import schedule
import time
import requests
from threading import Thread
from dataclasses import dataclass
from typing import Dict, Optional, Any

logger = logging.getLogger('home_temperature_control')

@dataclass
class RoomInfo:
    id: str
    name: str
    floor: int
    room_type: str

class Room:
    def __init__(self, room_info: RoomInfo, target_temp: float):
        self.info = room_info
        self.target_temp = target_temp
        self.current_temp: Optional[float] = None
        self.heater_status: bool = False

class TemperatureController:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.rooms: Dict[str, Room] = {}
        self.min_temp = config.get('min_allowed_temperature', 15.0)
        self.max_temp = config.get('max_allowed_temperature', 30.0)
        self.check_interval = config.get('temperature_check_interval_seconds', 300)
        self.scheduler_thread = None
        
    def initialize_rooms(self, topology):
        """Initialize rooms from the topology."""
        self.rooms = {}
        
        # Process each room type in the topology
        for room_type, room_list in topology['rooms'].items():
            default_temp = self.config['default_temperatures'][room_type]
            
            for room_data in room_list:
                room_id = room_data['id']
                room_info = RoomInfo(
                    id=room_id,
                    name=room_data['name'],
                    floor=room_data['floor'],
                    room_type=room_type
                )
                
                # Get room-specific overrides if they exist
                target_temp = self.config.get('room_overrides', {}).get(room_id, {}).get(
                    'target_temperature', default_temp
                )
                
                # Create room with target temperature
                self.rooms[room_id] = Room(
                    room_info=room_info,
                    target_temp=target_temp
                )
                logger.info(f"Initialized {room_info.name} (ID: {room_id}) with target temperature {target_temp}°C")
    
    def check_and_control_temperatures(self):
        """Check temperatures and control heaters for all rooms."""
        logger.debug("Starting temperature check and control cycle")
        for room_id, room in self.rooms.items():
            if room.current_temp is not None:
                # Control heater based on temperature
                should_heat = room.current_temp < room.target_temp
                if should_heat != room.heater_status:
                    logger.info(
                        f"{room.info.name}: Current temp {room.current_temp}°C is {'below' if should_heat else 'above'} "
                        f"target temp {room.target_temp}°C. {'Activating' if should_heat else 'Deactivating'} heater."
                    )
                    room.heater_status = should_heat
            else:
                logger.debug(f"No temperature reading available for {room.info.name}")
        logger.debug("Completed temperature check and control cycle")
    
    def start_scheduler(self):
        """Start the temperature control scheduler."""
        schedule.clear()
        
        # Convert check interval from seconds to minutes for schedule
        interval_minutes = max(1, self.check_interval // 60)
        logger.info(f"Scheduling temperature checks every {interval_minutes} minutes")
        
        schedule.every(interval_minutes).minutes.do(self.check_and_control_temperatures)
        
        if self.scheduler_thread is None or not self.scheduler_thread.is_alive():
            self.scheduler_thread = Thread(target=self._run_scheduler, daemon=True)
            self.scheduler_thread.start()
            logger.info("Temperature control scheduler started")
    
    def _run_scheduler(self):
        """Run the scheduler in a separate thread."""
        while True:
            schedule.run_pending()
            time.sleep(1)
