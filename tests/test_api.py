# tests/test_api.py
import unittest
import json
from unittest.mock import patch, MagicMock
from flask import Flask
from flask_socketio import SocketIO

# We'll need a function to create a fresh Flask app each time
def create_test_app():
    """Create a fresh Flask app for testing."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test_secret_key'
    return app

class TestAPI(unittest.TestCase):
    """Test cases for the API."""
    
    @classmethod
    def setUpClass(cls):
        """Set up fixtures for all tests in the class."""
        # Import here to avoid app creation during module import
        from api.routes import ApiHandler
        
        # Store the ApiHandler class for use in setUp
        cls.ApiHandlerClass = ApiHandler
    
    # Modify in tests/test_api.py
    def setUp(self):
        """Set up test fixtures before each test."""
        # Create mock components
        self.sensor_manager = MagicMock()
        self.actuator_controller = MagicMock()
        self.data_processor = MagicMock()
        
        # Create more realistic mock objects that can be JSON serialized
        # For sensor readings, create a dict with the right attributes instead of a MagicMock
        mock_reading = {
            "value": 22.0,
            "unit": "°C",
            "timestamp": 123456789,
            "sensor_id": "temp_1",
            "is_valid": True
        }
        self.sensor_manager.read_all.return_value = {"temp_1": mock_reading}
        
        # For actuator status
        mock_actuator = {
            "actuator_id": "food_1",
            "name": "Food Dispenser",
            "state": "IDLE",
            "current_power": 0.0,
            "last_activated": 0,
            "activation_count": 0
        }
        self.actuator_controller.get_all_actuators.return_value = {"food_1": mock_actuator}
        
        # System status
        self.data_processor.get_system_status.return_value = {
            "timestamp": 123456789,
            "sensors": {},
            "actuators": {},
            "environmental": {},
            "sues": {},
            "scheduler": {},
            "alarms": []
        }
        
        # Create a fresh Flask app for each test
        self.app = create_test_app()
        self.socketio = SocketIO(self.app)
        
        # Create API handler and set up routes
        self.api_handler = self.ApiHandlerClass(
            self.sensor_manager, 
            self.actuator_controller, 
            self.data_processor
        )
        self.api_handler.setup_routes(self.app)
        
        # Configure the Flask test client
        self.client = self.app.test_client()
        
        # Mock JWT token generation to return a known token
        self.jwt_mock = patch('api.routes.generate_token').start()
        self.jwt_mock.return_value = "test_token"
        
        # Mock token validation to return a test payload
        self.validate_mock = patch('api.routes.validate_token').start()
        self.validate_mock.return_value = {
            "user_id": "1", 
            "username": "test_user", 
            "role": "admin"
        }
    
    def tearDown(self):
        """Clean up after each test."""
        patch.stopall()
    
    def test_login(self):
        """Test the login endpoint."""
        # Test with valid credentials
        response = self.client.post(
            '/api/auth/login',
            json={"username": "admin", "password": "admin123"}
        )
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["success"])
        self.assertIn("token", data["data"])
        
        # Test with invalid credentials
        response = self.client.post(
            '/api/auth/login',
            json={"username": "invalid", "password": "wrong"}
        )
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 401)
        self.assertFalse(data["success"])
    
    def test_get_system_status(self):
        """Test the system status endpoint."""
        # Set the Authorization header
        headers = {'Authorization': 'Bearer test_token'}
        
        response = self.client.get('/api/system/status', headers=headers)
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["success"])
        self.assertIn("data", data)
        
        # Verify that the data processor was called
        self.data_processor.get_system_status.assert_called_once()
    
    def test_get_sensors(self):
        """Test the sensors endpoint."""
        headers = {'Authorization': 'Bearer test_token'}
        
        response = self.client.get('/api/sensors', headers=headers)
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["success"])
        
        # Verify that the sensor manager was called
        self.sensor_manager.read_all.assert_called_once()
    
    def test_activate_actuator(self):
        """Test the activate actuator endpoint."""
        headers = {'Authorization': 'Bearer test_token'}
        
        # Configure the mock
        self.actuator_controller.activate_actuator.return_value = True
        
        # Import the UserRole enum
        from api.models import UserRole

        # We need to make sure our mock returns the right role string format
        self.validate_mock.return_value = {
            "user_id": "1", 
            "username": "test_user", 
            "role": UserRole.ADMIN.value  # This needs to match what's in the requires_role decorator
        }
        
        response = self.client.post(
            '/api/actuators/food_1/activate',
            json={"power": 0.8, "duration": 5.0},
            headers=headers
        )
        
        # Print response data to see the error
        print(f"Response status: {response.status_code}")
        print(f"Response data: {response.data.decode('utf-8')}")
        
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["success"])
        
        # Verify that the actuator controller was called with correct parameters
        self.actuator_controller.activate_actuator.assert_called_once_with(
            "food_1", 0.8, 5.0
        )
    
    def test_authorization_required(self):
        """Test that endpoints require authorization."""
        # Try to access an endpoint without auth header
        response = self.client.get('/api/system/status')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 401)
        self.assertFalse(data["success"])


if __name__ == '__main__':
    unittest.main()