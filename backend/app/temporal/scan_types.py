"""Inputs of the scan workflow and its activities. Plain dataclasses, safe in the workflow sandbox."""

from dataclasses import dataclass


@dataclass
class ScanParams:
    connection_id: str
    # Set when the API created the run ("Scan now"); a scheduled run creates its own.
    scan_run_id: str | None = None


@dataclass
class RunScanInput:
    scan_run_id: str


@dataclass
class FailScanInput:
    scan_run_id: str
    error: str
