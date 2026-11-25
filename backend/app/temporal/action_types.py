"""Inputs of the action workflow and its activities. Plain dataclasses, safe in the workflow sandbox."""

from dataclasses import dataclass


@dataclass
class ExecuteActionParams:
    action_id: str
    # From settings at start (ACTION_VERIFY_ATTEMPTS, ACTION_VERIFY_DELAY_SECONDS), so the run is deterministic.
    verify_attempts: int = 3
    verify_delay_seconds: int = 30
    # Lock wait plus the connector's own limit, set by the dispatcher.
    activity_timeout_seconds: int = 45 * 60
    # A retry of a failed action: read first, write only when the change is not there yet.
    precheck: bool = False


@dataclass
class VerifyActionInput:
    action_id: str
    attempt: int
    final: bool


@dataclass
class FailActionInput:
    action_id: str
    error: str
