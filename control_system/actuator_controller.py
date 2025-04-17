"""
Actuator Controller for the Automated Pet Care System.
This module handles control interfaces for dispensers and environmental control systems,
along with safety monitoring and failsafe mechanisms.
"""
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum, auto

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ActuatorController")

class ActuatorState(Enum):
    """Possible states for an actuator."""
    IDLE = auto()          # Actuator is inactive
    ACTIVE = auto()        # Actuator is currently operating
    ERROR = auto()         # Actuator is in error state
    MAINTENANCE = auto()   # Actuator is in maintenance mode
    DISABLED = auto()      # Actuator is manually disabled

@dataclass
class ActuatorStatus:
    """Data class for storing actuator status information."""
    state: ActuatorState
    last_activated: float  # Timestamp of last activation
    activation_count: int  # Number of times activated
    error_message: Optional[str] = None
    current_power: float = 0.0  # Current power level (0.0-1.0)

class Actuator(ABC):
    """Abstract base class for all actuators."""
    
    def __init__(self, actuator_id: str, name: str):
        self.actuator_id = actuator_id
        self.name = name
        self.is_connected = False
        self.status = ActuatorStatus(
            state=ActuatorState.IDLE,
            last_activated=0.0,
            activation_count=0,
            current_power=0.0
        )
        # Safety limits
        self.max_activation_time = 60.0  # seconds
        self.min_cooldown_time = 10.0    # seconds
        self.last_deactivation_time = 0.0
        self.max_activations_per_day = 50
        self.daily_activation_count = 0
        self.daily_reset_time = 0.0
        
        logger.info(f"Initialized {name} actuator with ID {actuator_id}")
    
    @abstractmethod
    def activate(self, power: float = 1.0, duration: Optional[float] = None) -> bool:
        """
        Activate the actuator.
        Args:
            power: Power level between 0.0 and 1.0
            duration: Duration in seconds, or None for indefinite
        Returns:
            True if activation was successful
        """
        pass
    
    @abstractmethod
    def deactivate(self) -> bool:
        """
        Deactivate the actuator.
        Returns:
            True if deactivation was successful
        """
        pass
    
    def is_safe_to_activate(self) -> Tuple[bool, Optional[str]]:
        """
        Check if it's safe to activate the actuator based on various safety rules.
        Returns:
            Tuple of (is_safe, reason) where reason is None if is_safe is True
        """
        current_time = time.time()
        
        # Check if disabled
        if self.status.state == ActuatorState.DISABLED:
            return False, "Actuator is disabled"
        
        # Check if in error state
        if self.status.state == ActuatorState.ERROR:
            return False, f"Actuator is in error state: {self.status.error_message}"
        
        # Check if in maintenance
        if self.status.state == ActuatorState.MAINTENANCE:
            return False, "Actuator is in maintenance mode"
        
        # Check cooldown period
        if (current_time - self.last_deactivation_time) < self.min_cooldown_time:
            return False, f"Cooldown period not complete, wait {self.min_cooldown_time - (current_time - self.last_deactivation_time):.1f} seconds"
        
        # Check daily activation limit
        # Reset counter if it's a new day
        if (current_time - self.daily_reset_time) > 86400:  # 24 hours in seconds
            self.daily_activation_count = 0
            self.daily_reset_time = current_time
            
        if self.daily_activation_count >= self.max_activations_per_day:
            return False, f"Daily activation limit of {self.max_activations_per_day} reached"
        
        return True, None
    
    def set_error(self, error_message: str) -> None:
        """Set the actuator to ERROR state with the given error message."""
        self.status.state = ActuatorState.ERROR
        self.status.error_message = error_message
        logger.error(f"{self.name} error: {error_message}")
    
    def clear_error(self) -> None:
        """Clear the error state if the actuator is in ERROR state."""
        if self.status.state == ActuatorState.ERROR:
            self.status.state = ActuatorState.IDLE
            self.status.error_message = None
            logger.info(f"Cleared error state for {self.name}")
    
    def connect(self) -> bool:
        """
        Connect to the actuator hardware.
        Returns True if connection was successful.
        """
        # In a real implementation, this would handle actual hardware connection
        self.is_connected = True
        logger.info(f"Connected to {self.name} actuator")
        return True
    
    def disconnect(self) -> None:
        """Disconnect from the actuator hardware."""
        self.deactivate()
        self.is_connected = False
        logger.info(f"Disconnected from {self.name} actuator")
    
    def enable(self) -> None:
        """Enable the actuator if it was disabled."""
        if self.status.state == ActuatorState.DISABLED:
            self.status.state = ActuatorState.IDLE
            logger.info(f"Enabled {self.name} actuator")
    
    def disable(self) -> None:
        """Disable the actuator."""
        self.deactivate()
        self.status.state = ActuatorState.DISABLED
        logger.info(f"Disabled {self.name} actuator")
    
    def set_maintenance_mode(self, enable: bool) -> None:
        """Set or clear maintenance mode."""
        if enable:
            self.deactivate()
            self.status.state = ActuatorState.MAINTENANCE
            logger.info(f"Set {self.name} actuator to maintenance mode")
        elif self.status.state == ActuatorState.MAINTENANCE:
            self.status.state = ActuatorState.IDLE
            logger.info(f"Cleared maintenance mode for {self.name} actuator")


