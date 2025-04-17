# system_test.py
"""
System test for the Automated Pet Care System.
This script creates and runs all components of the system to verify they work together.
"""
import time
import logging
import threading
from flask import Flask
from control_system import create_control_system
from control_system.sensor_manager import TemperatureSensor, HumiditySensor, FoodLevelSensor, WaterLevelSensor
from control_system.actuator_controller import FoodDispenser, WaterDispenser, EnvironmentalController
from api.routes import create_api

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SystemTest")

def setup_system():
    """Set up the complete APCS system for testing."""
    logger.info("Setting up APCS system components...")
    
    # Create control system components
    sensor_manager, actuator_controller, data_processor = create_control_system()
    
    # Add sensors
    sensor_manager.add_sensor(TemperatureSensor("temp_1"))
    sensor_manager.add_sensor(HumiditySensor("humid_1"))
    sensor_manager.add_sensor(FoodLevelSensor("food_1"))
    sensor_manager.add_sensor(WaterLevelSensor("water_1"))
    
    # Add actuators
    actuator_controller.add_actuator(FoodDispenser("food_dispenser_1"))
    actuator_controller.add_actuator(WaterDispenser("water_dispenser_1"))
    actuator_controller.add_actuator(
        EnvironmentalController("fan_1", EnvironmentalController.ControllerType.FAN)
    )
    actuator_controller.add_actuator(
        EnvironmentalController("heater_1", EnvironmentalController.ControllerType.HEATER)
    )
    
    # Connect all components
    sensor_manager.connect_all()
    actuator_controller.connect_all()
    
    # Create API
    app, socketio, api_handler = create_api(sensor_manager, actuator_controller, data_processor)
    
    logger.info("System setup complete")
    return sensor_manager, actuator_controller, data_processor, app, socketio

def run_system_test():
    """Run a complete system test."""
    try:
        # Set up the system
        sensor_manager, actuator_controller, data_processor, app, socketio = setup_system()
        
        # Start the data processor
        logger.info("Starting data processor...")
        data_processor.start()
        
        # Start API server in a separate thread
        logger.info("Starting API server...")
        api_thread = threading.Thread(
            target=socketio.run,
            args=(app,),
            kwargs={"host": "127.0.0.1", "port": 5000, "debug": False}
        )
        api_thread.daemon = True
        api_thread.start()
        
        logger.info("Full system is now running")
        logger.info("API available at http://127.0.0.1:5000")
        
        # Run a series of tests
        time.sleep(2)  # Give everything time to start up
        
        # Test 1: Get sensor readings
        logger.info("\n--- Test 1: Sensor Readings ---")
        readings = sensor_manager.read_all()
        for sensor_id, reading in readings.items():
            logger.info(f"{sensor_id}: {reading.value} {reading.unit}")
        
        # Test 2: Get system status
        logger.info("\n--- Test 2: System Status ---")
        status = data_processor.get_system_status()
        logger.info(f"System status: {status}")
        
        # Test 3: Activate an actuator
        logger.info("\n--- Test 3: Activate Actuator ---")
        result = actuator_controller.activate_actuator("food_dispenser_1", power=0.8, duration=2.0)
        logger.info(f"Activation result: {result}")
        
        # Let the system run for a while to observe behavior
        logger.info("\nSystem is running. Press Ctrl+C to stop...")
        
        try:
            # Keep the main thread alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received stop signal")
    
    finally:
        # Clean up
        logger.info("Shutting down...")
        data_processor.stop()
        actuator_controller.disconnect_all()
        sensor_manager.disconnect_all()
        logger.info("System shutdown complete")

if __name__ == "__main__":
    run_system_test()