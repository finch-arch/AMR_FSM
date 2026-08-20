import unittest
from fsm import AMRStateMachine, Event, State

class TestAMRStateMachine(unittest.TestCase):

    def setUp(self):
        self.fsm = AMRStateMachine()

    def test_initial_state(self):
        """Test the FSM starts in IDLE state"""
        self.assertEqual(self.fsm.current_state, State.IDLE)

    def test_reachability_all_states(self):
        """Test all states are reachable via valid transitions."""
        
        # IDLE -> NAVIGATING
        self.fsm.trigger(Event.TASK_ASSIGNED)
        self.assertEqual(self.fsm.current_state, State.NAVIGATING)
        
        # NAVIGATING -> AVOIDING_OBSTACLE
        self.fsm.trigger(Event.OBSTACLE_DETECTED)
        self.assertEqual(self.fsm.current_state, State.AVOIDING_OBSTACLE)
        
        # AVOIDING_OBSTACLE -> RECOVERING_FROM_BLOCKAGE
        self.fsm.trigger(Event.PATH_BLOCKED)
        self.assertEqual(self.fsm.current_state, State.RECOVERING_FROM_BLOCKAGE)
        
        # RECOVERING_FROM_BLOCKAGE -> LOCALIZATION_RECOVERY
        self.fsm.trigger(Event.LOCALIZATION_LOST)
        self.assertEqual(self.fsm.current_state, State.LOCALIZATION_RECOVERY)
        
        # LOCALIZATION_RECOVERY -> SAFE_STOP
        self.fsm.trigger(Event.EMERGENCY_STOP_TRIGGERED)
        self.assertEqual(self.fsm.current_state, State.SAFE_STOP)
        
        # SAFE_STOP -> IDLE
        self.fsm.trigger(Event.EMERGENCY_STOP_RELEASED)
        self.assertEqual(self.fsm.current_state, State.IDLE)
        
        # IDLE -> DOCKING
        self.fsm.trigger(Event.BATTERY_LOW)
        self.assertEqual(self.fsm.current_state, State.DOCKING)
        
        # DOCKING -> CHARGING
        self.fsm.trigger(Event.CHARGING_STARTED)
        self.assertEqual(self.fsm.current_state, State.CHARGING)
        
        # Return to IDLE and test NETWORK_DEGRADED
        self.fsm.trigger(Event.CHARGING_COMPLETE)
        self.assertEqual(self.fsm.current_state, State.IDLE)
        
        self.fsm.trigger(Event.NETWORK_LOST)
        self.assertEqual(self.fsm.current_state, State.NETWORK_DEGRADED)

    def test_invalid_transitions_gracefully_dropped(self):
        """Test that sending unrelated events does not crash or change state inappropriately."""
        # While IDLE, obstacle cleared should do nothing
        self.fsm.trigger(Event.OBSTACLE_CLEARED)
        self.assertEqual(self.fsm.current_state, State.IDLE)
        
        # While IDLE, goal reached should do nothing
        self.fsm.trigger(Event.GOAL_REACHED)
        self.assertEqual(self.fsm.current_state, State.IDLE)
        
        # Transition to charging
        self.fsm.trigger(Event.BATTERY_LOW)
        self.fsm.trigger(Event.CHARGING_STARTED)
        self.assertEqual(self.fsm.current_state, State.CHARGING)
        
        # While CHARGING, task assigned should be ignored (battery needs to finish charging)
        self.fsm.trigger(Event.TASK_ASSIGNED)
        self.assertEqual(self.fsm.current_state, State.CHARGING)

    def test_event_priority_determinism(self):
        """Test that high priority events preempt lower priority ones perfectly."""
        # 3 events injected simultaneously: Task Assigned (6), Battery Critical (2), E-Stop (1)
        self.fsm.trigger([Event.TASK_ASSIGNED, Event.BATTERY_CRITICAL, Event.EMERGENCY_STOP_TRIGGERED])
        
        # E-Stop is Priority 1, so it should win
        self.assertEqual(self.fsm.current_state, State.SAFE_STOP)

    def test_high_frequency_event_spam(self):
        """Test FSM doesn't break when spammed with every single event."""
        all_events = [e for e in Event]
        # Reverse list, shuffle it, etc. We will just pass the entire list.
        # Highest priority (E-Stop) should always win if present.
        self.fsm.trigger(all_events)
        self.assertEqual(self.fsm.current_state, State.SAFE_STOP)
        
        # Release E-stop
        self.fsm.trigger(Event.EMERGENCY_STOP_RELEASED)
        self.assertEqual(self.fsm.current_state, State.IDLE)
        
        # Spam all events EXCEPT E-stop
        no_estop = [e for e in Event if e not in [Event.EMERGENCY_STOP_TRIGGERED, Event.EMERGENCY_STOP_RELEASED]]
        self.fsm.trigger(no_estop)
        # Next highest priority is BATTERY_CRITICAL (Priority 2)
        # So it should end up in DOCKING
        self.assertEqual(self.fsm.current_state, State.DOCKING)

    def test_context_variables(self):
        """Test guard context: localization recovery should know if it was navigating or idle."""
        # Case A: Idle -> Localization lost -> Recovered -> Idle
        self.fsm.trigger(Event.LOCALIZATION_LOST)
        self.assertEqual(self.fsm.current_state, State.LOCALIZATION_RECOVERY)
        self.fsm.trigger(Event.LOCALIZATION_RECOVERED)
        self.assertEqual(self.fsm.current_state, State.IDLE)
        
        # Case B: Navigating -> Localization lost -> Recovered -> Navigating
        self.fsm.trigger(Event.TASK_ASSIGNED)
        self.assertEqual(self.fsm.current_state, State.NAVIGATING)
        self.fsm.trigger(Event.LOCALIZATION_LOST)
        self.assertEqual(self.fsm.current_state, State.LOCALIZATION_RECOVERY)
        self.fsm.trigger(Event.LOCALIZATION_RECOVERED)
        # Context remembers it had a pending task
        self.assertEqual(self.fsm.current_state, State.NAVIGATING)

if __name__ == '__main__':
    unittest.main()
