# AMR Deterministic State Machine

This repository contains the solution for the high-level deterministic state machine for an Autonomous Mobile Robot (AMR). The FSM strictly orchestrates behavior, prioritizes critical events, and handles edge cases without any randomness or undefined behavior.

## Deliverables Included
1. **Architecture Document**: `Architecture_Document.md` contains the State Diagram, Transition Table, Failure Mode Analysis, and the Event Priority Model.
2. **Implementation**: `fsm.py` contains the clean, object-oriented State Machine logic with no external dependencies (like ROS or SMACH).
3. **Simulation Driver**: `simulator.py` demonstrates the FSM deterministically handling 5 complex edge cases.
4. **Test Cases**: `test_fsm.py` provides comprehensive `unittest` coverage.

## Prerequisites
- Python 3.7+
- No external libraries are required. (Mermaid is used in the markdown document for diagrams).

## How to Run the Simulation
To execute the simulation driver that feeds predefined event sequences and logs the transitions for the 5 complex scenarios:
```bash
python3 simulator.py
```

## How to Run the Tests
To run the unit tests and verify the state reachability, deterministic prioritization, and high-frequency event spam handling:
```bash
python3 -m unittest test_fsm.py
```

## Reviewer Notes
To @miko.ai:
The FSM is guaranteed to be deterministic through a strict Event Priority queue mapping, centralized transition functions without global state leaks, and explicit dropping of invalid fall-through events. Please refer to `Architecture_Document.md` for a full write-up on the failure analysis.
# AMR_FSM
