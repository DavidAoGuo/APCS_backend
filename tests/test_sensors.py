# tests/test_sensor_manager.py
import unittest
from unittest.mock import patch, MagicMock
import time
from control_system.sensor_manager import SensorManager, TemperatureSensor, HumiditySensor

class TestSensorManager(unittest.TestCase):
    """Test cases for the Sensor Manager."""
    
    def setUp(self):
        """Set up test fixtures before each test."""
        self.manager = SensorManager()
    
    def test_add_sensor(self):
        """Test adding a sensor to the manager."""
        sensor = TemperatureSensor("test_temp")
        self.manager.add_sensor(sensor)
        self.assertIn("test_temp", self.manager.sensors)
        self.assertEqual(sensor, self.manager.get_sensor("test_temp"))
    
    def test_remove_sensor(self):
        """Test removing a sensor from the manager."""
        sensor = TemperatureSensor("test_temp")
        self.manager.add_sensor(sensor)
        self.assertTrue(self.manager.remove_sensor("test_temp"))
        self.assertNotIn("test_temp", self.manager.sensors)
        self.assertFalse(self.manager.remove_sensor("non_existent"))
    
    def test_read_all(self):
        """Test reading from all sensors."""
        sensor1 = TemperatureSensor("test_temp")
        sensor2 = HumiditySensor("test_humid")
        self.manager.add_sensor(sensor1)
        self.manager.add_sensor(sensor2)
        
        readings = self.manager.read_all()
        self.assertEqual(len(readings), 2)
        self.assertIn("test_temp", readings)
        self.assertIn("test_humid", readings)
        
        # Check that readings have the correct type
        self.assertTrue(readings["test_temp"].is_valid)
        self.assertEqual(readings["test_temp"].sensor_id, "test_temp")
    
    def test_connect_disconnect_all(self):
        """Test connecting and disconnecting all sensors."""
        sensor1 = TemperatureSensor("test_temp")
        sensor2 = HumiditySensor("test_humid")
        self.manager.add_sensor(sensor1)
        self.manager.add_sensor(sensor2)
        
        # Test connect
        failed = self.manager.connect_all()
        self.assertEqual(len(failed), 0)
        self.assertTrue(sensor1.is_connected)
        self.assertTrue(sensor2.is_connected)
        
        # Test disconnect
        self.manager.disconnect_all()
        self.assertFalse(sensor1.is_connected)
        self.assertFalse(sensor2.is_connected)

class TestTemperatureSensor(unittest.TestCase):
    """Test cases for the Temperature Sensor."""
    
    def setUp(self):
        """Set up test fixtures before each test."""
        self.sensor = TemperatureSensor("test_temp")
    
    def test_sensor_initialization(self):
        """Test sensor initialization."""
        self.assertEqual(self.sensor.sensor_id, "test_temp")
        self.assertEqual(self.sensor.name, "Temperature")
        self.assertFalse(self.sensor.is_connected)
    
    def test_read(self):
        """Test reading from the sensor."""
        reading = self.sensor.read()
        self.assertIsNotNone(reading)
        self.assertEqual(reading.sensor_id, "test_temp")
        self.assertEqual(reading.unit, "°C")
        self.assertTrue(reading.is_valid)
    
    def test_calibration(self):
        """Test sensor calibration."""
        # Mock the read_raw method to return a consistent value
        with patch.object(TemperatureSensor, 'read_raw', return_value=20.0):
            # Calibrate to make sensor read 22.0 when raw value is 20.0
            self.sensor.calibrate(22.0)
            self.assertEqual(self.sensor.calibration_offset, 2.0)
            
            # Check that the calibration is applied
            reading = self.sensor.read()
            self.assertAlmostEqual(reading.value, 22.0, delta=0.1)

if __name__ == '__main__':
    unittest.main()