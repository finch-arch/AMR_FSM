from enum import Enum
import logging

class State(Enum):
    IDLE = 1
    NAVIGATING = 2
    AVOIDING_OBSTACLE = 3
    RECOVERING_FROM_BLOCKAGE = 4
    DOCKING = 5
    CHARGING = 6
    LOCALIZATION_RECOVERY = 7
    SAFE_STOP = 8
    NETWORK_DEGRADED = 9

class Event(Enum):
    # Safety Critical (Priority 1)
    EMERGENCY_STOP_TRIGGERED = 1
    EMERGENCY_STOP_RELEASED = 2
    
    # System Critical (Priority 2)
    BATTERY_CRITICAL = 3
    
    # Localization (Priority 3)
    LOCALIZATION_LOST = 4
    LOCALIZATION_RECOVERED = 5
    
    # Environment (Priority 4)
    OBSTACLE_DETECTED = 6
    OBSTACLE_CLEARED = 7
    PATH_BLOCKED = 8
    
    # Operational (Priority 5)
    NETWORK_LOST = 9
    NETWORK_RESTORED = 10
    BATTERY_LOW = 11
    BATTERY_OK = 12
    
    # Task / Docking (Priority 6)
    TASK_ASSIGNED = 13
    GOAL_REACHED = 14
    NAVIGATION_TIMEOUT = 15
    DOCK_DETECTED = 16
    DOCK_ALIGNMENT_FAILED = 17
    CHARGING_STARTED = 18
    CHARGING_COMPLETE = 19

# Map event to priority (lower number = higher priority)
EVENT_PRIORITIES = {
    Event.EMERGENCY_STOP_TRIGGERED: 1,
    Event.EMERGENCY_STOP_RELEASED: 1,
    
    Event.BATTERY_CRITICAL: 2,
    
    Event.LOCALIZATION_LOST: 3,
    Event.LOCALIZATION_RECOVERED: 3,
    
    Event.OBSTACLE_DETECTED: 4,
    Event.OBSTACLE_CLEARED: 4,
    Event.PATH_BLOCKED: 4,
    
    Event.NETWORK_LOST: 5,
    Event.NETWORK_RESTORED: 5,
    Event.BATTERY_LOW: 5,
    Event.BATTERY_OK: 5,
    
    Event.TASK_ASSIGNED: 6,
    Event.GOAL_REACHED: 6,
    Event.NAVIGATION_TIMEOUT: 6,
    Event.DOCK_DETECTED: 6,
    Event.DOCK_ALIGNMENT_FAILED: 6,
    Event.CHARGING_STARTED: 6,
    Event.CHARGING_COMPLETE: 6,
}

class Context:
    """Holds variables that act as guards for the FSM."""
    def __init__(self):
        self.has_pending_task = False

class AMRStateMachine:
    def __init__(self):
        self.current_state = State.IDLE
        self.context = Context()
        logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

    def trigger(self, events):
        """
        Accepts a list of simultaneous events, sorts them by priority,
        and processes the highest priority event that causes a valid transition.
        Guarantees determinism when events clash.
        """
        if not events:
            return self.current_state

        if not isinstance(events, list):
            events = [events]

        # Sort by priority
        events.sort(key=lambda e: EVENT_PRIORITIES[e])

        for event in events:
            next_state = self.handle_event(self.current_state, event)
            if next_state != self.current_state:
                logging.info(f"Transition: {self.current_state.name} --({event.name})--> {next_state.name}")
                self.current_state = next_state
                # If a higher priority event causes a transition, drop the lower priority ones for this cycle
                return self.current_state
                
        return self.current_state

    def handle_event(self, current_state: State, event: Event) -> State:
        """
        Core deterministic transition logic. Returns next state.
        No hidden state used. No fall-through logic.
        """
        # Global Preemptions (High Priority)
        if event == Event.EMERGENCY_STOP_TRIGGERED:
            return State.SAFE_STOP
            
        if current_state == State.SAFE_STOP:
            if event == Event.EMERGENCY_STOP_RELEASED:
                return State.IDLE
            return current_state # Block all other events

        if event == Event.BATTERY_CRITICAL and current_state != State.CHARGING:
            return State.DOCKING
            
        if event == Event.NETWORK_LOST:
            return State.NETWORK_DEGRADED
            
        if current_state == State.NETWORK_DEGRADED:
            if event == Event.NETWORK_RESTORED:
                return State.IDLE
            if event != Event.BATTERY_CRITICAL:
                return current_state # Pause non-critical ops

        if event == Event.LOCALIZATION_LOST:
            return State.LOCALIZATION_RECOVERY

        # State-specific Transitions
        if current_state == State.IDLE:
            if event == Event.TASK_ASSIGNED:
                self.context.has_pending_task = True
                return State.NAVIGATING
            elif event == Event.BATTERY_LOW:
                return State.DOCKING

        elif current_state == State.NAVIGATING:
            if event == Event.OBSTACLE_DETECTED:
                return State.AVOIDING_OBSTACLE
            elif event == Event.PATH_BLOCKED:
                return State.RECOVERING_FROM_BLOCKAGE
            elif event == Event.GOAL_REACHED:
                self.context.has_pending_task = False
                return State.IDLE

        elif current_state == State.AVOIDING_OBSTACLE:
            if event == Event.OBSTACLE_CLEARED:
                return State.NAVIGATING
            elif event == Event.PATH_BLOCKED:
                return State.RECOVERING_FROM_BLOCKAGE

        elif current_state == State.RECOVERING_FROM_BLOCKAGE:
            if event == Event.OBSTACLE_CLEARED:
                return State.NAVIGATING
            elif event == Event.NAVIGATION_TIMEOUT:
                self.context.has_pending_task = False
                return State.IDLE

        elif current_state == State.LOCALIZATION_RECOVERY:
            if event == Event.LOCALIZATION_RECOVERED:
                return State.NAVIGATING if self.context.has_pending_task else State.IDLE

        elif current_state == State.DOCKING:
            if event == Event.CHARGING_STARTED:
                return State.CHARGING
            elif event == Event.DOCK_ALIGNMENT_FAILED:
                return State.IDLE

        elif current_state == State.CHARGING:
            if event == Event.CHARGING_COMPLETE:
                return State.IDLE
            elif event == Event.BATTERY_CRITICAL:
                return State.DOCKING

        # If no valid transition, drop the event and remain in current state
        return current_state
