# AMR Deterministic State Machine - Architecture Document

## 1. Overview
This document outlines the architecture for a Deterministic State Machine designed to control the high-level behavior of an Autonomous Mobile Robot (AMR). It guarantees determinism, prioritizing critical events and gracefully handling complex edge cases.

## 2. Event Priority Model

To guarantee determinism in an event-driven system, events must be processed sequentially based on a strict priority hierarchy. If multiple events occur within the same cycle, the FSM queue sorts them based on the following priorities (1 = Highest, 6 = Lowest).

1. **Safety Critical:** `EMERGENCY_STOP_TRIGGERED`, `EMERGENCY_STOP_RELEASED`
2. **System Critical:** `BATTERY_CRITICAL`
3. **Localization (Safety/Nav blocker):** `LOCALIZATION_LOST`, `LOCALIZATION_RECOVERED`
4. **Environment Reactivity:** `OBSTACLE_DETECTED`, `OBSTACLE_CLEARED`, `PATH_BLOCKED`
5. **System / Operational:** `NETWORK_LOST`, `NETWORK_RESTORED`, `BATTERY_LOW`, `BATTERY_OK`
6. **Task Progression / Docking:** `GOAL_REACHED`, `NAVIGATION_TIMEOUT`, `DOCK_DETECTED`, `DOCK_ALIGNMENT_FAILED`, `CHARGING_STARTED`, `CHARGING_COMPLETE`

**Conflict Resolution Strategy:**
- **Preemption:** High-priority events immediately preempt current states. For example, `EMERGENCY_STOP_TRIGGERED` overrides `NAVIGATING` instantly, ignoring any concurrent `GOAL_REACHED` event.
- **Queuing & Dropping:** 
  - Conflicting events of lower priority are evaluated based on the *new* state.
  - Irrelevant events (e.g., `OBSTACLE_CLEARED` while in `IDLE`) are explicitly dropped.
- **Merge/Debounce:** Rapid oscillating events (e.g., oscillating sensor noise triggering `OBSTACLE_DETECTED` and `CLEARED`) are structurally mitigated by state transition guards, ensuring that the machine transitions to `AVOIDING_OBSTACLE` and remains there until the obstacle is confirmed cleared consistently.

## 3. State Diagram

```mermaid
stateDiagram-v2
    [*] --> IDLE
    IDLE --> NAVIGATING : TASK_ASSIGNED
    IDLE --> DOCKING : BATTERY_LOW
    
    NAVIGATING --> IDLE : GOAL_REACHED
    NAVIGATING --> AVOIDING_OBSTACLE : OBSTACLE_DETECTED
    NAVIGATING --> RECOVERING_FROM_BLOCKAGE : PATH_BLOCKED
    NAVIGATING --> LOCALIZATION_RECOVERY : LOCALIZATION_LOST
    
    AVOIDING_OBSTACLE --> NAVIGATING : OBSTACLE_CLEARED
    AVOIDING_OBSTACLE --> RECOVERING_FROM_BLOCKAGE : PATH_BLOCKED
    
    RECOVERING_FROM_BLOCKAGE --> NAVIGATING : PATH_CLEARED
    RECOVERING_FROM_BLOCKAGE --> IDLE : NAVIGATION_TIMEOUT
    
    LOCALIZATION_RECOVERY --> NAVIGATING : LOCALIZATION_RECOVERED (if was navigating)
    LOCALIZATION_RECOVERY --> IDLE : LOCALIZATION_RECOVERED (if idle)
    
    DOCKING --> CHARGING : CHARGING_STARTED
    DOCKING --> IDLE : DOCK_ALIGNMENT_FAILED
    
    CHARGING --> IDLE : CHARGING_COMPLETE
    
    state "Any State" as AnyState {
    }
    
    AnyState --> SAFE_STOP : EMERGENCY_STOP_TRIGGERED
    SAFE_STOP --> IDLE : EMERGENCY_STOP_RELEASED
    
    AnyState --> DOCKING : BATTERY_CRITICAL
```

## 4. Transition Table