class FoodDispenser(Actuator):
    """Food dispenser actuator implementation."""
    
    def __init__(self, actuator_id: str, name: str = "Food Dispenser"):
        super().__init__(actuator_id, name)
        # Configuration
        self.dispensing_rate = 10.0  # amount per second
        self.max_activation_time = 10.0  # Max 10 seconds of continuous dispensing
        
    def activate(self, power: float = 1.0, duration: Optional[float] = None) -> bool:
        """
        Activate the food dispenser.
        Args:
            power: Power level between 0.0 and 1.0 (affects dispensing rate)
            duration: Duration in seconds, or None for indefinite
        Returns:
            True if activation was successful
        """
        # Safety check
        is_safe, reason = self.is_safe_to_activate()
        if not is_safe:
            logger.warning(f"Cannot activate {self.name}: {reason}")
            return False
        
        # Ensure power is within bounds
        power = max(0.1, min(1.0, power))  # Clamp between 0.1 and 1.0
        
        # Apply duration limit if not specified
        if duration is None or duration > self.max_activation_time:
            duration = self.max_activation_time
            logger.info(f"Limited {self.name} activation to {duration} seconds")
        
        try:
            # In a real implementation, this would control actual hardware
            # e.g., via GPIO pins on a Raspberry Pi
            logger.info(f"Activating {self.name} at {power*100:.0f}% power for {duration} seconds")
            
            # Update status
            self.status.state = ActuatorState.ACTIVE
            self.status.last_activated = time.time()
            self.status.activation_count += 1
            self.daily_activation_count += 1
            self.status.current_power = power
            
            # Simulate dispensing (in a real implementation, this would be a separate thread)
            # For simplicity, we're just going to wait here
            amount_dispensed = self.dispensing_rate * power * duration
            logger.info(f"Dispensed {amount_dispensed:.1f} units of food")
            
            # Simulated delay - in a real implementation, you would use a timer or thread
            time.sleep(0.1)  # Just a small delay for simulation
            
            # Deactivate after duration (in a real implementation, this would be on a timer)
            if duration > 0:
                # Note: in a real implementation, you would set a timer instead of sleeping
                # time.sleep(duration)
                self.deactivate()
            
            return True
            
        except Exception as e:
            self.set_error(f"Activation failed: {str(e)}")
            return False
    
    def deactivate(self) -> bool:
        """
        Deactivate the food dispenser.
        Returns:
            True if deactivation was successful
        """
        if self.status.state != ActuatorState.ACTIVE:
            return True  # Already inactive
        
        try:
            # In a real implementation, this would control actual hardware
            logger.info(f"Deactivating {self.name}")
            
            # Update status
            self.status.state = ActuatorState.IDLE
            self.last_deactivation_time = time.time()
            self.status.current_power = 0.0
            
            return True
            
        except Exception as e:
            self.set_error(f"Deactivation failed: {str(e)}")
            return False


