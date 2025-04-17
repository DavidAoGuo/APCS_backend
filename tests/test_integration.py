# tests/test_integration.py
import unittest
import time
from control_system import create_control_system

class TestSystemIntegration(unittest.TestCase):
    """Test cases for system integration."""
    
    def setUp(self):
        """Set up test fixtures before each test."""
        self.sensor_manager, self.actuator_controller, self.data_processor = create_control_system()
        
        # Add test sensors and actuators
        from control_system.sensor_manager import TemperatureSensor, FoodLevelSensor
        from control_system.actuator_controller import FoodDispenser, EnvironmentalController
        
        self.sensor_manager.add_sensor(TemperatureSensor("temp_1"))
        self.sensor_manager.add_sensor(FoodLevelSensor("food_1"))
        self.actuator_controller.add_actuator(FoodDispenser("food_dispenser_1"))
        self.actuator_controller.add_actuator(
            EnvironmentalController("heater_1", EnvironmentalController.ControllerType.HEATER)
        )
        
        # Connect everything
        self.sensor_manager.connect_all()
        self.actuator_controller.connect_all()
    
    def tearDown(self):
        """Clean up after each test."""
        self.actuator_controller.disconnect_all()
        self.sensor_manager.disconnect_all()
    
    def test_data_processing_flow(self):
        """Test the flow of data from sensors through processing to decisions."""
        # Get initial sensor data
        processed_data = self.data_processor.process_sensor_data()
        
        # Verify we have the expected data
        self.assertIn("temperature_avg", processed_data)
        self.assertIn("food_level", processed_data)
        
        # Run a rule evaluation
        triggered_rules = self.data_processor.evaluate_rules(processed_data)
        
        # We don't know which rules might trigger with simulated data,
        # but the function should run without errors
        self.assertIsInstance(triggered_rules, list)
    
    def test_control_system_interaction(self):
        """Test interaction between different control system components."""
        # Test that sensor data can trigger actuator actions
        # For example, simulate a low temperature:
        
        # Start the data processor
        self.data_processor.start()
        
        try:
            # Wait a bit for processing to occur
            time.sleep(2)
            
            # Check system status
            status = self.data_processor.get_system_status()
            
            # Verify status contains expected fields
            self.assertIn("timestamp", status)
            
            # The exact fields will depend on the implementation, but we should have some data
            self.assertGreater(len(status), 1)
        
        finally:
            # Always stop the data processor
            self.data_processor.stop()

if __name__ == '__main__':
    unittest.main()