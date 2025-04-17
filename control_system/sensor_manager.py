import time
import random
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SensorManager")

@dataclass
class SensorReading:
    """Data class for storing sensor readings with metadata."""
    value: float
    unit: str
    timestamp: float
    sensor_id: str
    is_valid: bool = True
    error_message: Optional[str] = None

class Sensor(ABC):
    """Abstract base class for all sensors."""
    
    def __init__(self, sensor_id: str, name: str):
        self.sensor_id = sensor_id
        self.name = name
        self.calibration_offset = 0.0
        self.calibration_factor = 1.0
        self.min_valid_value = float('-inf')
        self.max_valid_value = float('inf')
        self.last_reading = None
        self.is_connected = False
        logger.info(f"Initialized {name} sensor with ID {sensor_id}")
    
    @abstractmethod
    def read_raw(self) -> float:
        """Read raw value from the sensor hardware."""
        pass
    
    def read(self) -> SensorReading:
        """
        Read from the sensor, apply calibration, validate, and return a SensorReading.
        """
        try:
            raw_value = self.read_raw()
            # Apply calibration
            calibrated_value = (raw_value + self.calibration_offset) * self.calibration_factor
            
            # Create reading object
            reading = SensorReading(
                value=calibrated_value,
                unit=self.get_unit(),
                timestamp=time.time(),
                sensor_id=self.sensor_id
            )
            
            # Validate reading
            if not self.min_valid_value <= reading.value <= self.max_valid_value:
                reading.is_valid = False
                reading.error_message = f"Value out of range [{self.min_valid_value}, {self.max_valid_value}]"
                logger.warning(f"Invalid reading from {self.name}: {reading.error_message}")
            
            self.last_reading = reading
            return reading
            
        except Exception as e:
            logger.error(f"Error reading from {self.name} sensor: {str(e)}")
            return SensorReading(
                value=0.0,
                unit=self.get_unit(),
                timestamp=time.time(),
                sensor_id=self.sensor_id,
                is_valid=False,
                error_message=str(e)
            )
    
    @abstractmethod
    def get_unit(self) -> str:
        """Return the unit of measurement for this sensor."""
        pass
    
    def calibrate(self, reference_value: float) -> bool:
        """
        Calibrate the sensor using a known reference value.
        Returns True if calibration was successful.
        """
        try:
            raw_value = self.read_raw()
            # Simple offset calibration
            self.calibration_offset = reference_value - raw_value
            logger.info(f"Calibrated {self.name} sensor: offset set to {self.calibration_offset}")
            return True
        except Exception as e:
            logger.error(f"Calibration failed for {self.name} sensor: {str(e)}")
            return False
    
    def set_valid_range(self, min_value: float, max_value: float) -> None:
        """Set the valid range for sensor readings."""
        self.min_valid_value = min_value
        self.max_valid_value = max_value
        logger.info(f"Set valid range for {self.name}: [{min_value}, {max_value}]")
    
    def connect(self) -> bool:
        """
        Connect to the sensor hardware.
        Returns True if connection was successful.
        """
        # In a real implementation, this would handle actual hardware connection
        self.is_connected = True
        logger.info(f"Connected to {self.name} sensor")
        return True
    
    def disconnect(self) -> None:
        """Disconnect from the sensor hardware."""
        self.is_connected = False
        logger.info(f"Disconnected from {self.name} sensor")


class TemperatureSensor(Sensor):
    """Temperature sensor implementation."""
    
    def __init__(self, sensor_id: str, name: str = "Temperature"):
        super().__init__(sensor_id, name)
        self.set_valid_range(-10.0, 50.0)  # °C
    
    def read_raw(self) -> float:
        """Read raw temperature value."""
        # Simulated reading - in a real implementation, this would interface with hardware
        # For example, using GPIO pins on a Raspberry Pi or an Arduino interface
        simulated_value = 22.0 + random.uniform(-1.0, 1.0)
        return simulated_value
    
    def get_unit(self) -> str:
        return "°C"


class HumiditySensor(Sensor):
    """Humidity sensor implementation."""
    
    def __init__(self, sensor_id: str, name: str = "Humidity"):
        super().__init__(sensor_id, name)
        self.set_valid_range(0.0, 100.0)  # %
    
    def read_raw(self) -> float:
        """Read raw humidity value."""
        # Simulated reading
        simulated_value = 45.0 + random.uniform(-5.0, 5.0)
        return simulated_value
    
    def get_unit(self) -> str:
        return "%"


class FoodLevelSensor(Sensor):
    """Food level sensor implementation."""
    
    def __init__(self, sensor_id: str, name: str = "Food Level", max_capacity: float = 100.0):
        super().__init__(sensor_id, name)
        self.max_capacity = max_capacity
        self.set_valid_range(0.0, max_capacity)
        self._current_level = max_capacity  # Start with full capacity
    
    def read_raw(self) -> float:
        """Read raw food level value."""
        # Simulated reading - decreases over time
        # In a real implementation, this might use weight sensors or IR distance sensors
        self._current_level = max(0.0, self._current_level - random.uniform(0.0, 0.5))
        return self._current_level
    
    def get_unit(self) -> str:
        return "%"
    
    def refill(self) -> None:
        """Simulate refilling the food container."""
        self._current_level = self.max_capacity
        logger.info(f"Food container refilled to {self.max_capacity}%")