class WaterDispenser(Actuator):
    """Water dispenser actuator implementation."""
    
    def __init__(self, actuator_id: str, name: str = "Water Dispenser"):
        super().__init__(actuator_id, name)
        # Configuration
        self.flow_rate = 20.0  # mL per second
        self.max_activation_time = 15.0  # Max 15 seconds of continuous flow
        
    def activate(self, power: float = 1.0, duration: Optional[float] = None) -> bool:
        """
        Activate the water dispenser.
        Args:
            power: Power level between 0.0 and 1.0 (affects flow rate)
            duration: Duration in seconds, or None for indefinite
        Returns:
            True if activation was successful
        """
        # Safety check
        is_safe, reason = self.is_safe_to_activate()
        if not is_safe:
            logger.warning(f"Cannot activate {self.name}: {reason}")
            return False
        
        # Ensure power is within bounds
        power = max(0.1, min(1.0, power))  # Clamp between 0.1 and 1.0
        
        # Apply duration limit if not specified
        if duration is None or duration > self.max_activation_time:
            duration = self.max_activation_time
            logger.info(f"Limited {self.name} activation to {duration} seconds")
        
        try:
            # In a real implementation, this would control actual hardware
            logger.info(f"Activating {self.name} at {power*100:.0f}% power for {duration} seconds")
            
            # Update status
            self.status.state = ActuatorState.ACTIVE
            self.status.last_activated = time.time()
            self.status.activation_count += 1
            self.daily_activation_count += 1
            self.status.current_power = power
            
            # Simulate dispensing (in a real implementation, this would be a separate thread)
            amount_dispensed = self.flow_rate * power * duration
            logger.info(f"Dispensed {amount_dispensed:.1f} mL of water")
            
            # Simulated delay - in a real implementation, you would use a timer or thread
            time.sleep(0.1)  # Just a small delay for simulation
            
            # Deactivate after duration (in a real implementation, this would be on a timer)
            if duration > 0:
                # Note: in a real implementation, you would set a timer instead of sleeping
                # time.sleep(duration)
                self.deactivate()
            
            return True
            
        except Exception as e:
            self.set_error(f"Activation failed: {str(e)}")
            return False
    
    def deactivate(self) -> bool:
        """
        Deactivate the water dispenser.
        Returns:
            True if deactivation was successful
        """
        if self.status.state != ActuatorState.ACTIVE:
            return True  # Already inactive
        
        try:
            # In a real implementation, this would control actual hardware
            logger.info(f"Deactivating {self.name}")
            
            # Update status
            self.status.state = ActuatorState.IDLE
            self.last_deactivation_time = time.time()
            self.status.current_power = 0.0
            
            return True
            
        except Exception as e:
            self.set_error(f"Deactivation failed: {str(e)}")
            return False


