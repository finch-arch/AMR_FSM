import time
import logging
from fsm import AMRStateMachine, Event, State

def run_scenario(scenario_name, fsm, events):
    print(f"\n{'='*50}")
    print(f"Executing Scenario: {scenario_name}")
    print(f"{'='*50}")
    
    # Reset FSM for new scenario
    fsm.current_state = State.IDLE
    fsm.context.has_pending_task = False
    print(f"Initial State: {fsm.current_state.name}")
    
    for event_group in events:
        if not isinstance(event_group, list):
            event_group = [event_group]
            
        names = [e.name for e in event_group]
        print(f"\n--- Injecting Events: {names} ---")
        fsm.trigger(event_group)
        print(f"Current State: {fsm.current_state.name}")
        time.sleep(0.1) # Simulate tick

if __name__ == "__main__":
    # Disable default root logger from fsm.py to format our own prints
    logging.getLogger().setLevel(logging.CRITICAL)
    
    fsm = AMRStateMachine()

    # Scenario 1: The Complex Navigation Example from the PDF
    scenario_1 = [
        Event.TASK_ASSIGNED,
        Event.OBSTACLE_DETECTED,
        Event.PATH_BLOCKED,
        Event.LOCALIZATION_LOST,
        # Attempting to send localizer recovered, but maybe it takes a few ticks
        Event.LOCALIZATION_RECOVERED,
        Event.GOAL_REACHED
    ]
    run_scenario("1. PDF Example (Obstacles & Localization Loss)", fsm, scenario_1)

    # Scenario 2: Emergency Stop During Docking
    scenario_2 = [
        Event.BATTERY_LOW,
        Event.DOCK_DETECTED,
        # Robot is docking. Suddenly, an emergency stop is hit!
        Event.EMERGENCY_STOP_TRIGGERED,
        # While E-stop is active, trying to send docking events should be dropped
        Event.CHARGING_STARTED, 
        Event.EMERGENCY_STOP_RELEASED,
        # Robot goes back to IDLE, realizes battery is low, and resumes docking
        Event.BATTERY_LOW, 
        Event.CHARGING_STARTED,
        Event.CHARGING_COMPLETE
    ]
    run_scenario("2. Emergency Stop During Docking", fsm, scenario_2)

    # Scenario 3: Battery Critical While Network Lost
    scenario_3 = [
        Event.TASK_ASSIGNED,
        Event.NETWORK_LOST, # Enters NETWORK_DEGRADED
        # Oh no, while network is lost, battery goes critical!
        Event.BATTERY_CRITICAL, # Should autonomously override to DOCKING
        Event.CHARGING_STARTED,
        Event.NETWORK_RESTORED,
        Event.CHARGING_COMPLETE # Goes to IDLE since task context was lost/paused, but safe
    ]
    run_scenario("3. Battery Critical While Network Lost", fsm, scenario_3)

    # Scenario 4: Simultaneous Conflicting Events (Determinism Check)
    # Testing that priority resolves conflicts. E_STOP > BATTERY_CRITICAL > OBSTACLE
    scenario_4 = [
        Event.TASK_ASSIGNED,
        # Send 3 massive events at the exact same time
        [Event.OBSTACLE_DETECTED, Event.EMERGENCY_STOP_TRIGGERED, Event.BATTERY_CRITICAL],
        # The FSM must resolve this deterministically to SAFE_STOP
        Event.EMERGENCY_STOP_RELEASED, # Now battery is critical
        Event.BATTERY_CRITICAL,
        Event.CHARGING_STARTED
    ]
    run_scenario("4. Conflicting Simultaneous Events", fsm, scenario_4)

    # Scenario 5: Rapid Oscillating Obstacles (Debounce Check)
    scenario_5 = [
        Event.TASK_ASSIGNED,
        # Sensor rapidly flickers due to noise
        [Event.OBSTACLE_DETECTED, Event.OBSTACLE_CLEARED],
        [Event.OBSTACLE_CLEARED, Event.OBSTACLE_DETECTED],
        Event.OBSTACLE_CLEARED,
        Event.GOAL_REACHED
    ]
    run_scenario("5. Rapid Oscillating Obstacles", fsm, scenario_5)
