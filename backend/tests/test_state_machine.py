import pytest

from app.services.agents.state_machine import (
    AgentState,
    AgentStateMachine,
    InvalidStateTransitionError,
    VALID_TRANSITIONS,
)


class TestAgentState:
    def test_all_states_exist(self):
        assert AgentState.OBSERVE.value == "observe"
        assert AgentState.INVESTIGATE.value == "investigate"
        assert AgentState.DIAGNOSE.value == "diagnose"
        assert AgentState.PLAN.value == "plan"
        assert AgentState.COMPLETED.value == "completed"
        assert AgentState.FAILED.value == "failed"

    def test_transition_map_completeness(self):
        expected_from = {AgentState.OBSERVE, AgentState.INVESTIGATE, AgentState.DIAGNOSE, AgentState.PLAN, AgentState.COMPLETED, AgentState.FAILED}
        assert set(VALID_TRANSITIONS.keys()) == expected_from

    def test_terminal_states_have_no_transitions(self):
        assert VALID_TRANSITIONS[AgentState.COMPLETED] == set()
        assert VALID_TRANSITIONS[AgentState.FAILED] == set()


class TestStateMachineTransitions:
    def test_happy_path(self):
        sm = AgentStateMachine()
        assert sm.state == AgentState.OBSERVE

        sm.transition(AgentState.INVESTIGATE)
        assert sm.state == AgentState.INVESTIGATE

        sm.transition(AgentState.DIAGNOSE)
        assert sm.state == AgentState.DIAGNOSE

        sm.transition(AgentState.PLAN)
        assert sm.state == AgentState.PLAN

        sm.transition(AgentState.COMPLETED)
        assert sm.state == AgentState.COMPLETED

    def test_can_transition_valid(self):
        sm = AgentStateMachine(AgentState.OBSERVE)
        assert sm.can_transition(AgentState.INVESTIGATE) is True
        assert sm.can_transition(AgentState.FAILED) is True

    def test_can_transition_invalid(self):
        sm = AgentStateMachine(AgentState.OBSERVE)
        assert sm.can_transition(AgentState.DIAGNOSE) is False
        assert sm.can_transition(AgentState.PLAN) is False
        assert sm.can_transition(AgentState.COMPLETED) is False

    def test_any_state_can_fail(self):
        for state in [AgentState.OBSERVE, AgentState.INVESTIGATE, AgentState.DIAGNOSE, AgentState.PLAN]:
            sm = AgentStateMachine(state)
            assert sm.can_transition(AgentState.FAILED) is True

    def test_failed_is_terminal(self):
        sm = AgentStateMachine(AgentState.FAILED)
        assert sm.can_transition(AgentState.OBSERVE) is False
        assert sm.can_transition(AgentState.INVESTIGATE) is False

    def test_completed_is_terminal(self):
        sm = AgentStateMachine(AgentState.COMPLETED)
        assert sm.can_transition(AgentState.OBSERVE) is False
        assert sm.can_transition(AgentState.FAILED) is False


class TestStateMachineHistory:
    def test_records_history(self):
        sm = AgentStateMachine()
        sm.transition(AgentState.INVESTIGATE)
        sm.transition(AgentState.DIAGNOSE)
        assert sm.history == [AgentState.OBSERVE, AgentState.INVESTIGATE, AgentState.DIAGNOSE]

    def test_history_is_copy(self):
        sm = AgentStateMachine()
        sm.transition(AgentState.INVESTIGATE)
        h = sm.history
        h.append(AgentState.DIAGNOSE)
        assert len(sm.history) == 2


class TestInvalidTransitions:
    def test_observe_to_diagnose(self):
        sm = AgentStateMachine(AgentState.OBSERVE)
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            sm.transition(AgentState.DIAGNOSE)
        assert exc_info.value.from_state == AgentState.OBSERVE
        assert exc_info.value.to_state == AgentState.DIAGNOSE

    def test_observe_to_plan(self):
        sm = AgentStateMachine(AgentState.OBSERVE)
        with pytest.raises(InvalidStateTransitionError):
            sm.transition(AgentState.PLAN)

    def test_observe_to_completed(self):
        sm = AgentStateMachine(AgentState.OBSERVE)
        with pytest.raises(InvalidStateTransitionError):
            sm.transition(AgentState.COMPLETED)

    def test_investigate_to_observe(self):
        sm = AgentStateMachine(AgentState.INVESTIGATE)
        with pytest.raises(InvalidStateTransitionError):
            sm.transition(AgentState.OBSERVE)

    def test_investigate_to_plan(self):
        sm = AgentStateMachine(AgentState.INVESTIGATE)
        with pytest.raises(InvalidStateTransitionError):
            sm.transition(AgentState.PLAN)

    def test_diagnose_to_observe(self):
        sm = AgentStateMachine(AgentState.DIAGNOSE)
        with pytest.raises(InvalidStateTransitionError):
            sm.transition(AgentState.OBSERVE)

    def test_diagnose_to_investigate(self):
        sm = AgentStateMachine(AgentState.DIAGNOSE)
        with pytest.raises(InvalidStateTransitionError):
            sm.transition(AgentState.INVESTIGATE)

    def test_plan_to_observe(self):
        sm = AgentStateMachine(AgentState.PLAN)
        with pytest.raises(InvalidStateTransitionError):
            sm.transition(AgentState.OBSERVE)

    def test_plan_to_diagnose(self):
        sm = AgentStateMachine(AgentState.PLAN)
        with pytest.raises(InvalidStateTransitionError):
            sm.transition(AgentState.DIAGNOSE)

    def test_failed_cannot_go_anywhere(self):
        sm = AgentStateMachine(AgentState.FAILED)
        for target in [AgentState.OBSERVE, AgentState.INVESTIGATE, AgentState.DIAGNOSE, AgentState.PLAN, AgentState.COMPLETED]:
            with pytest.raises(InvalidStateTransitionError):
                sm.transition(target)

    def test_completed_cannot_go_anywhere(self):
        sm = AgentStateMachine(AgentState.COMPLETED)
        for target in [AgentState.OBSERVE, AgentState.INVESTIGATE, AgentState.DIAGNOSE, AgentState.PLAN, AgentState.FAILED]:
            with pytest.raises(InvalidStateTransitionError):
                sm.transition(target)

    def test_invalid_state_transition_error_message(self):
        sm = AgentStateMachine(AgentState.OBSERVE)
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            sm.transition(AgentState.DIAGNOSE)
        msg = str(exc_info.value)
        assert "observe" in msg
        assert "diagnose" in msg
        assert "investigate" in msg