class EnvironmentalController(Actuator):
    """Environmental control actuator (fan, heater, etc.)"""
    
    class ControllerType(Enum):
        """Types of environmental controllers."""
        FAN = auto()
        HEATER = auto()
        HUMIDIFIER = auto()
        DEHUMIDIFIER = auto()
    
    def __init__(self, actuator_id: str, controller_type: ControllerType, name: Optional[str] = None):
        if name is None:
            name = f"{controller_type.name.title()} Controller"
        super().__init__(actuator_id, name)
        
        self.controller_type = controller_type
        # Configuration based on type
        if controller_type == self.ControllerType.FAN:
            self.max_activation_time = 3600.0  # 1 hour
            self.power_consumption = 15.0  # Watts
        elif controller_type == self.ControllerType.HEATER:
            self.max_activation_time = 1800.0  # 30 minutes
            self.power_consumption = 150.0  # Watts
        elif controller_type in (self.ControllerType.HUMIDIFIER, self.ControllerType.DEHUMIDIFIER):
            self.max_activation_time = 3600.0  # 1 hour
            self.power_consumption = 25.0  # Watts
    
    def activate(self, power: float = 1.0, duration: Optional[float] = None) -> bool:
        """
        Activate the environmental controller.
        Args:
            power: Power level between 0.0 and 1.0
            duration: Duration in seconds, or None for indefinite
        Returns:
            True if activation was successful
        """
        # Safety check
        is_safe, reason = self.is_safe_to_activate()
        if not is_safe:
            logger.warning(f"Cannot activate {self.name}: {reason}")
            return False
        
        # Additional safety checks for heaters
        if self.controller_type == self.ControllerType.HEATER and power > 0.7:
            logger.warning(f"Limiting heater power to 70% for safety")
            power = 0.7
        
        # Ensure power is within bounds
        power = max(0.1, min(1.0, power))  # Clamp between 0.1 and 1.0
        
        # Apply duration limit if not specified
        if duration is None or duration > self.max_activation_time:
            duration = self.max_activation_time
            logger.info(f"Limited {self.name} activation to {duration} seconds")
        
        try:
            # In a real implementation, this would control actual hardware
            logger.info(f"Activating {self.name} at {power*100:.0f}% power for {duration} seconds")
            
            # Update status
            self.status.state = ActuatorState.ACTIVE
            self.status.last_activated = time.time()
            self.status.activation_count += 1
            self.daily_activation_count += 1
            self.status.current_power = power
            
            # Calculate power consumption
            power_used = self.power_consumption * power * (duration / 3600.0)  # in watt-hours
            logger.info(f"Estimated power consumption: {power_used:.2f} Wh")
            
            # Simulated delay - in a real implementation, you would use a timer or thread
            time.sleep(0.1)  # Just a small delay for simulation
            
            # Deactivate after duration (in a real implementation, this would be on a timer)
            if duration > 0:
                # Note: in a real implementation, you would set a timer instead of sleeping
                # time.sleep(duration)
                self.deactivate()
            
            return True
            
        except Exception as e:
            self.set_error(f"Activation failed: {str(e)}")
            return False
    
    def deactivate(self) -> bool:
        """
        Deactivate the environmental controller.
        Returns:
            True if deactivation was successful
        """
        if self.status.state != ActuatorState.ACTIVE:
            return True  # Already inactive
        
        try:
            # In a real implementation, this would control actual hardware
            logger.info(f"Deactivating {self.name}")
            
            # Update status
            self.status.state = ActuatorState.IDLE
            self.last_deactivation_time = time.time()
            self.status.current_power = 0.0
            
            return True
            
        except Exception as e:
            self.set_error(f"Deactivation failed: {str(e)}")
            return False


