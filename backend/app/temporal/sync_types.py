"""Inputs of the sync workflow and its activities. Plain dataclasses, safe in the workflow sandbox."""

from dataclasses import dataclass


@dataclass
class SyncParams:
    connection_id: str
    # Set when the API created the run ("Sync now"); a scheduled run creates its own.
    sync_run_id: str | None = None
    force: bool = False


@dataclass
class RunSyncInput:
    sync_run_id: str
    force: bool = False


@dataclass
class FailSyncInput:
    sync_run_id: str
    error: str
