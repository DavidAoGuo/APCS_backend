"""
Data Processor for the Automated Pet Care System.
This module handles sensor data analysis, decision-making logic for automation,
and scheduling of regular tasks.
"""
import time
import logging
import threading
import datetime
import json
from typing import Dict, List, Optional, Any, Callable, Tuple
from enum import Enum, auto
import heapq
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DataProcessor")

# Import necessary components from other modules
# In a real implementation, these would be proper imports
# For this example, we'll define stub classes to represent them
try:
    from control_system.sensor_manager import SensorManager, SensorReading
    from control_system.actuator_controller import ActuatorController, ActuatorState
except ImportError:
    # Stub classes for development
    class SensorManager:
        def read_all(self): return {}
    
    class SensorReading:
        def __init__(self, value=0, unit="", timestamp=0, sensor_id="", is_valid=True):
            self.value = value
            self.unit = unit
            self.timestamp = timestamp
            self.sensor_id = sensor_id
            self.is_valid = is_valid
    
    class ActuatorController:
        def activate_actuator(self, actuator_id, power=1.0, duration=None): return True
        def deactivate_actuator(self, actuator_id): return True
        def get_actuator(self, actuator_id): return None
    
    class ActuatorState(Enum):
        IDLE = auto()
        ACTIVE = auto()