class ActuatorController:
    """
    Manager class for handling multiple actuators.
    Provides a unified interface for actuator operations.
    """
    
    def __init__(self):
        self.actuators = {}
        self.emergency_stop_active = False
        logger.info("Actuator Controller initialized")
    
    def add_actuator(self, actuator: Actuator) -> None:
        """Add an actuator to the controller."""
        self.actuators[actuator.actuator_id] = actuator
        logger.info(f"Added actuator {actuator.name} (ID: {actuator.actuator_id})")
    
    def remove_actuator(self, actuator_id: str) -> bool:
        """Remove an actuator from the controller."""
        if actuator_id in self.actuators:
            del self.actuators[actuator_id]
            logger.info(f"Removed actuator with ID {actuator_id}")
            return True
        logger.warning(f"Attempted to remove non-existent actuator with ID {actuator_id}")
        return False
    
    def get_actuator(self, actuator_id: str) -> Optional[Actuator]:
        """Get an actuator by ID."""
        return self.actuators.get(actuator_id)
    
    def get_all_actuators(self) -> Dict[str, Actuator]:
        """Get all actuators."""
        return self.actuators
    
    def activate_actuator(self, actuator_id: str, power: float = 1.0, duration: Optional[float] = None) -> bool:
        """Activate a specific actuator."""
        if self.emergency_stop_active:
            logger.warning("Cannot activate actuator: Emergency stop is active")
            return False
            
        if actuator_id in self.actuators:
            return self.actuators[actuator_id].activate(power, duration)
        
        logger.warning(f"Attempted to activate non-existent actuator with ID {actuator_id}")
        return False
    
    def deactivate_actuator(self, actuator_id: str) -> bool:
        """Deactivate a specific actuator."""
        if actuator_id in self.actuators:
            return self.actuators[actuator_id].deactivate()
            
        logger.warning(f"Attempted to deactivate non-existent actuator with ID {actuator_id}")
        return False
    
    def connect_all(self) -> List[str]:
        """
        Connect all actuators to their hardware.
        Returns a list of actuator IDs that failed to connect.
        """
        failed_actuators = []
        for actuator_id, actuator in self.actuators.items():
            if not actuator.connect():
                failed_actuators.append(actuator_id)
        return failed_actuators
    
    def disconnect_all(self) -> None:
        """Disconnect all actuators from their hardware."""
        for actuator in self.actuators.values():
            actuator.disconnect()
    
    def emergency_stop(self) -> None:
        """
        Trigger an emergency stop - deactivate all actuators and prevent further activation.
        """
        logger.critical("EMERGENCY STOP TRIGGERED")
        self.emergency_stop_active = True
        
        # Deactivate all actuators
        for actuator in self.actuators.values():
            actuator.deactivate()
    
    def reset_emergency_stop(self) -> None:
        """
        Reset the emergency stop condition.
        """
        if self.emergency_stop_active:
            logger.info("Emergency stop reset")
            self.emergency_stop_active = False
    
    def get_active_actuators(self) -> List[Actuator]:
        """Get a list of all currently active actuators."""
        return [actuator for actuator in self.actuators.values() 
                if actuator.status.state == ActuatorState.ACTIVE]
    
    def get_actuators_in_error(self) -> List[Actuator]:
        """Get a list of all actuators in error state."""
        return [actuator for actuator in self.actuators.values() 
                if actuator.status.state == ActuatorState.ERROR]
    
    def reset_errors(self) -> None:
        """Clear error state for all actuators."""
        for actuator in self.actuators.values():
            actuator.clear_error()


# Example usage
if __name__ == "__main__":
    # Create actuator controller
    controller = ActuatorController()
    
    # Add actuators
    controller.add_actuator(FoodDispenser("food_1"))
    controller.add_actuator(WaterDispenser("water_1"))
    controller.add_actuator(EnvironmentalController("fan_1", EnvironmentalController.ControllerType.FAN))
    controller.add_actuator(EnvironmentalController("heater_1", EnvironmentalController.ControllerType.HEATER))
    
    # Connect to actuators
    failed_connections = controller.connect_all()
    if failed_connections:
        print(f"Failed to connect to actuators: {failed_connections}")
    
    # Test activating food dispenser
    print("\nTesting food dispenser...")
    controller.activate_actuator("food_1", power=0.5, duration=2.0)
    
    # Test activating water dispenser
    print("\nTesting water dispenser...")
    controller.activate_actuator("water_1", power=0.8, duration=3.0)
    
    # Test activating fan
    print("\nTesting fan...")
    controller.activate_actuator("fan_1", power=0.7, duration=5.0)
    
    # Test activating heater
    print("\nTesting heater...")
    controller.activate_actuator("heater_1", power=0.6, duration=4.0)
    
    # Test emergency stop
    print("\nTesting emergency stop...")
    controller.emergency_stop()
    
    # Try to activate something after emergency stop
    print("\nTrying to activate after emergency stop...")
    result = controller.activate_actuator("fan_1", power=0.5)
    print(f"Activation successful: {result}")
    
    # Reset emergency stop and try again
    print("\nResetting emergency stop and trying again...")
    controller.reset_emergency_stop()
    result = controller.activate_actuator("fan_1", power=0.5, duration=2.0)
    print(f"Activation successful: {result}")
    
    # Disconnect all actuators
    controller.disconnect_all()