class WaterLevelSensor(Sensor):
    """Water level sensor implementation."""
    
    def __init__(self, sensor_id: str, name: str = "Water Level", max_capacity: float = 100.0):
        super().__init__(sensor_id, name)
        self.max_capacity = max_capacity
        self.set_valid_range(0.0, max_capacity)
        self._current_level = max_capacity  # Start with full capacity
    
    def read_raw(self) -> float:
        """Read raw water level value."""
        # Simulated reading - decreases over time
        # In a real implementation, this might use ultrasonic sensors or float sensors
        self._current_level = max(0.0, self._current_level - random.uniform(0.0, 0.3))
        return self._current_level
    
    def get_unit(self) -> str:
        return "%"
    
    def refill(self) -> None:
        """Simulate refilling the water container."""
        self._current_level = self.max_capacity
        logger.info(f"Water container refilled to {self.max_capacity}%")


class SensorManager:
    """
    Manager class for handling multiple sensors.
    Provides a unified interface for sensor operations.
    """
    
    def __init__(self):
        self.sensors = {}
        logger.info("Sensor Manager initialized")
    
    def add_sensor(self, sensor: Sensor) -> None:
        """Add a sensor to the manager."""
        self.sensors[sensor.sensor_id] = sensor
        logger.info(f"Added sensor {sensor.name} (ID: {sensor.sensor_id})")
    
    def remove_sensor(self, sensor_id: str) -> bool:
        """Remove a sensor from the manager."""
        if sensor_id in self.sensors:
            del self.sensors[sensor_id]
            logger.info(f"Removed sensor with ID {sensor_id}")
            return True
        logger.warning(f"Attempted to remove non-existent sensor with ID {sensor_id}")
        return False
    
    def get_sensor(self, sensor_id: str) -> Optional[Sensor]:
        """Get a sensor by ID."""
        return self.sensors.get(sensor_id)
    
    def get_all_sensors(self) -> Dict[str, Sensor]:
        """Get all sensors."""
        return self.sensors
    
    def read_all(self) -> Dict[str, SensorReading]:
        """Read all sensors and return their readings."""
        readings = {}
        for sensor_id, sensor in self.sensors.items():
            readings[sensor_id] = sensor.read()
        return readings
    
    def connect_all(self) -> List[str]:
        """
        Connect all sensors to their hardware.
        Returns a list of sensor IDs that failed to connect.
        """
        failed_sensors = []
        for sensor_id, sensor in self.sensors.items():
            if not sensor.connect():
                failed_sensors.append(sensor_id)
        return failed_sensors
    
    def disconnect_all(self) -> None:
        """Disconnect all sensors from their hardware."""
        for sensor in self.sensors.values():
            sensor.disconnect()
    
    def calibrate_sensor(self, sensor_id: str, reference_value: float) -> bool:
        """Calibrate a specific sensor."""
        if sensor_id in self.sensors:
            return self.sensors[sensor_id].calibrate(reference_value)
        logger.warning(f"Attempted to calibrate non-existent sensor with ID {sensor_id}")
        return False
    
    def run_calibration_routine(self, sensor_ids: List[str] = None) -> Dict[str, bool]:
        """
        Run a calibration routine for multiple sensors.
        If sensor_ids is None, calibrate all sensors.
        Returns a dictionary mapping sensor IDs to calibration success (True/False).
        """
        results = {}
        sensors_to_calibrate = self.sensors
        
        if sensor_ids is not None:
            sensors_to_calibrate = {id: self.sensors[id] for id in sensor_ids if id in self.sensors}
        
        # In a real implementation, this would use known reference values
        # Here we're just simulating with reasonable values for each sensor type
        for sensor_id, sensor in sensors_to_calibrate.items():
            reference_value = None
            
            if isinstance(sensor, TemperatureSensor):
                reference_value = 22.0  # Reference temperature of 22°C
            elif isinstance(sensor, HumiditySensor):
                reference_value = 45.0  # Reference humidity of 45%
            elif isinstance(sensor, FoodLevelSensor):
                reference_value = 100.0  # Reference food level of 100%
            elif isinstance(sensor, WaterLevelSensor):
                reference_value = 100.0  # Reference water level of 100%
            
            if reference_value is not None:
                results[sensor_id] = sensor.calibrate(reference_value)
            else:
                logger.warning(f"No calibration routine available for sensor {sensor.name}")
                results[sensor_id] = False
                
        return results


# Example usage
if __name__ == "__main__":
    # Create sensor manager
    manager = SensorManager()
    
    # Add sensors
    manager.add_sensor(TemperatureSensor("temp_1"))
    manager.add_sensor(HumiditySensor("humid_1"))
    manager.add_sensor(FoodLevelSensor("food_1"))
    manager.add_sensor(WaterLevelSensor("water_1"))
    
    # Connect to sensors
    failed_connections = manager.connect_all()
    if failed_connections:
        print(f"Failed to connect to sensors: {failed_connections}")
    
    # Run calibration routine
    calibration_results = manager.run_calibration_routine()
    print(f"Calibration results: {calibration_results}")
    
    # Read all sensors
    readings = manager.read_all()
    for sensor_id, reading in readings.items():
        print(f"{sensor_id}: {reading.value} {reading.unit} (valid: {reading.is_valid})")
    
    # Disconnect all sensors
    manager.disconnect_all()