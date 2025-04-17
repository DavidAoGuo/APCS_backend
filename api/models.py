"""
Models for the APCS API.
Defines data structures and schema for the API.
"""
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum


class UserRole(Enum):
    """User roles with different permission levels."""
    VIEWER = "viewer"      # Can only view status
    OPERATOR = "operator"  # Can control the system
    ADMIN = "admin"        # Full access including configuration


@dataclass
class User:
    """User data model."""
    user_id: str
    username: str
    email: str
    role: UserRole
    created_at: float = field(default_factory=time.time)
    last_login: Optional[float] = None
    # Note: In a real implementation, we would also have a hashed_password field
    # but for this example, we'll omit it


@dataclass
class SensorDataPoint:
    """Data point from a sensor."""
    value: float
    unit: str
    timestamp: float
    sensor_id: str
    is_valid: bool = True


@dataclass
class ActuatorStatus:
    """Status information for an actuator."""
    actuator_id: str
    name: str
    state: str
    current_power: float
    last_activated: float
    activation_count: int
    error_message: Optional[str] = None


@dataclass
class SystemStatus:
    """Overall system status."""
    timestamp: float
    sensors: Dict[str, SensorDataPoint]
    actuators: Dict[str, ActuatorStatus]
    environmental: Dict[str, Any]
    supplies: Dict[str, Any]
    scheduler: Dict[str, Any]
    alarms: List[Dict[str, Any]]


@dataclass
class ApiResponse:
    """Standard API response format."""
    success: bool
    message: str
    data: Optional[Any] = None
    errors: Optional[List[str]] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class ScheduledEvent:
    """Scheduled event in the system."""
    event_id: str
    name: str
    event_type: str
    time: str
    repeat: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    last_executed: Optional[float] = None
    next_execution: Optional[float] = None


@dataclass
class SystemConfiguration:
    """System configuration settings."""
    temperature_range: tuple
    humidity_range: tuple
    food_level_threshold: float
    water_level_threshold: float
    feeding_schedule: List[Dict[str, Any]]
    notifications_enabled: bool
    smart_home_integration: Dict[str, bool]