class TaskPriority(Enum):
    """Priority levels for scheduled tasks."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass(order=True)
class ScheduledTask:
    """
    Task scheduled for execution at a specific time.
    The dataclass is ordered by execution_time to work with a priority queue.
    """
    execution_time: float
    priority: TaskPriority = field(compare=False)
    task_id: str = field(compare=False)
    function: Callable = field(compare=False)
    args: tuple = field(default_factory=tuple, compare=False)
    kwargs: dict = field(default_factory=dict, compare=False)
    repeat_interval: Optional[float] = field(default=None, compare=False)
    
    def execute(self) -> bool:
        """Execute the task and return success status."""
        try:
            self.function(*self.args, **self.kwargs)
            return True
        except Exception as e:
            logger.error(f"Error executing task {self.task_id}: {str(e)}")
            return False


class ConditionType(Enum):
    """Types of conditions for rules."""
    GREATER_THAN = auto()
    LESS_THAN = auto()
    EQUAL_TO = auto()
    NOT_EQUAL_TO = auto()
    BETWEEN = auto()
    NOT_BETWEEN = auto()
    CONTAINS = auto()
    NOT_CONTAINS = auto()
    IS_TRUE = auto()
    IS_FALSE = auto()


class Condition:
    """A condition used in automation rules."""
    
    def __init__(self, 
                 condition_type: ConditionType, 
                 value: Any, 
                 comparison_value: Any = None,
                 second_comparison_value: Any = None):
        self.condition_type = condition_type
        self.value = value
        self.comparison_value = comparison_value
        self.second_comparison_value = second_comparison_value
    
    def evaluate(self) -> bool:
        """Evaluate the condition and return True/False."""
        if self.condition_type == ConditionType.GREATER_THAN:
            return self.value > self.comparison_value
        elif self.condition_type == ConditionType.LESS_THAN:
            return self.value < self.comparison_value
        elif self.condition_type == ConditionType.EQUAL_TO:
            return self.value == self.comparison_value
        elif self.condition_type == ConditionType.NOT_EQUAL_TO:
            return self.value != self.comparison_value
        elif self.condition_type == ConditionType.BETWEEN:
            return self.comparison_value <= self.value <= self.second_comparison_value
        elif self.condition_type == ConditionType.NOT_BETWEEN:
            return not (self.comparison_value <= self.value <= self.second_comparison_value)
        elif self.condition_type == ConditionType.CONTAINS:
            return self.comparison_value in self.value
        elif self.condition_type == ConditionType.NOT_CONTAINS:
            return self.comparison_value not in self.value
        elif self.condition_type == ConditionType.IS_TRUE:
            return bool(self.value)
        elif self.condition_type == ConditionType.IS_FALSE:
            return not bool(self.value)
        else:
            raise ValueError(f"Unknown condition type: {self.condition_type}")


class Rule:
    """
    An automation rule that triggers actions based on conditions.
    """
    
    def __init__(self, rule_id: str, name: str, conditions: List[Condition], 
                 actions: List[Callable], active: bool = True):
        self.rule_id = rule_id
        self.name = name
        self.conditions = conditions
        self.actions = actions
        self.active = active
        self.last_triggered = 0.0
        self.trigger_count = 0
    
    def evaluate(self) -> bool:
        """
        Evaluate all conditions in the rule.
        Returns True if all conditions are met.
        """
        if not self.active:
            return False
            
        return all(condition.evaluate() for condition in self.conditions)
    
    def execute(self) -> bool:
        """
        Execute all actions in the rule.
        Returns True if all actions were executed successfully.
        """
        success = True
        for action in self.actions:
            try:
                action()
            except Exception as e:
                logger.error(f"Error executing action in rule {self.name}: {str(e)}")
                success = False
        
        self.last_triggered = time.time()
        self.trigger_count += 1
        return success


class DataProcessor:
    """
    Main class for processing sensor data, making decisions, and scheduling tasks.
    """
    
    def __init__(self, sensor_manager: SensorManager, actuator_controller: ActuatorController):
        self.sensor_manager = sensor_manager
        self.actuator_controller = actuator_controller
        
        # Data storage
        self.sensor_data_history = {}  # sensor_id -> list of readings
        self.history_max_length = 1000  # Maximum readings to store per sensor
        
        # Rules engine
        self.rules = {}  # rule_id -> Rule
        
        # Task scheduler
        self.task_queue = []  # Priority queue of ScheduledTask objects
        self.scheduler_lock = threading.Lock()
        self.scheduler_thread = None
        self.scheduler_running = False
        
        # Configuration
        self.config = {
            "temperature_range": (15.0, 30.0),  # °C
            "humidity_range": (40.0, 70.0),  # %
            "food_level_threshold": 20.0,  # %
            "water_level_threshold": 15.0,  # %
            "feeding_schedule": [
                {"time": "08:00", "amount": 1.0},
                {"time": "18:00", "amount": 1.0}
            ],
            "data_logging_interval": 300,  # seconds
            "rule_evaluation_interval": 10,  # seconds
        }
        
        logger.info("Data Processor initialized")
    
    def start(self) -> None:
        """Start the data processor, including the scheduler thread."""
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            logger.warning("Scheduler already running")
            return
            
        self.scheduler_running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        # Schedule regular tasks
        self._setup_regular_tasks()
        
        # Set up default rules
        self._setup_default_rules()
        
        logger.info("Data Processor started")
    
    def stop(self) -> None:
        """Stop the data processor and scheduler thread."""
        self.scheduler_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=2.0)
        logger.info("Data Processor stopped")
    
    def process_sensor_data(self) -> Dict[str, Any]:
        """
        Process current sensor data and update history.
        Returns a dictionary of processed data.
        """
        # Get all sensor readings
        readings = self.sensor_manager.read_all()
        
        # Update history
        for sensor_id, reading in readings.items():
            if sensor_id not in self.sensor_data_history:
                self.sensor_data_history[sensor_id] = []
            
            history = self.sensor_data_history[sensor_id]
            history.append(reading)
            
            # Limit history length
            if len(history) > self.history_max_length:
                self.sensor_data_history[sensor_id] = history[-self.history_max_length:]
        
        # Process the readings
        processed_data = {}
        
        # Process temperature data
        temp_readings = [r for sensor_id, r in readings.items() 
                        if "temp" in sensor_id and r.is_valid]
        if temp_readings:
            processed_data["temperature_avg"] = sum(r.value for r in temp_readings) / len(temp_readings)
            processed_data["temperature_min"] = min(r.value for r in temp_readings)
            processed_data["temperature_max"] = max(r.value for r in temp_readings)
        
        # Process humidity data
        humid_readings = [r for sensor_id, r in readings.items() 
                         if "humid" in sensor_id and r.is_valid]
        if humid_readings:
            processed_data["humidity_avg"] = sum(r.value for r in humid_readings) / len(humid_readings)
        
        # Process food level data
        food_readings = [r for sensor_id, r in readings.items() 
                        if "food" in sensor_id and r.is_valid]
        if food_readings:
            processed_data["food_level"] = sum(r.value for r in food_readings) / len(food_readings)
        
        # Process water level data
        water_readings = [r for sensor_id, r in readings.items() 
                         if "water" in sensor_id and r.is_valid]
        if water_readings:
            processed_data["water_level"] = sum(r.value for r in water_readings) / len(water_readings)
        
        # Check for environmental issues
        if "temperature_avg" in processed_data:
            temp_min, temp_max = self.config["temperature_range"]
            processed_data["temperature_in_range"] = temp_min <= processed_data["temperature_avg"] <= temp_max
        
        if "humidity_avg" in processed_data:
            humid_min, humid_max = self.config["humidity_range"]
            processed_data["humidity_in_range"] = humid_min <= processed_data["humidity_avg"] <= humid_max
        
        # Check for low supply levels
        if "food_level" in processed_data:
            processed_data["food_low"] = processed_data["food_level"] < self.config["food_level_threshold"]
        
        if "water_level" in processed_data:
            processed_data["water_low"] = processed_data["water_level"] < self.config["water_level_threshold"]
        
        return processed_data
    
    def evaluate_rules(self, processed_data: Dict[str, Any]) -> List[str]:
        """
        Evaluate all rules against the processed data.
        Returns a list of triggered rule IDs.
        """
        triggered_rules = []
        
        for rule_id, rule in self.rules.items():
            # Update the value in each condition
            for condition in rule.conditions:
                if hasattr(condition.value, "__call__"):
                    # If value is a function, call it to get the actual value
                    data_key = condition.value()
                    if data_key in processed_data:
                        condition.value = processed_data[data_key]
                elif isinstance(condition.value, str) and condition.value in processed_data:
                    # If value is a key in processed_data, use that value
                    condition.value = processed_data[condition.value]
            
            # Evaluate the rule
            if rule.evaluate():
                logger.info(f"Rule triggered: {rule.name}")
                rule.execute()
                triggered_rules.append(rule_id)
        
        return triggered_rules
    
    def add_rule(self, rule: Rule) -> None:
        """Add a rule to the rules engine."""
        self.rules[rule.rule_id] = rule
        logger.info(f"Added rule: {rule.name} (ID: {rule.rule_id})")
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule from the rules engine."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Removed rule with ID {rule_id}")
            return True
        return False
    
    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get a rule by ID."""
        return self.rules.get(rule_id)
    
    def schedule_task(self, task: ScheduledTask) -> None:
        """Schedule a task for execution."""
        with self.scheduler_lock:
            heapq.heappush(self.task_queue, task)
        logger.info(f"Scheduled task {task.task_id} for execution at {datetime.datetime.fromtimestamp(task.execution_time)}")
    
    def schedule_task_at(self, task_id: str, function: Callable, time_str: str, 
                        priority: TaskPriority = TaskPriority.NORMAL,
                        repeat_interval: Optional[float] = None,
                        *args, **kwargs) -> None:
        """
        Schedule a task to run at a specific time of day.
        Args:
            task_id: Unique identifier for the task
            function: Function to execute
            time_str: Time in "HH:MM" format (24-hour)
            priority: Task priority
            repeat_interval: If set, reschedule the task after execution with this interval (seconds)
            *args, **kwargs: Arguments to pass to the function
        """
        # Parse the time string
        hour, minute = map(int, time_str.split(':'))
        
        # Calculate the execution time
        now = datetime.datetime.now()
        target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # If the target time is in the past, schedule for tomorrow
        if target_time < now:
            target_time = target_time + datetime.timedelta(days=1)
        
        # Create and schedule the task
        task = ScheduledTask(
            execution_time=target_time.timestamp(),
            priority=priority,
            task_id=task_id,
            function=function,
            args=args,
            kwargs=kwargs,
            repeat_interval=repeat_interval
        )
        self.schedule_task(task)
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        with self.scheduler_lock:
            # Find and remove the task - this is O(n) but we don't expect many tasks
            for i, task in enumerate(self.task_queue):
                if task.task_id == task_id:
                    # Remove the task by replacing it with the last task and re-heapifying
                    self.task_queue[i] = self.task_queue[-1]
                    self.task_queue.pop()
                    heapq.heapify(self.task_queue)
                    logger.info(f"Cancelled task {task_id}")
                    return True
        
        logger.warning(f"Task {task_id} not found for cancellation")
        return False
    
    def _scheduler_loop(self) -> None:
        """Main loop for the task scheduler."""
        logger.info("Scheduler started")
        
        while self.scheduler_running:
            now = time.time()
            task_to_execute = None
            
            # Check if there's a task to execute
            with self.scheduler_lock:
                if self.task_queue and self.task_queue[0].execution_time <= now:
                    task_to_execute = heapq.heappop(self.task_queue)
            
            # Execute the task if we found one
            if task_to_execute:
                logger.info(f"Executing task: {task_to_execute.task_id}")
                success = task_to_execute.execute()
                
                # Reschedule the task if it's recurring
                if success and task_to_execute.repeat_interval:
                    # Calculate the next execution time
                    next_execution = task_to_execute.execution_time + task_to_execute.repeat_interval
                    
                    # If we missed an execution, schedule for the next interval
                    if next_execution < now:
                        intervals_missed = int((now - task_to_execute.execution_time) / task_to_execute.repeat_interval) + 1
                        next_execution = task_to_execute.execution_time + (intervals_missed * task_to_execute.repeat_interval)
                    
                    # Create a new task with the updated execution time
                    new_task = ScheduledTask(
                        execution_time=next_execution,
                        priority=task_to_execute.priority,
                        task_id=task_to_execute.task_id,
                        function=task_to_execute.function,
                        args=task_to_execute.args,
                        kwargs=task_to_execute.kwargs,
                        repeat_interval=task_to_execute.repeat_interval
                    )
                    
                    # Schedule the new task
                    with self.scheduler_lock:
                        heapq.heappush(self.task_queue, new_task)
                    
                    logger.info(f"Rescheduled task {new_task.task_id} for {datetime.datetime.fromtimestamp(new_task.execution_time)}")
            
            # Sleep a short time to avoid busy waiting
            # But not too long to ensure timely task execution
            time.sleep(0.1)
    
    def _setup_regular_tasks(self) -> None:
        """Set up regular tasks for data processing and system maintenance."""
        # Schedule sensor data processing task
        self.schedule_task(ScheduledTask(
            execution_time=time.time() + 5.0,  # Start after 5 seconds
            priority=TaskPriority.HIGH,
            task_id="process_sensor_data",
            function=self._task_process_data,
            repeat_interval=self.config["rule_evaluation_interval"]
        ))
        
        # Schedule data logging task
        self.schedule_task(ScheduledTask(
            execution_time=time.time() + 10.0,  # Start after 10 seconds
            priority=TaskPriority.NORMAL,
            task_id="data_logging",
            function=self._task_log_data,
            repeat_interval=self.config["data_logging_interval"]
        ))
        
        # Schedule feeding tasks based on config
        for i, feeding in enumerate(self.config["feeding_schedule"]):
            self.schedule_task_at(
                task_id=f"feeding_{i}",
                function=self._task_feed_pet,
                time_str=feeding["time"],
                priority=TaskPriority.HIGH,
                repeat_interval=86400,  # Daily
                amount=feeding["amount"]
            )
    
    def _setup_default_rules(self) -> None:
        """Set up default automation rules."""
        # Rule for low temperature
        self.add_rule(Rule(
            rule_id="rule_low_temp",
            name="Low Temperature Rule",
            conditions=[
                Condition(ConditionType.LESS_THAN, "temperature_avg", self.config["temperature_range"][0])
            ],
            actions=[
                lambda: self._action_adjust_temperature(True)
            ]
        ))
        
        # Rule for high temperature
        self.add_rule(Rule(
            rule_id="rule_high_temp",
            name="High Temperature Rule",
            conditions=[
                Condition(ConditionType.GREATER_THAN, "temperature_avg", self.config["temperature_range"][1])
            ],
            actions=[
                lambda: self._action_adjust_temperature(False)
            ]
        ))
        
        # Rule for low food level
        self.add_rule(Rule(
            rule_id="rule_low_food",
            name="Low Food Level Rule",
            conditions=[
                Condition(ConditionType.LESS_THAN, "food_level", self.config["food_level_threshold"])
            ],
            actions=[
                self._action_notify_low_food
            ]
        ))
        
        # Rule for low water level
        self.add_rule(Rule(
            rule_id="rule_low_water",
            name="Low Water Level Rule",
            conditions=[
                Condition(ConditionType.LESS_THAN, "water_level", self.config["water_level_threshold"])
            ],
            actions=[
                self._action_refill_water
            ]
        ))
    
    def _task_process_data(self) -> None:
        """Task to process sensor data and evaluate rules."""
        processed_data = self.process_sensor_data()
        triggered_rules = self.evaluate_rules(processed_data)
        
        if triggered_rules:
            logger.info(f"Triggered rules: {triggered_rules}")
    
    def _task_log_data(self) -> None:
        """Task to log sensor data for historical analysis."""
        readings = self.sensor_manager.read_all()
        log_data = {
            "timestamp": time.time(),
            "readings": {
                sensor_id: {
                    "value": reading.value,
                    "unit": reading.unit,
                    "valid": reading.is_valid
                }
                for sensor_id, reading in readings.items()
            }
        }
        
        # In a real implementation, this would write to a database or file
        # For this example, we'll just log it
        logger.info(f"Data log: {json.dumps(log_data)}")
    
    def _task_feed_pet(self, amount: float = 1.0) -> None:
        """Task to dispense food at scheduled times."""
        logger.info(f"Scheduled feeding: {amount} portions")
        
        # Activate the food dispenser
        # In a real system, the amount would be converted to a duration or specific amount
        duration = amount * 5.0  # Convert portion to seconds of dispensing
        self.actuator_controller.activate_actuator("food_1", power=0.8, duration=duration)
    
    def _action_adjust_temperature(self, increase: bool) -> None:
        """Action to adjust temperature based on sensor readings."""
        if increase:
            logger.info("Activating heater to increase temperature")
            self.actuator_controller.activate_actuator("heater_1", power=0.6, duration=300)
        else:
            logger.info("Activating fan to decrease temperature")
            self.actuator_controller.activate_actuator("fan_1", power=0.8, duration=300)
    
    def _action_notify_low_food(self) -> None:
        """Action to notify about low food level."""
        # In a real implementation, this would send a notification via the mobile app
        logger.warning("Low food level detected! Please refill soon.")
    
    def _action_refill_water(self) -> None:
        """Action to refill water automatically."""
        logger.info("Refilling water automatically")
        self.actuator_controller.activate_actuator("water_1", power=1.0, duration=10.0)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get the overall system status."""
        # Process current data
        processed_data = self.process_sensor_data()
        
        # Get scheduled tasks
        with self.scheduler_lock:
            pending_tasks = len(self.task_queue)
            next_task = self.task_queue[0].task_id if self.task_queue else None
            next_task_time = datetime.datetime.fromtimestamp(self.task_queue[0].execution_time).strftime("%H:%M:%S") if self.task_queue else None
        
        # Compile status report
        status = {
            "timestamp": time.time(),
            "sensor_data": processed_data,
            "scheduler": {
                "running": self.scheduler_running,
                "pending_tasks": pending_tasks,
                "next_task": next_task,
                "next_task_time": next_task_time
            },
            "system_health": {
                "temperature_ok": processed_data.get("temperature_in_range", True),
                "humidity_ok": processed_data.get("humidity_in_range", True),
                "food_ok": not processed_data.get("food_low", False),
                "water_ok": not processed_data.get("water_low", False)
            }
        }
        
        return status


# Example usage
if __name__ == "__main__":
    # Create mock sensor manager and actuator controller
    sensor_manager = SensorManager()
    actuator_controller = ActuatorController()
    
    # Create data processor
    processor = DataProcessor(sensor_manager, actuator_controller)
    
    # Start the processor
    processor.start()
    
    # Simulate running for a while
    try:
        print("Data processor started. Press Ctrl+C to stop.")
        while True:
            # Get system status every 5 seconds
            time.sleep(5)
            status = processor.get_system_status()
            print(f"System status: {json.dumps(status, indent=2)}")
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        # Stop the processor
        processor.stop()
        print("Data processor stopped.")