| Current State | Event | Guard | Next State | Action |
| --- | --- | --- | --- | --- |
| Any | `EMERGENCY_STOP_TRIGGERED` | None | `SAFE_STOP` | Disable Actuators |
| `SAFE_STOP` | `EMERGENCY_STOP_RELEASED` | None | `IDLE` | Enable Actuators |
| Any (Except `SAFE_STOP`/`CHARGING`) | `BATTERY_CRITICAL` | None | `DOCKING` | Plan route to Dock |
| Any (Except `SAFE_STOP`) | `LOCALIZATION_LOST` | None | `LOCALIZATION_RECOVERY` | Stop motion, start spin |
| `LOCALIZATION_RECOVERY` | `LOCALIZATION_RECOVERED` | Has pending Task | `NAVIGATING` | Resume Task |
| `LOCALIZATION_RECOVERY` | `LOCALIZATION_RECOVERED` | No pending Task | `IDLE` | Wait |
| `IDLE` | `TASK_ASSIGNED` | Localization OK | `NAVIGATING` | Generate Path |
| `IDLE` | `BATTERY_LOW` | None | `DOCKING` | Plan route to Dock |
| `NAVIGATING` | `OBSTACLE_DETECTED` | None | `AVOIDING_OBSTACLE` | Trigger local planner |
| `NAVIGATING` | `PATH_BLOCKED` | None | `RECOVERING_FROM_BLOCKAGE` | Request global replan |
| `NAVIGATING` | `GOAL_REACHED` | None | `IDLE` | Mark task complete |
| `AVOIDING_OBSTACLE` | `OBSTACLE_CLEARED` | None | `NAVIGATING` | Resume global path |
| `AVOIDING_OBSTACLE` | `PATH_BLOCKED` | Local timeout | `RECOVERING_FROM_BLOCKAGE` | Request global replan |
| `RECOVERING_FROM_BLOCKAGE` | `OBSTACLE_CLEARED` | Path found | `NAVIGATING` | Follow new path |
| `RECOVERING_FROM_BLOCKAGE` | `NAVIGATION_TIMEOUT` | None | `IDLE` | Abort task, flag error |
| `DOCKING` | `CHARGING_STARTED` | Dock detected | `CHARGING` | Sleep systems |
| `DOCKING` | `DOCK_ALIGNMENT_FAILED` | Retries exceeded | `IDLE` | Flag docking error |
| `CHARGING` | `CHARGING_COMPLETE` | Battery 100% | `IDLE` | Disconnect from dock |
| `CHARGING` | `BATTERY_CRITICAL` | Power lost | `DOCKING` | Retry docking |
| Any | `NETWORK_LOST` | None | `NETWORK_DEGRADED` | Log warning, pause tasks |
| `NETWORK_DEGRADED`| `NETWORK_RESTORED` | None | `IDLE` / `NAVIGATING` | Resume operation |

## 5. Failure Mode Analysis

- **Simultaneous Events:** Handled deterministically by the Event Priority queue. If `BATTERY_CRITICAL` and `OBSTACLE_DETECTED` occur at the exact same tick, `BATTERY_CRITICAL` takes precedence, forcing a transition to `DOCKING`.
- **Delayed Events:** Events are validated against the *current state*. If a delayed `OBSTACLE_CLEARED` event arrives while the robot is in `IDLE`, it is structurally ignored as it does not match a valid transition.
- **Rapidly Repeating / Oscillating Events:** e.g., a sensor rapidly toggling `OBSTACLE_DETECTED` / `CLEARED`. The state transitions act as debouncers. Upon `OBSTACLE_DETECTED`, the state moves to `AVOIDING_OBSTACLE`. The FSM will only transition back to `NAVIGATING` upon an explicit `OBSTACLE_CLEARED` that satisfies a temporal or spatial guard in the obstacle avoidance layer.
- **Network Flaps:** Network events transition the robot in and out of `NETWORK_DEGRADED`. The FSM ensures safety first; it will finish navigating its current safe path if safe, but won't accept new commands until `NETWORK_RESTORED`.
- **Localization lost while navigating:** `LOCALIZATION_LOST` preempts navigation. Next state is `LOCALIZATION_RECOVERY`. `OBSTACLE_DETECTED` in this state is ignored since motion is already halted or localized strictly to place-recognition spins.

## 6. Determinism Explanation

Determinism in this system is mathematically guaranteed because:
1. **Explicit Enumeration:** The state machine is a strict Moore/Mealy hybrid where every state S_n and input event E maps exclusively to a single next state S_{n+1} without ambiguity.
2. **Strict Queueing:** Events are routed through a singular centralized loop (`handle_event`). Concurrent events are sorted by the predefined Event Priority Table before processing.
3. **No Hidden State:** Global variables do not influence state transitions. The `next_state` is a pure function of `(current_state, event, guard_conditions)`.
4. **Defined Fall-throughs:** Any unhandled `(current_state, event)` pair defaults to dropping the event and remaining in `current_state`, preventing undefined behavior.
