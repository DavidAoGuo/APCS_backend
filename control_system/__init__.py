"""
Control System package for the Automated Pet Care System.
This package contains the core components for sensor management,
actuator control, and data processing.
"""
from control_system.sensor_manager import SensorManager
from control_system.actuator_controller import ActuatorController
from control_system.data_processor import DataProcessor

# Version information
__version__ = '0.1.0'

# Export main classes
__all__ = ['SensorManager', 'ActuatorController', 'DataProcessor']

def create_control_system():
    """
    Factory function to create a complete control system with all components properly connected.
    Returns:
        tuple: (sensor_manager, actuator_controller, data_processor)
    """
    # Create components
    sensor_manager = SensorManager()
    actuator_controller = ActuatorController()
    data_processor = DataProcessor(sensor_manager, actuator_controller)
    
    # Return all components
    return sensor_manager, actuator_controller, data_processor