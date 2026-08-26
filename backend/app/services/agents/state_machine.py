from __future__ import annotations

import enum


class AgentState(str, enum.Enum):
    OBSERVE = "observe"
    INVESTIGATE = "investigate"
    DIAGNOSE = "diagnose"
    PLAN = "plan"
    COMPLETED = "completed"
    FAILED = "failed"


VALID_TRANSITIONS: dict[AgentState, set[AgentState]] = {
    AgentState.OBSERVE: {AgentState.INVESTIGATE, AgentState.FAILED},
    AgentState.INVESTIGATE: {AgentState.DIAGNOSE, AgentState.FAILED},
    AgentState.DIAGNOSE: {AgentState.PLAN, AgentState.FAILED},
    AgentState.PLAN: {AgentState.COMPLETED, AgentState.FAILED},
    AgentState.COMPLETED: set(),
    AgentState.FAILED: set(),
}


class InvalidStateTransitionError(Exception):
    def __init__(self, from_state: AgentState, to_state: AgentState) -> None:
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(
            f"Cannot transition from '{from_state.value}' to '{to_state.value}'. "
            f"Valid targets: {[s.value for s in VALID_TRANSITIONS.get(from_state, set())]}"
        )


class AgentStateMachine:
    def __init__(self, initial_state: AgentState = AgentState.OBSERVE) -> None:
        self._state = initial_state
        self._history: list[AgentState] = [initial_state]

    @property
    def state(self) -> AgentState:
        return self._state

    @property
    def history(self) -> list[AgentState]:
        return list(self._history)

    def can_transition(self, target: AgentState) -> bool:
        return target in VALID_TRANSITIONS.get(self._state, set())

    def transition(self, target: AgentState) -> AgentState:
        if target not in VALID_TRANSITIONS.get(self._state, set()):
            raise InvalidStateTransitionError(self._state, target)
        self._state = target
        self._history.append(target)
        return self._state
