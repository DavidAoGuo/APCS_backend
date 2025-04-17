"""
API Routes for the APCS.
Defines the REST endpoints and WebSocket communication.
"""
import time
import json
import logging
import secrets
import datetime
from typing import Dict, List, Optional, Any, Union
from functools import wraps
from flask import Flask, request, jsonify, Response
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import jwt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("API")

# Import necessary components from other modules
# In a real implementation, these would be proper imports
try:
    from control_system.sensor_manager import SensorManager
    from control_system.actuator_controller import ActuatorController
    from control_system.data_processor import DataProcessor
    from api.models import (
        User, UserRole, SensorDataPoint, ActuatorStatus, 
        SystemStatus, ApiResponse, ScheduledEvent, SystemConfiguration
    )
except ImportError:
    # Create mock imports for development
    logger.warning("Using mock imports for development")
    
    class UserRole:
        VIEWER = "viewer"
        OPERATOR = "operator"
        ADMIN = "admin"
    
    class User:
        def __init__(self, user_id, username, email, role):
            self.user_id = user_id
            self.username = username
            self.email = email
            self.role = role
    
    class SensorDataPoint:
        def __init__(self, value, unit, timestamp, sensor_id, is_valid=True):
            self.value = value
            self.unit = unit
            self.timestamp = timestamp
            self.sensor_id = sensor_id
            self.is_valid = is_valid
    
    class ActuatorStatus:
        def __init__(self, actuator_id, name, state, current_power, last_activated, activation_count, error_message=None):
            self.actuator_id = actuator_id
            self.name = name
            self.state = state
            self.current_power = current_power
            self.last_activated = last_activated
            self.activation_count = activation_count
            self.error_message = error_message
    
    class SystemStatus:
        def __init__(self, timestamp, sensors, actuators, environmental, supplies, scheduler, alarms):
            self.timestamp = timestamp
            self.sensors = sensors
            self.actuators = actuators
            self.environmental = environmental
            self.supplies = supplies
            self.scheduler = scheduler
            self.alarms = alarms
    
    class ApiResponse:
        def __init__(self, success, message, data=None, errors=None, timestamp=None):
            self.success = success
            self.message = message
            self.data = data
            self.errors = errors
            self.timestamp = timestamp or time.time()
    
    class SensorManager:
        def read_all(self): return {}
    
    class ActuatorController:
        def activate_actuator(self, actuator_id, power=1.0, duration=None): return True
        def deactivate_actuator(self, actuator_id): return True
        def get_actuator(self, actuator_id): return None
        def get_all_actuators(self): return {}
    
    class DataProcessor:
        def get_system_status(self): return {"timestamp": time.time()}
        def add_rule(self, rule): pass
        def remove_rule(self, rule_id): return True
        def get_rule(self, rule_id): return None


# Create the Flask app and SocketIO instance
app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
CORS(app)  # Enable CORS for all routes
socketio = SocketIO(app, cors_allowed_origins="*")

# JWT configuration
JWT_SECRET = app.config['SECRET_KEY']
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION = 86400  # 24 hours in seconds

# Mock users database (in a real app, this would be a database)
users_db = {
    "admin": User(
        user_id="1",
        username="admin",
        email="admin@example.com",
        role=UserRole.ADMIN
    ),
    "operator": User(
        user_id="2",
        username="operator",
        email="operator@example.com",
        role=UserRole.OPERATOR
    ),
    "viewer": User(
        user_id="3",
        username="viewer",
        email="viewer@example.com",
        role=UserRole.VIEWER
    )
}

# Mock passwords (in a real app, these would be hashed)
passwords_db = {
    "admin": "admin123",
    "operator": "operator123",
    "viewer": "viewer123"
}


# Authentication utilities
def generate_token(user: User) -> str:
    """Generate a JWT for the user."""
    payload = {
        'user_id': user.user_id,
        'username': user.username,
        'role': user.role.value if isinstance(user.role, UserRole) else user.role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=JWT_EXPIRATION)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def validate_token(token: str) -> Optional[Dict[str, Any]]:
    """Validate a JWT and return the payload if valid."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Expired token")
        return None
    except jwt.InvalidTokenError:
        logger.warning("Invalid token")
        return None


def requires_auth(f):
    """Decorator to require authentication for routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify(ApiResponse(
                success=False,
                message="Authentication required",
                errors=["No valid authentication token provided"]
            ).__dict__), 401
        
        token = auth_header.split(' ')[1]
        payload = validate_token(token)
        if not payload:
            return jsonify(ApiResponse(
                success=False,
                message="Authentication failed",
                errors=["Invalid or expired token"]
            ).__dict__), 401
        
        # Add user info to request context
        request.user = payload
        return f(*args, **kwargs)
    return decorated


def requires_role(roles):
    """Decorator to require specific roles for routes."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # This decorator should be used after requires_auth
            if not hasattr(request, 'user'):
                return jsonify(ApiResponse(
                    success=False,
                    message="Authentication required",
                    errors=["No authentication context"]
                ).__dict__), 401
            
            user_role = request.user.get('role')
            
            # Convert roles to their string values for comparison
            role_values = []
            for role in roles:
                if hasattr(role, 'value'):
                    role_values.append(role.value)
                else:
                    role_values.append(role)
            
            if not user_role or user_role not in role_values:
                return jsonify(ApiResponse(
                    success=False,
                    message="Access denied",
                    errors=["Insufficient permissions"]
                ).__dict__), 403
            
            return f(*args, **kwargs)
        return decorated
    return decorator


class ApiHandler:
    """Handler for API routes, connecting to the control system."""
    
    def __init__(self, sensor_manager: SensorManager, 
                 actuator_controller: ActuatorController,
                 data_processor: DataProcessor):
        self.sensor_manager = sensor_manager
        self.actuator_controller = actuator_controller
        self.data_processor = data_processor
        self.clients = set()  # For tracking WebSocket clients
        self.status_broadcast_running = False
        logger.info("API Handler initialized")
    
    def setup_routes(self, app: Flask) -> None:
        """Set up all API routes."""
        # Authentication routes
        app.route('/api/auth/login', methods=['POST'])(self.login)
        app.route('/api/auth/validate', methods=['GET'])(requires_auth(self.validate_token))
        
        # System status routes
        app.route('/api/system/status', methods=['GET'])(requires_auth(self.get_system_status))
        app.route('/api/sensors', methods=['GET'])(requires_auth(self.get_all_sensors))
        app.route('/api/sensors/<sensor_id>', methods=['GET'])(requires_auth(self.get_sensor))
        app.route('/api/actuators', methods=['GET'])(requires_auth(self.get_all_actuators))
        app.route('/api/actuators/<actuator_id>', methods=['GET'])(requires_auth(self.get_actuator))
        
        # Control routes (require operator or admin role)
        app.route('/api/actuators/<actuator_id>/activate', methods=['POST'])(
            requires_auth(requires_role([UserRole.OPERATOR, UserRole.ADMIN])(self.activate_actuator))
        )
        app.route('/api/actuators/<actuator_id>/deactivate', methods=['POST'])(
            requires_auth(requires_role([UserRole.OPERATOR, UserRole.ADMIN])(self.deactivate_actuator))
        )
        
        # Rules routes
        app.route('/api/rules', methods=['GET'])(requires_auth(self.get_rules))
        app.route('/api/rules/<rule_id>', methods=['GET'])(requires_auth(self.get_rule))
        app.route('/api/rules', methods=['POST'])(
            requires_auth(requires_role([UserRole.ADMIN])(self.add_rule))
        )
        app.route('/api/rules/<rule_id>', methods=['DELETE'])(
            requires_auth(requires_role([UserRole.ADMIN])(self.delete_rule))
        )
        
        # Configuration routes (admin only)
        app.route('/api/config', methods=['GET'])(
            requires_auth(requires_role([UserRole.ADMIN])(self.get_config))
        )
        app.route('/api/config', methods=['PUT'])(
            requires_auth(requires_role([UserRole.ADMIN])(self.update_config))
        )
        
        # Scheduled events routes
        app.route('/api/events', methods=['GET'])(requires_auth(self.get_events))
        app.route('/api/events', methods=['POST'])(
            requires_auth(requires_role([UserRole.ADMIN])(self.add_event))
        )
        app.route('/api/events/<event_id>', methods=['DELETE'])(
            requires_auth(requires_role([UserRole.ADMIN])(self.delete_event))
        )
        
        logger.info("API routes setup complete")
    
    def setup_socketio(self, socketio: SocketIO) -> None:
        """Set up SocketIO event handlers."""
        @socketio.on('connect')
        def handle_connect():
            logger.info(f"Client connected: {request.sid}")
            self.clients.add(request.sid)
            # Start status broadcast if not already running
            if not self.status_broadcast_running:
                self.start_status_broadcast()
        
        @socketio.on('disconnect')
        def handle_disconnect():
            logger.info(f"Client disconnected: {request.sid}")
            self.clients.remove(request.sid)
            # Stop broadcast if no clients
            if not self.clients and self.status_broadcast_running:
                self.stop_status_broadcast()
        
        @socketio.on('request_status')
        def handle_status_request():
            # Send immediate status update
            status = self.data_processor.get_system_status()
            emit('status_update', status)
        
        logger.info("SocketIO events setup complete")
    
    def start_status_broadcast(self) -> None:
        """Start broadcasting status updates to connected clients."""
        self.status_broadcast_running = True
        
        def broadcast_status():
            while self.status_broadcast_running and self.clients:
                status = self.data_processor.get_system_status()
                socketio.emit('status_update', status, room=None)  # Broadcast to all clients
                socketio.sleep(2)  # Update every 2 seconds
        
        socketio.start_background_task(broadcast_status)
        logger.info("Status broadcast started")
    
    def stop_status_broadcast(self) -> None:
        """Stop broadcasting status updates."""
        self.status_broadcast_running = False
        logger.info("Status broadcast stopped")
    
    # Authentication route handlers
    def login(self) -> Response:
        """Handle user login and token generation."""
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify(ApiResponse(
                success=False,
                message="Login failed",
                errors=["Username and password are required"]
            ).__dict__), 400
        
        # Check if user exists and password is correct
        if username not in users_db or passwords_db.get(username) != password:
            return jsonify(ApiResponse(
                success=False,
                message="Login failed",
                errors=["Invalid username or password"]
            ).__dict__), 401
        
        # Generate token
        user = users_db[username]
        token = generate_token(user)
        
        # Update last login
        user.last_login = time.time()
        
        return jsonify(ApiResponse(
            success=True,
            message="Login successful",
            data={"token": token, "user": {
                "username": user.username,
                "email": user.email,
                "role": user.role.value if isinstance(user.role, UserRole) else user.role
            }}
        ).__dict__)
    
    def validate_token(self) -> Response:
        """Validate the current token."""
        return jsonify(ApiResponse(
            success=True,
            message="Token is valid",
            data={"user": request.user}
        ).__dict__)
    
    # System status route handlers
    def get_system_status(self) -> Response:
        """Get the current system status."""
        status = self.data_processor.get_system_status()
        
        return jsonify(ApiResponse(
            success=True,
            message="System status retrieved",
            data=status
        ).__dict__)
    
    def get_all_sensors(self) -> Response:
        """Get data from all sensors."""
        readings = self.sensor_manager.read_all()
        
        return jsonify(ApiResponse(
            success=True,
            message="Sensor readings retrieved",
            data=readings
        ).__dict__)
    
    def get_sensor(self, sensor_id: str) -> Response:
        """Get data from a specific sensor."""
        readings = self.sensor_manager.read_all()
        
        if sensor_id not in readings:
            return jsonify(ApiResponse(
                success=False,
                message="Sensor not found",
                errors=[f"No sensor with ID {sensor_id}"]
            ).__dict__), 404
        
        return jsonify(ApiResponse(
            success=True,
            message=f"Sensor {sensor_id} data retrieved",
            data=readings[sensor_id]
        ).__dict__)
    
    def get_all_actuators(self) -> Response:
        """Get status of all actuators."""
        actuators = self.actuator_controller.get_all_actuators()
        
        return jsonify(ApiResponse(
            success=True,
            message="Actuator statuses retrieved",
            data=actuators
        ).__dict__)
    
    def get_actuator(self, actuator_id: str) -> Response:
        """Get status of a specific actuator."""
        actuator = self.actuator_controller.get_actuator(actuator_id)
        
        if not actuator:
            return jsonify(ApiResponse(
                success=False,
                message="Actuator not found",
                errors=[f"No actuator with ID {actuator_id}"]
            ).__dict__), 404
        
        return jsonify(ApiResponse(
            success=True,
            message=f"Actuator {actuator_id} status retrieved",
            data=actuator
        ).__dict__)
    
    # Control route handlers
    def activate_actuator(self, actuator_id: str) -> Response:
        """Activate a specific actuator."""
        data = request.get_json()
        power = data.get('power', 1.0)
        duration = data.get('duration')
        
        result = self.actuator_controller.activate_actuator(actuator_id, power, duration)
        
        if not result:
            return jsonify(ApiResponse(
                success=False,
                message="Activation failed",
                errors=[f"Failed to activate actuator {actuator_id}"]
            ).__dict__), 400
        
        return jsonify(ApiResponse(
            success=True,
            message=f"Actuator {actuator_id} activated",
            data={"power": power, "duration": duration}
        ).__dict__)
    
    def deactivate_actuator(self, actuator_id: str) -> Response:
        """Deactivate a specific actuator."""
        result = self.actuator_controller.deactivate_actuator(actuator_id)
        
        if not result:
            return jsonify(ApiResponse(
                success=False,
                message="Deactivation failed",
                errors=[f"Failed to deactivate actuator {actuator_id}"]
            ).__dict__), 400
        
        return jsonify(ApiResponse(
            success=True,
            message=f"Actuator {actuator_id} deactivated"
        ).__dict__)
    
    # Rules route handlers
    def get_rules(self) -> Response:
        """Get all automation rules."""
        # In a real implementation, this would get rules from the data processor
        # For this example, we'll return mock data
        rules = {
            "rule1": {
                "name": "Low Temperature Rule",
                "conditions": ["temperature < 15°C"],
                "actions": ["Activate heater"]
            },
            "rule2": {
                "name": "Low Food Rule",
                "conditions": ["food level < 20%"],
                "actions": ["Send notification"]
            }
        }
        
        return jsonify(ApiResponse(
            success=True,
            message="Rules retrieved",
            data=rules
        ).__dict__)
    
    def get_rule(self, rule_id: str) -> Response:
        """Get a specific automation rule."""
        rule = self.data_processor.get_rule(rule_id)
        
        if not rule:
            return jsonify(ApiResponse(
                success=False,
                message="Rule not found",
                errors=[f"No rule with ID {rule_id}"]
            ).__dict__), 404
        
        return jsonify(ApiResponse(
            success=True,
            message=f"Rule {rule_id} retrieved",
            data=rule
        ).__dict__)
    
    def add_rule(self) -> Response:
        """Add a new automation rule."""
        data = request.get_json()
        
        # In a real implementation, this would create and add a rule
        # For this example, we'll just log it
        logger.info(f"Adding rule: {data}")
        
        return jsonify(ApiResponse(
            success=True,
            message="Rule added",
            data={"rule_id": "new_rule_id"}
        ).__dict__)
    
    def delete_rule(self, rule_id: str) -> Response:
        """Delete an automation rule."""
        result = self.data_processor.remove_rule(rule_id)
        
        if not result:
            return jsonify(ApiResponse(
                success=False,
                message="Rule deletion failed",
                errors=[f"No rule with ID {rule_id}"]
            ).__dict__), 404
        
        return jsonify(ApiResponse(
            success=True,
            message=f"Rule {rule_id} deleted"
        ).__dict__)
    
    # Configuration route handlers
    def get_config(self) -> Response:
        """Get the system configuration."""
        # In a real implementation, this would get configuration from the data processor
        # For this example, we'll return mock data
        config = {
            "temperature_range": (15.0, 30.0),
            "humidity_range": (40.0, 70.0),
            "food_level_threshold": 20.0,
            "water_level_threshold": 15.0,
            "feeding_schedule": [
                {"time": "08:00", "amount": 1.0},
                {"time": "18:00", "amount": 1.0}
            ],
            "notifications_enabled": True,
            "smart_home_integration": {
                "google_home": True,
                "alexa": True
            }
        }
        
        return jsonify(ApiResponse(
            success=True,
            message="Configuration retrieved",
            data=config
        ).__dict__)
    
    def update_config(self) -> Response:
        """Update the system configuration."""
        data = request.get_json()
        
        # In a real implementation, this would update configuration
        # For this example, we'll just log it
        logger.info(f"Updating configuration: {data}")
        
        return jsonify(ApiResponse(
            success=True,
            message="Configuration updated",
            data=data
        ).__dict__)
    
    # Scheduled events route handlers
    def get_events(self) -> Response:
        """Get all scheduled events."""
        # In a real implementation, this would get events from the data processor
        # For this example, we'll return mock data
        events = [
            {
                "event_id": "feeding_1",
                "name": "Morning Feeding",
                "event_type": "feeding",
                "time": "08:00",
                "repeat": "daily",
                "parameters": {"amount": 1.0},
                "last_executed": time.time() - 3600,
                "next_execution": time.time() + 82800
            },
            {
                "event_id": "feeding_2",
                "name": "Evening Feeding",
                "event_type": "feeding",
                "time": "18:00",
                "repeat": "daily",
                "parameters": {"amount": 1.0},
                "last_executed": time.time() - 43200,
                "next_execution": time.time() + 43200
            }
        ]
        
        return jsonify(ApiResponse(
            success=True,
            message="Events retrieved",
            data=events
        ).__dict__)
    
    def add_event(self) -> Response:
        """Add a new scheduled event."""
        data = request.get_json()
        
        # In a real implementation, this would add an event
        # For this example, we'll just log it
        logger.info(f"Adding event: {data}")
        
        return jsonify(ApiResponse(
            success=True,
            message="Event added",
            data={"event_id": "new_event_id"}
        ).__dict__)
    
    def delete_event(self, event_id: str) -> Response:
        """Delete a scheduled event."""
        # In a real implementation, this would delete an event
        # For this example, we'll just log it
        logger.info(f"Deleting event: {event_id}")
        
        return jsonify(ApiResponse(
            success=True,
            message=f"Event {event_id} deleted"
        ).__dict__)


def create_api(sensor_manager, actuator_controller, data_processor):
    """Create and configure the API."""
    api_handler = ApiHandler(sensor_manager, actuator_controller, data_processor)
    api_handler.setup_routes(app)
    api_handler.setup_socketio(socketio)
    return app, socketio, api_handler


# Example usage when running this file directly
if __name__ == "__main__":
    # Create mock components
    sensor_manager = SensorManager()
    actuator_controller = ActuatorController()
    data_processor = DataProcessor(sensor_manager, actuator_controller)
    
    # Create API
    app, socketio, _ = create_api(sensor_manager, actuator_controller, data_processor)
    
    # Run the application
    print("Starting API server at http://127.0.0.1:5000")
    socketio.run(app, host='127.0.0.1', port=5000, debug=True)